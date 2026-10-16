"""Registro de modelos: descarga y carga una vez por lote (SDD §10)."""

import os
import urllib.request
from pathlib import Path

from editor_imagen.config import PROJECT_ROOT

MODELS_DIR = PROJECT_ROOT / "models"
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BIREFNET_REPO = "ZhengPeng7/BiRefNet"  # MIT
# El modelo trae código propio (trust_remote_code): se fija la revisión para no ejecutar versiones nuevas sin revisar.
BIREFNET_REVISION = "e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4"

UPSCALERS = {
    # nombre: (archivo, url) — Real-ESRGAN, BSD-3
    "realesrgan-x4plus": (
        "RealESRGAN_x4plus.pth",
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    ),
}

_cache: dict[str, object] = {}


def device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def download_upscaler(name: str) -> Path:
    filename, url = UPSCALERS[name]
    dest = MODELS_DIR / "upscale" / filename
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
    return dest


def birefnet():
    if "birefnet" not in _cache:
        import torch
        from transformers import AutoModelForImageSegmentation

        model = AutoModelForImageSegmentation.from_pretrained(
            BIREFNET_REPO, revision=BIREFNET_REVISION, trust_remote_code=True
        )
        model.to(device()).eval()
        if device() == "cuda":
            model.half()
        _cache["birefnet"] = model
    return _cache["birefnet"]


def upscaler(name: str = "realesrgan-x4plus"):
    key = f"upscale:{name}"
    if key not in _cache:
        from spandrel import ModelLoader

        model = ModelLoader().load_from_file(download_upscaler(name))
        model.to(device()).eval()
        _cache[key] = model
    return _cache[key]
