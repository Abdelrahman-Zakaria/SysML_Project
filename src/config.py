import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = "https://integrate.api.nvidia.com/v1"

if not API_KEY:
    raise ValueError("Missing NVIDIA API key")

if not MODEL:
    raise ValueError("Missing model identifier")