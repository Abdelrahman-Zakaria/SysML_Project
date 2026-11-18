import os

API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL_ID = os.getenv("MODEL_ID")

BASE_URL = "https://integrate.api.nvidia.com/v1"

if not API_KEY:
    raise ValueError("NVIDIA_API_KEY is missing!")

if not MODEL_ID:
    raise ValueError("MODEL_ID is missing!")