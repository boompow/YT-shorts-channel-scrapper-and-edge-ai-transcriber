# YouTube Shorts Scraper & Local Transcriber

A robust terminal CLI tool that scrapes all YouTube Shorts from a channel and transcribes them locally with timestamps using **Faster-Whisper** — no API keys, no cloud, no rate limits.

## Features

- **YouTube Shorts Scraping**: Uses `yt-dlp` to fetch all Shorts URLs from a channel instantly.
- **Local Audio Caching**: Downloads lightweight MP3 audio files to the local `downloads/` directory. Re-runs skip already-downloaded files.
- **Offline Transcription**: Uses [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2-optimized Whisper) to transcribe audio entirely on-device. Supports `tiny`, `base`, `small`, and `medium` model sizes.
- **Automatic GPU Detection**: Auto-detects CUDA GPUs for accelerated inference; falls back gracefully to CPU.
- **Resumable State Management**: Progress is saved to `shorts.json` after every video. Restarting the tool resumes where it left off — no duplicate downloads or re-transcriptions.
- **Stunning Terminal UI**: Built with `rich` for elegant logs, tables, spinners, and progress bars.

---

## Installation

1. **Prerequisites**:
   - Python 3.10+
   - [FFmpeg](https://ffmpeg.org/) installed and available on your system PATH.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   The Whisper model (~74MB for `base`) is downloaded automatically on first run.

3. **Configure Channel**:
   Create a `.env` file in the project root with your target channel:
   ```env
   YOUTUBE_CHANNEL="@ChannelHandle"
   ```

---

## Usage

```bash
python main.py
```

The channel is read from `.env` by default. You can also pass it directly:

```bash
python main.py --channel @ChannelHandle
```

### Command-Line Arguments

| Argument | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--channel` | `-c` | YouTube channel handle (e.g. `@Username`) or URL. | From `.env` |
| `--model` | `-m` | Whisper model size: `tiny`, `base`, `small`, `medium`. | `base` |
| `--delay` | `-d` | Delay in seconds between downloads (polite to YouTube). | `1.0` |
| `--force-scrape`| `-f` | Force re-scraping the channel even if `shorts.json` exists. | `False` |
| `--output-json` | `-o` | Path for the state tracking JSON database. | `shorts.json` |
| `--output-txt`  | `-t` | Path for the formatted transcripts text file. | `transcripts.txt` |

### Model Comparison

| Model | Size | Speed (CPU, ~60s clip) | Quality |
| :--- | :--- | :--- | :--- |
| `tiny` | ~39 MB | ~1-2s | Decent for clear speech |
| `base` | ~74 MB | ~3-5s | **Recommended** — good balance |
| `small` | ~244 MB | ~8-15s | High accuracy |
| `medium` | ~769 MB | ~20-40s | Best accuracy, slow on CPU |

---

## How It Works

1. **Scraping**: Queries the channel's `/shorts` tab via `yt-dlp`, extracts titles and URLs, and saves them as `pending` entries in `shorts.json`.
2. **Downloading**: For each pending short, checks if `downloads/[video_id].mp3` exists. If not, downloads the best audio and converts it to 128kbps MP3 via FFmpeg.
3. **Transcription**: Runs the audio through the local Faster-Whisper model with VAD (Voice Activity Detection) filtering. Produces timestamped segments formatted as `[MM:SS]`.
4. **State Persistence**: Updates `shorts.json` to `completed`, stores the transcript, and regenerates `transcripts.txt` with all finished transcriptions.

---

## Output Format

### State Database (`shorts.json`)
```json
[
  {
    "id": "dQw4w9WgXcQ",
    "url": "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up Short",
    "status": "completed",
    "transcript": "[00:00] We're no strangers to love...\n[00:04] You know the rules and so do I...",
    "transcribed_at": "2026-06-11 11:30:00"
  }
]
```

### Transcripts File (`transcripts.txt`)
```
================================================================================
Title: Never Gonna Give You Up Short
URL: https://www.youtube.com/shorts/dQw4w9WgXcQ
Transcribed At: 2026-06-11 11:30:00
--------------------------------------------------------------------------------
[00:00] We're no strangers to love...
[00:04] You know the rules and so do I...
================================================================================
```

---

## Project Structure

```
├── main.py            # Entry point — orchestrates scraping, downloading, transcribing
├── scraper.py         # YouTube Shorts list scraper (yt-dlp)
├── transcriber.py     # Audio download + Faster-Whisper transcription
├── config.py          # All configuration defaults (model, paths, delays)
├── requirements.txt   # Python dependencies
├── .env               # Channel handle (not committed)
├── shorts.json        # State database (auto-generated)
├── transcripts.txt    # Final transcript output (auto-generated)
└── downloads/         # Cached MP3 audio files
```
