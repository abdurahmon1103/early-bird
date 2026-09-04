import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.5-flash-lite:generateContent"
)


def summarize_post(title: str) -> str:
    """
    Translates + lightly summarizes a Korean post title into a short
    English line. Falls back to the raw title if the API call fails,
    so a Gemini hiccup never blocks the whole Telegram message.
    """
    if not GEMINI_API_KEY:
        return title

    prompt = (
        "Translate this korean university notice title into a short, "
        "clear english sentence (max ~15 words). Just the translation, "
        "no extra commentary:\n\n"
        f"{title}"
    )

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}]
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"[WARN] Gemini summarization failed for '{title}': {e}")
        return title  # fallback: return the original korean title