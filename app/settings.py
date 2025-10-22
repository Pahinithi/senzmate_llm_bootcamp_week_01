import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).parent.parent


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_MODEL_NAME = "gemini-2.5-flash"

API_TITLE = "Nithilan CV and Job Description Matcher"
API_DESCRIPTION = "API to match CV with Job Description using Gemini AI"
API_VERSION = "1.0.0"
