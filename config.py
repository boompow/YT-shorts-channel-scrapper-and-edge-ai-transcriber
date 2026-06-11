import os

# Faster-Whisper local transcription configuration
# Model sizes: "tiny" (~39MB), "base" (~74MB), "small" (~244MB), "medium" (~769MB)
# "base" is the recommended default — fast on CPU with good accuracy for YouTube Shorts.
WHISPER_MODEL = "base"

# Device: "auto" will use CUDA GPU if available, otherwise CPU.
WHISPER_DEVICE = "auto"

# Compute type for CTranslate2 inference.
# "int8" is fastest on CPU. Use "float16" for GPU with good VRAM, "int8_float16" for limited VRAM.
WHISPER_COMPUTE_TYPE = "int8"

# Delay between downloads (seconds). No API rate limits to worry about,
# but a small delay is polite to YouTube's servers.
DEFAULT_DELAY_SECONDS = 1.0

# Paths and file naming
DEFAULT_JSON_OUTPUT = "shorts.json"
DEFAULT_TXT_OUTPUT = "transcripts.txt"
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

# Ensure directories exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
