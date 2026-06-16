"""Gender detection via avatar image analysis.

Uses Anthropic Claude Vision API if ANTHROPIC_API_KEY is configured.
Otherwise saves avatars to disk for manual review.
"""

import base64
import os
from pathlib import Path

import httpx

from icrush.config import DATA_DIR

AVATAR_DIR = DATA_DIR / "avatars"

# Attempt to load Anthropic API key
_ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


async def download_avatar(url: str, username: str) -> Path | None:
    """Download avatar image from URL, save to data/avatars/{username}.jpg.

    Returns the local path, or None on failure.
    """
    if not url:
        return None

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    if ".png" in url:
        ext = ".png"
    local_path = AVATAR_DIR / f"{username}{ext}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                local_path.write_bytes(resp.content)
                return local_path
    except Exception:
        pass

    return None


async def classify_avatar(local_path: Path) -> str | None:
    """Classify avatar as 'female', 'male', 'couple', or None if uncertain.

    Uses Anthropic Claude Vision API if key is available.
    Falls back to None (needs manual review).
    """
    if not _ANTHROPIC_KEY:
        return None

    try:
        image_bytes = local_path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("ascii")
        mime = "image/png" if local_path.suffix == ".png" else "image/jpeg"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": _ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 10,
                    "system": "You are a gender classifier. Look at the profile picture and respond with EXACTLY one word: female, male, or couple. A couple photo (man+woman together) counts as couple. Default to female if uncertain.",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime,
                                        "data": b64,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Classify this profile picture:",
                                },
                            ],
                        }
                    ],
                },
            )
            data = resp.json()
            answer = data.get("content", [{}])[0].get("text", "").strip().lower()
            if answer in ("female", "male", "couple"):
                return answer
            return None

    except Exception:
        return None
