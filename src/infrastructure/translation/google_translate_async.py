import aiohttp
import asyncio
from typing import Optional

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

async def google_translate(text: str, source: str = "auto", target: str = "ko") -> Optional[str]:
    """
    Translate text using Google Translate (unofficial, GET method).
    Returns translated text or None on error.
    """
    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": text,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(GOOGLE_TRANSLATE_URL, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            # data[0] is a list of [translatedText, originalText, ...]
            try:
                return "".join([item[0] for item in data[0] if item[0]])
            except Exception:
                return None
