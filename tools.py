"""
Video Pipeline - All-in-one video processing utilities.
"""

from azure.storage.blob import BlobServiceClient
from elevenlabs.client import ElevenLabs
import anthropic
import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import logging
import requests
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize clients
anthropic_client = anthropic.Anthropic()


def run_video_pipeline(file_path: str, progress_callback=None) -> dict:
    """
    Complete video processing pipeline:
    1. Upload to Azure
    2. Transcribe (Hindi)
    3. Translate to English
    4. Generate editor script
    5. Generate English audio (TTS)
    6. Generate Instagram & LinkedIn captions
    7. Save all outputs locally & upload to Azure

    Args:
        file_path: Path to video/audio file
        progress_callback: Optional callback(step, total, status, detail) for progress updates

    Returns:
        Dictionary with all results and file paths
    """

    def report(step, total, status, detail=""):
        if progress_callback:
            progress_callback(step, total, status, detail)

    results = {
        "input_file": file_path,
        "steps_completed": []
    }

    # === STEP 1: Upload to Azure ===
    report(1, 7, "started", "Uploading to Azure...")
    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME")

        if not connection_string or not container_name:
            raise ValueError("Azure credentials not configured")

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_name = os.path.basename(file_path)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        results["azure_url"] = blob_client.url
        results["steps_completed"].append("upload")
        report(1, 7, "done")

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        results["upload_error"] = str(e)

    # === STEP 2: Transcribe with ElevenLabs ===
    report(2, 7, "started", "Transcribing audio (Hindi)...")
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ElevenLabs API key not configured")

        elevenlabs = ElevenLabs(api_key=api_key)

        with open(file_path, "rb") as audio_file:
            transcription = elevenlabs.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v2",
                language_code="hin"
            )

        results["hindi_transcript"] = transcription.text
        results["steps_completed"].append("transcribe")
        report(2, 7, "done")

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        results["transcribe_error"] = str(e)
        return results  # Can't continue without transcript

    # === STEP 3: Translate to English ===
    report(3, 7, "started", "Translating to English...")
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""Translate this Hindi text to English.
Keep it natural and conversational. Only return the translation.
Do not add filler words like "guys", "folks", or "you know" that aren't in the original.

Example:
Hindi: "तो हम आज बात करेंगे कि कैसे आप अपना पहला ऐप बना सकते हैं"
English: "So today we'll talk about how you can build your first app"
(Note: "तो हम आज" = "So today we" - do NOT translate as "So guys today")

Now translate:
{results["hindi_transcript"]}"""
            }]
        )
        results["english_transcript"] = response.content[0].text
        results["steps_completed"].append("translate")
        report(3, 7, "done")

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        results["translate_error"] = str(e)

    # === STEP 4: Generate Editor Script ===
    report(4, 7, "started", "Generating editor script...")
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""You are a video editor assistant. Create an editor script for this video.

Include:
1. **Key Segments** - Break into sections with estimated timestamps
2. **B-Roll Suggestions** - Visuals to overlay
3. **Text Overlays** - Key points for screen
4. **Transitions** - Between sections
5. **Music Notes** - Background mood
6. **Cuts** - Filler words/pauses to remove

TRANSCRIPT:
{results.get("english_transcript", results["hindi_transcript"])}

Generate the editor script:"""
            }]
        )
        results["editor_script"] = response.content[0].text
        results["steps_completed"].append("editor_script")
        report(4, 7, "done")

    except Exception as e:
        logger.error(f"Editor script failed: {e}")
        results["editor_error"] = str(e)

    # === STEP 5: Generate English Audio (Text-to-Speech) ===
    report(5, 7, "started", "Generating English audio...")
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs = ElevenLabs(api_key=api_key)

        # Generate audio from English transcript
        audio_generator = elevenlabs.text_to_speech.convert(
            voice_id="ipTsYx5BgSDPgZ2oCy9M",
            text=results["english_transcript"],
            model_id="eleven_multilingual_v2"
        )

        # Collect audio bytes from generator
        audio_bytes = b"".join(audio_generator)

        results["english_audio"] = audio_bytes
        results["steps_completed"].append("text_to_speech")
        report(5, 7, "done")

    except Exception as e:
        logger.error(f"Text-to-speech failed: {e}")
        results["tts_error"] = str(e)

    # === STEP 6: Generate Social Media Captions ===
    report(6, 7, "started", "Generating Instagram & LinkedIn captions...")
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"""Based on this video transcript, create engaging social media captions.

TRANSCRIPT:
{results.get("english_transcript", results["hindi_transcript"])}

Generate TWO captions:

## INSTAGRAM CAPTION
- Hook in first line (attention-grabbing)
- Use line breaks for readability
- Include relevant emojis
- Add a call-to-action
- Include 5-10 relevant hashtags at the end
- Keep it under 2200 characters

## LINKEDIN CAPTION
- Professional tone
- Start with a hook or insight
- Use short paragraphs
- Include a thought-provoking question or CTA
- No hashtags in the middle, only 3-5 at the very end
- Keep it under 3000 characters

Format your response exactly as:
---INSTAGRAM---
[instagram caption here]

---LINKEDIN---
[linkedin caption here]"""
            }]
        )

        caption_text = response.content[0].text

        # Parse the captions
        if "---INSTAGRAM---" in caption_text and "---LINKEDIN---" in caption_text:
            parts = caption_text.split("---LINKEDIN---")
            instagram_part = parts[0].replace("---INSTAGRAM---", "").strip()
            linkedin_part = parts[1].strip() if len(parts) > 1 else ""

            results["instagram_caption"] = instagram_part
            results["linkedin_caption"] = linkedin_part
        else:
            # Fallback: store the whole response
            results["social_captions"] = caption_text

        results["steps_completed"].append("social_captions")
        report(6, 7, "done")

    except Exception as e:
        logger.error(f"Social captions failed: {e}")
        results["social_captions_error"] = str(e)

    # === STEP 7: SAVE ALL FILES & UPLOAD ===
    report(7, 7, "started", "Saving files & uploading...")
    try:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(file_path))[0]

        # Save Hindi transcript
        if "hindi_transcript" in results:
            path = os.path.join(output_dir, f"{base_name}_hindi.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["hindi_transcript"])
            results["hindi_file"] = path

        # Save English transcript
        if "english_transcript" in results:
            path = os.path.join(output_dir, f"{base_name}_english.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["english_transcript"])
            results["english_file"] = path

        # Save Editor script
        if "editor_script" in results:
            path = os.path.join(output_dir, f"{base_name}_editor.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["editor_script"])
            results["editor_file"] = path

        # Save English audio
        if "english_audio" in results:
            path = os.path.join(output_dir, f"{base_name}_english.mp3")
            with open(path, "wb") as f:
                f.write(results["english_audio"])
            results["english_audio_file"] = path

        # Save Instagram caption
        if "instagram_caption" in results:
            path = os.path.join(output_dir, f"{base_name}_instagram.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["instagram_caption"])
            results["instagram_file"] = path

        # Save LinkedIn caption
        if "linkedin_caption" in results:
            path = os.path.join(output_dir, f"{base_name}_linkedin.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(results["linkedin_caption"])
            results["linkedin_file"] = path

        results["steps_completed"].append("save_files")

        # Upload all files to Azure (part of step 6)
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Upload English transcript
        if "english_file" in results:
            blob_name = os.path.basename(results["english_file"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(results["english_file"], "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            results["english_transcript_url"] = blob_client.url

        # Upload Editor script
        if "editor_file" in results:
            blob_name = os.path.basename(results["editor_file"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(results["editor_file"], "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            results["editor_script_url"] = blob_client.url

        # Upload English audio
        if "english_audio_file" in results:
            blob_name = os.path.basename(results["english_audio_file"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(results["english_audio_file"], "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            results["english_audio_url"] = blob_client.url

        # Upload Instagram caption
        if "instagram_file" in results:
            blob_name = os.path.basename(results["instagram_file"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(results["instagram_file"], "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            results["instagram_caption_url"] = blob_client.url

        # Upload LinkedIn caption
        if "linkedin_file" in results:
            blob_name = os.path.basename(results["linkedin_file"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(results["linkedin_file"], "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            results["linkedin_caption_url"] = blob_client.url

        results["steps_completed"].append("upload_files")
        report(7, 7, "done")

    except Exception as e:
        logger.error(f"Save/upload failed: {e}")
        results["save_error"] = str(e)

    return results
