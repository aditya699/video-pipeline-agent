# 🎬 Video Pipeline Agent

**An AI agent that does your video post-production busywork.**

Hindi video in → English transcript, editor script, dubbed audio out. One command.

Built by a creator who got tired of the copy-paste grind.

---

## The Story

I create content in Hindi. My editor works in English. You see the problem.

Every video meant:
1. Upload video somewhere
2. Get it transcribed (usually garbage quality)
3. Translate the transcript
4. Write notes for the editor about cuts, B-roll, music
5. Copy-paste URLs into WhatsApp/Slack
6. Repeat. Forever.

I even hired someone to do this. Didn't work out — too slow, too many back-and-forths, still needed my input at every step.

Should've built this a year ago. Koi nahi, better late than never.

---

## What It Does

Drop a Hindi video file → Get everything your editor needs:

| Input | Output |
|-------|--------|
| `video.mp4` | ✅ Cloud URL (shareable) |
| | ✅ Hindi transcript |
| | ✅ English translation |
| | ✅ Editor script (B-roll suggestions, cuts, transitions) |
| | ✅ English dubbed audio |
| | ✅ All files uploaded to cloud with shareable links |

Just send your editor the links. Done.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your .env file (see below)

# Run the agent
python agent.py

# Then just type:
You: process my_video.mp4
```

---

## Setup

### Environment Variables

Create a `.env` file:

```env
# Azure Storage (for cloud uploads)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_CONTAINER_NAME=your_container

# ElevenLabs (for transcription + TTS)
ELEVENLABS_API_KEY=your_api_key

# Anthropic (for translation + editor script)
ANTHROPIC_API_KEY=your_api_key
```

### Dependencies

```txt
anthropic
azure-storage-blob
elevenlabs
python-dotenv
claude-agent-sdk
```

---

## How It Works

```
┌─────────────┐
│ Hindi Video │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│                   VIDEO PIPELINE                      │
│                                                       │
│  1. Upload to Azure ──────────────► Cloud URL        │
│  2. Transcribe (ElevenLabs) ──────► Hindi Text       │
│  3. Translate (Claude) ───────────► English Text     │
│  4. Generate Editor Notes (Claude)► Edit Script      │
│  5. Text-to-Speech (ElevenLabs) ──► English Audio    │
│  6. Save & Upload All ────────────► Shareable Links  │
│                                                       │
└──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ OUTPUT (all in /output folder)      │
├─────────────────────────────────────┤
│ • video_hindi.txt                   │
│ • video_english.txt                 │
│ • video_editor.txt                  │
│ • video_english.mp3                 │
│ • Cloud URLs for everything         │
└─────────────────────────────────────┘
```

---

## Output Example

```
Pipeline Complete!

Steps completed: upload, transcribe, translate, editor_script, text_to_speech, save_files, upload_files

Files saved:
- Hindi transcript: output/video_hindi.txt
- English transcript: output/video_english.txt
- Editor script: output/video_editor.txt
- English audio: output/video_english.mp3

Cloud URLs (share with editor):
- Video: https://your-storage.blob.core.windows.net/container/video.mp4
- Transcript: https://your-storage.blob.core.windows.net/container/video_english.txt
- Editor Notes: https://your-storage.blob.core.windows.net/container/video_editor.txt
- English Audio: https://your-storage.blob.core.windows.net/container/video_english.mp3
```

---

## The Editor Script Includes

- **Key Segments** — Video broken into sections with timestamps
- **B-Roll Suggestions** — What visuals to overlay
- **Text Overlays** — Key points to show on screen
- **Transitions** — How to move between sections
- **Music Notes** — Background mood suggestions
- **Cuts** — Filler words and pauses to remove

Basically everything I used to type out manually in Google Docs.

---

## Tech Stack

| Service | Purpose |
|---------|---------|
| **ElevenLabs Scribe** | Hindi speech-to-text (actually good quality) |
| **Claude Haiku** | Translation + editor script generation |
| **ElevenLabs TTS** | English audio dubbing |
| **Azure Blob Storage** | Cloud storage for sharing |
| **Claude Agent SDK** | CLI agent interface |

---

## Why This Stack?

- **ElevenLabs Scribe** — Best Hindi transcription I've found. Most others butcher it.
- **Claude** — Fast, cheap, follows instructions well. Haiku is enough for translation.
- **Azure** — Already had it set up, works fine.

---

## Limitations

- Currently optimized for Hindi → English (my use case)
- Timestamps in editor script are estimates (no actual audio analysis)
- TTS voice is fixed (can change `voice_id` in tools.py)

---

## License

MIT — Use it, modify it, ship it.

---

*Built because I'd rather spend time creating than copy-pasting.*

---

> **A note:** A lot of service-based jobs — the kind you'd hire someone for on a freelance platform — are going to be done by agents soon. If you're a creator or builder, being AI-first means you'll prefer to build and deploy an agent over hiring for repetitive tasks. This is one of those. The era of "I'll just hire someone for this" is shifting to "I'll just build an agent for this." Learn to build them.

**Pricing**

Claude Haiku: $0.02 dollars per 1-1:30 min reels
Eleven Labs : 2k Credits (Note-90K tokens are in a 5 dollar pack)