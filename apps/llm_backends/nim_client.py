"""NVIDIA NIM HTTP helpers (PS5.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

from config import settings

NIM_HEALTH_PATH = "/v1/health/ready"
BACKEND_ID = "gpu"


def nim_base_url() -> str:
    return (getattr(settings, "gpu_llm_base_url", "") or "").strip().rstrip("/")


def nim_health_url(base: str | None = None) -> str:
    root = (base or nim_base_url()).rstrip("/")
    if not root:
        return ""
    if root.endswith(NIM_HEALTH_PATH):
        return root
    return urljoin(f"{root}/", NIM_HEALTH_PATH.lstrip("/"))


def check_nim_health(
    *,
    base_url: str | None = None,
    timeout_s: float = 5.0,
) -> bool:
    """Return True when NIM ready endpoint responds HTTP 200."""
    url = nim_health_url(base_url)
    if not url:
        return False
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


def gpu_activity_path() -> Path:
    raw = (getattr(settings, "gpu_activity_file", "") or "").strip()
    if not raw:
        raw = str(Path(__file__).resolve().parents[2] / "var" / "llm_last_gpu_call_at")
    return Path(raw)


def record_gpu_activity(*, at: datetime | None = None) -> Path:
    """Write last successful GPU call timestamp (PS5.7 idle TTL signal)."""
    path = gpu_activity_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = (at or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    path.write_text(f"{ts}\n", encoding="utf-8")
    return path
