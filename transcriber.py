import os
import yt_dlp
from faster_whisper import WhisperModel


def download_audio_for_short(video_id, url, downloads_dir):
    """
    Downloads audio for a YouTube Short and saves it as [video_id].mp3.
    If the file already exists, it uses it as a cache.
    """
    out_path = os.path.join(downloads_dir, f"{video_id}.mp3")
    
    # Check if the file is already downloaded (caching)
    if os.path.exists(out_path):
        return out_path
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',  # 128kbps is lightweight and great for voice
        }],
        'outtmpl': os.path.join(downloads_dir, f"{video_id}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        try:
            ydl.download([url])
        except Exception as e:
            raise RuntimeError(f"Failed to download audio for {url}: {e}")
            
    # Double check file exists after download
    if not os.path.exists(out_path):
        raise FileNotFoundError(f"Audio file expected at {out_path} was not created.")
        
    return out_path


def load_whisper_model(model_size="base", device="auto", compute_type="int8"):
    """
    Loads and returns a Faster-Whisper model instance.
    The model is downloaded automatically on first use (~74MB for 'base').
    
    Args:
        model_size: One of "tiny", "base", "small", "medium", "large-v3"
        device: "auto" (auto-detect GPU/CPU), "cpu", or "cuda"
        compute_type: "int8" (fast CPU), "float16" (GPU), "int8_float16" (low-VRAM GPU)
    """
   # Resolve "auto" device using ctranslate2's built-in detection (no torch needed)
    if device == "auto":
        try:
            import ctranslate2
            supported = ctranslate2.get_supported_compute_types("cuda")
            resolved_device = "cuda" if supported else "cpu"
        except Exception:
            resolved_device = "cpu"
        
        # Adjust compute_type for GPU if auto-detected
        if resolved_device == "cuda" and compute_type == "int8":
            compute_type = "float16"
    else:
        resolved_device = device

    model = WhisperModel(model_size, device=resolved_device, compute_type=compute_type)
    return model, resolved_device


def transcribe_audio_with_whisper(model, audio_path):
    """
    Transcribes audio using a local Faster-Whisper model with timestamps.
    
    Returns the transcript as a formatted string with [MM:SS] timestamps
    at the beginning of each segment, matching the previous output format.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Local audio file not found: {audio_path}")

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,  # Filters out silence for cleaner output
    )

    lines = []
    for segment in segments:
        # Format timestamp as [MM:SS]
        total_seconds = int(segment.start)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        else:
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
        
        text = segment.text.strip()
        if text:
            lines.append(f"{timestamp} {text}")

    return "\n".join(lines)
