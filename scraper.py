import yt_dlp
import re
from typing import Any


def normalize_channel_url(channel_input):
    """
    Normalizes a channel handle or URL into a YouTube Shorts tab URL.
    Examples:
        @username -> https://www.youtube.com/@username/shorts
        username -> https://www.youtube.com/@username/shorts
        https://www.youtube.com/@username -> https://www.youtube.com/@username/shorts
    """
    channel_input = channel_input.strip()
    
    # If it's already a full URL
    if channel_input.startswith("http://") or channel_input.startswith("https://"):
        # Make sure it points to the shorts tab
        if "/shorts" not in channel_input.lower():
            # Remove trailing slash
            channel_input = channel_input.rstrip("/")
            # Handle channels with handles or custom paths
            channel_input = f"{channel_input}/shorts"
        return channel_input

    # If it starts with @ or is just a handle name
    if channel_input.startswith("@"):
        return f"https://www.youtube.com/{channel_input}/shorts"
    else:
        return f"https://www.youtube.com/@{channel_input}/shorts"

def scrape_shorts_list(channel_input):
    """
    Scrapes the list of Shorts from a channel using yt-dlp.
    Returns:
        List of dicts containing metadata for each YouTube Short.
    """
    shorts_url = normalize_channel_url(channel_input)
    
    ydl_opts: dict[str, Any] = {
        'extract_flat': True,    # Get metadata without downloading videos or reading deep comments
        'quiet': True,           # Avoid clogging console outputs
        'skip_download': True,   # Do not download files yet
        'no_warnings': True,
        'playlistreverse': False # Fetch in standard order
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        try:
            info = ydl.extract_info(shorts_url, download=False)
            
            shorts = []
            if 'entries' in info:
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    video_id = entry.get('id')
                    title = entry.get('title')
                    
                    if video_id:
                        shorts.append({
                            'id': video_id,
                            'url': f"https://www.youtube.com/shorts/{video_id}",
                            'title': title or f"Short {video_id}",
                            'status': 'pending',
                            'transcript': None,
                            'transcribed_at': None
                        })
            return shorts
        except Exception as e:
            raise RuntimeError(f"Failed to scrape shorts from {shorts_url}: {e}")
