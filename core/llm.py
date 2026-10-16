"""Optional Gemini client over urllib. Returns parsed JSON or None; never raises."""
import json
import os
import urllib.request

TIMEOUT_SECONDS = 8
DEFAULT_MODEL = "gemini-2.5-flash"


def configured():
    return bool(os.getenv("GEMINI_API_KEY"))


def model_name():
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def complete_json(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name()}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception:
        return None
