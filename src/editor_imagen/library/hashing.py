"""Hash exacto (SHA-256) y perceptual (pHash) (SDD §6.1 paso 2)."""

import hashlib
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def abrir(ruta: Path) -> Image.Image:
    im = Image.open(ruta)
    im.load()
    return ImageOps.exif_transpose(im)


def tiene_transparencia(im: Image.Image) -> bool:
    """True si al menos el 1 % de los píxeles es transparente (no solo un canal alfa vacío)."""
    if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
        return False
    alfa = np.asarray(im.convert("RGBA"))[..., 3]
    return bool((alfa < 250).mean() > 0.01)


def sobre_blanco(im: Image.Image) -> Image.Image:
    """Compone sobre blanco, para comparar fotos con y sin transparencia del mismo producto."""
    rgba = im.convert("RGBA")
    fondo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(fondo, rgba).convert("RGB")


def analizar(ruta: Path) -> dict:
    im = abrir(ruta)
    return {
        "ancho": im.width,
        "alto": im.height,
        "transparente": tiene_transparencia(im),
        "phash": str(imagehash.phash(sobre_blanco(im))),
    }
