"""Exportación (SDD §9.8): PNG RGBA, sRGB, 300 DPI."""

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

_ICC_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def a_imagen(rgb: np.ndarray, alfa: np.ndarray) -> Image.Image:
    a8 = np.round(alfa * 255).astype(np.uint8)
    rgb8 = np.round(rgb * 255).astype(np.uint8)
    rgb8[a8 == 0] = 0  # sin color basura en lo transparente (y PNG más chico)
    return Image.fromarray(np.dstack([rgb8, a8]), "RGBA")


def guardar(im: Image.Image, destino: Path, dpi: int) -> None:
    tmp = destino.with_name(destino.name + ".tmp")
    im.save(tmp, format="PNG", dpi=(dpi, dpi), icc_profile=_ICC_SRGB)
    os.replace(tmp, destino)
