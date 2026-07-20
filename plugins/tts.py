import base64
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from plugins.config import PROMPT_LANG, PROMPT_TEXT, REFER_WAV_PATH, SOVITS_API_URL

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent


def to_api_path(path: str) -> str:
    source_path = Path(path)
    if not source_path.is_absolute():
        source_path = BASE_DIR / source_path
    return str(source_path).replace("\\", "/")


async def get_sovits_audio(
    text: str,
    ref_path: Optional[str] = None,
    *,
    batch_size: int = 30,
    sample_steps: int = 64,
    speed_factor: Optional[float] = None,
) -> Optional[str]:
    try:
        target_ref = to_api_path(ref_path or REFER_WAV_PATH)
        if not os.path.exists(target_ref):
            logger.error("Reference audio path does not exist: %s", target_ref)
            return None

        params = {
            "text": text,
            "text_lang": "zh",
            "ref_audio_path": target_ref,
            "prompt_text": PROMPT_TEXT,
            "prompt_lang": PROMPT_LANG,
            "top_k": 5,
            "top_p": 0.95,
            "temperature": 0.9,
            "text_split_method": "cut5",
            "batch_size": batch_size,
            "seed": -1,
            "parallel_infer": True,
            "Repetition_Penalty": 1.4,
            "sample_steps": sample_steps,
            "fragment_interval": 0.3,
        }
        if speed_factor is not None:
            params["speed_factor"] = speed_factor

        async with httpx.AsyncClient(timeout=160.0, trust_env=False) as http_client:
            response = await http_client.post(
                SOVITS_API_URL,
                timeout=120.0,
                json=params,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                return base64.b64encode(response.content).decode("utf-8")
            logger.error("SOVITS API error %s - %s", response.status_code, response.text)
    except Exception:
        logger.exception("Voice synthesis exception")
    return None
