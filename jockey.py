import firebase_admin
from firebase_admin import credentials as fb_credentials, firestore
from google.oauth2 import service_account
from google.cloud import texttospeech
import os
import google.generativeai as genai
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel


SERVICE_ACCOUNT_PATH = "./keys/radio-jockey-testing-site-firebase-adminsdk-fbsvc-9ce27601c6.json"
COLLECTION_NAME = "news"

# Separate credential objects
vertex_credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)
firebase_cred = fb_credentials.Certificate(SERVICE_ACCOUNT_PATH)


def generate_transcript(news_batch):
    aiplatform.init(
        project="radio-jockey-testing-site",
        location="asia-south1",
        credentials=vertex_credentials
    )
    try:
        model = GenerativeModel("gemini-2.5-flash")

        # Check for key errors safely
        news_batch = [item for item in news_batch if 'title' in item and 'content' in item]

        input_text = "\n\n".join([f"📰 {item['title']}: {item['content']}" for item in news_batch])

        prompt = f"""
        You are a professional radio host creating a spoken radio segment based on {len(news_batch)} news stories.

         Instructions:
        - Make the script sound casual, expressive, and engaging, like a real human radio announcer.
        - Group related stories smoothly, using natural transitions between them.
        - Do NOT use the phrase "news item" or any numbering.

        📰 News stories:
        {input_text}
    """



        response = model.generate_content(prompt)
        print("🗒️ Transcript:")
        print(response.text)
        return response.text

    except Exception as e:
        print(f"❌ Error generating transcript with Gemini: {e}")
        return ""


def fetch_tagged_news(service_account_path, collection_name):
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(firebase_cred)

        db = firestore.client()
        print("✅ Connected to Firestore")

        # Filter: where tag == True, edit this part acc to the final dbase config
        docs = db.collection(collection_name).where("tag", "==", True).get()

        filtered_data = []
        for doc in docs:
            data = doc.to_dict()
            filtered_data.append(data)

        print(f"📦 Retrieved {len(filtered_data)} tagged items")
        return filtered_data

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []




def synthesize_with_chirp(text, output_filename="outputs/output.mp3"):
    client = texttospeech.TextToSpeechClient(credentials=vertex_credentials)

    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        name="en-IN-Chirp3-HD-Zephyr",  # Replace with your preferred Chirp3 voice
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config,
    )

    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f"🔉 Audio content written to {output_filename}")

# === Run ===
docs = fetch_tagged_news(SERVICE_ACCOUNT_PATH, COLLECTION_NAME)
print("=====done retrieval=====\n")
transcript=generate_transcript(docs)
print("=====transcripting=====\n")

synthesize_with_chirp(transcript)