# app3.py
"""
Backend for app3: send full PDF file to Gemini Vision and request
extraction of the exact schema the client wants.

Environment:
- GOOGLE_API_KEY in .env
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st

load_dotenv()
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API")

if not GOOGLE_API_KEY:
    raise RuntimeError("Please set GOOGLE_API_KEY in Streamlit secrets or your environment.")
genai.configure(api_key=GOOGLE_API_KEY)

# choose a vision-capable Gemini model name available in your environment.
# If your environment requires a different identifier, change this value.
MODEL_NAME = "gemini-2.0-flash"  # adjust if you use a different vision model


def get_model():
    """
    Return a model handle (wrapper) for our calls.
    """
    return genai.GenerativeModel(MODEL_NAME)

# Strict JSON template we will ask the model to follow.
JSON_TEMPLATE = {
    "service_type": "",
    "services": "",
    "title": "",
    "airport": "",
    "max_passengers_allowed": "",
    "pricing": {
        "1_pax": {"adults": None, "children": None},
        "2_pax": {"adults": None, "children": None},
        "3_pax": {"adults": None, "children": None},
        "4_pax": {"adults": None, "children": None},
        "5_pax": {"adults": None, "children": None},
        "6_pax": {"adults": None, "children": None},
        "7_pax": {"adults": None, "children": None},
        "8_pax": {"adults": None, "children": None},
        "9_pax": {"adults": None, "children": None},
        "10_pax": {"adults": None, "children": None}
    },
    "travel_type": "",   # arrival / departure / both
    "status": "",        # Active / Inactive
    "meeting_point": "",
    "fast_track": "",    # Yes / No / Expedited
    "service_details": [],   # list of bullets
    "transportation_inside_airport": "",  # Foot / Vehicle
    "assistance_with_pieces_of_luggage": "",
    "lounge_access": "",  # Yes / No
    "farewell": "",
    "special_announcement": "",
    "duration_minutes": None,
    "fee_ooh": "",       # Fee OOH
    "late_booking_fee": "",
    "usp": "",
    "refund_policy_hours": None  # 100% refund cancellation period (1-100) hours
}


def _make_prompt(pdf_text_hint=""):
    """
    Compose the instruction prompt we will send to Gemini Vision.
    We include a strict JSON template and instructions to only output valid JSON
    and to use null for missing values (or null for numeric fields).
    """
    template_json = json.dumps(JSON_TEMPLATE, indent=2)
    prompt = f"""
You are a precise data extraction assistant that reads PDFs (which may contain images, tables, or complex layout).
Extract the following fields from the provided PDF document.

Return output as STRICTLY valid JSON and match the keys exactly as in this template.
If a value is missing, return null for numeric fields and null or empty string for textual fields (prefer null for unknown).
Do NOT include any additional text, explanation, or backticks — ONLY the JSON.

Template:
{template_json}

Notes / rules:
- For pricing: try to populate each "X_pax" object's "adults" and "children" with numbers (integers). If a children price is not present, use null.
- For duration_minutes and refund_policy_hours use integers or null.
- service_details must be a JSON array of short strings (bulleted features).
- travel_type should be one of: "arrival", "departure", "both", or null.
- status should be "Active" / "Inactive" / null.
- If the PDF contains multiple possible values (e.g., multiple airports), prefer the one that is clearly labeled for the service header or first occurrence.

Now read the attached PDF (it can contain images) and extract values accordingly.
If you cannot find a field, set it to null.

{pdf_text_hint}
"""
    return prompt


def extract_fields_ai(pdf_file):
    """
    Accepts a file-like object (e.g., streamlit's UploadedFile).
    Sends the file bytes to Gemini Vision with a prompt asking for the JSON schema.
    Returns a Python dict (parsed JSON) or a dict with "error" and "raw" keys on failure.
    """
    # read bytes
    # IMPORTANT: we must read bytes once. After reading, the stream may be exhausted.
    pdf_bytes = pdf_file.read()
    mime_type = getattr(pdf_file, "type", "application/pdf")

    model = get_model()
    prompt = _make_prompt()

    # Build the multimodal parts: file + text prompt.
    # The SDK uses "parts" that can include binary file and text.
    # We pass the PDF as a binary part with correct mime_type.
    try:
        response = model.generate_content(
            [
                {
                    "role": "user",
                    "parts": [
                        {"mime_type": mime_type, "data": pdf_bytes},
                        {"text": prompt}
                    ]
                }
            ]
        )
    except Exception as e:
        return {"error": "model_call_failed", "detail": str(e)}

    # The SDK response object may expose text in different attributes; handle common cases.
    raw_text = None
    try:
        # response.text is commonly used in examples
        raw_text = response.text if hasattr(response, "text") else None
    except Exception:
        raw_text = None

    if not raw_text:
        # try string conversion
        try:
            raw_text = str(response)
        except Exception:
            raw_text = ""

    cleaned = raw_text.strip()
    # remove markdown fences if present
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # Try to parse JSON
    try:
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError:
        # If the model replied with something slightly off, return raw for inspection.
        return {"error": "invalid_json", "raw": cleaned}
