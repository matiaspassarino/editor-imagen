"""Registro de modelos: descarga y carga una vez por lote (SDD §10)."""

import os
import urllib.request
from pathlib import Path

from editor_imagen.config import PROJECT_ROOT

MODELS_DIR = PROJECT_ROOT / "models"
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Variantes de BiRefNet (todas MIT): nombre → (repo, revisión, resolución de entrada).
# Traen código propio (trust_remote_code): se fija la revisión para no ejecutar versiones nuevas sin revisar.
BIREFNET = {
    "birefnet": ("ZhengPeng7/BiRefNet", "e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4", 1024),
    "birefnet-dynamic": ("ZhengPeng7/BiRefNet_dynamic", "280306042f57b7a33854319da62fd86aaa89ec4c", 1536),
    "birefnet-dis": ("ZhengPeng7/BiRefNet-DIS5K", "343602b3219a0e905a86c5012935d5a4a0882390", 1024),
}

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


def birefnet(nombre: str = "birefnet"):
    """Devuelve (modelo, resolución de entrada)."""
    if nombre not in _cache:
        from transformers import AutoModelForImageSegmentation

        repo, revision, _ = BIREFNET[nombre]
        model = AutoModelForImageSegmentation.from_pretrained(repo, revision=revision, trust_remote_code=True)
        model.to(device()).eval()
        if device() == "cuda":
            model.half()
        _cache[nombre] = model
    return _cache[nombre], BIREFNET[nombre][2]


def upscaler(name: str = "realesrgan-x4plus"):
    key = f"upscale:{name}"
    if key not in _cache:
        from spandrel import ModelLoader

        model = ModelLoader().load_from_file(download_upscaler(name))
        model.to(device()).eval()
        _cache[key] = model
    return _cache[key]
