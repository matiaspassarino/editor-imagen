"""Carga y normalización (SDD §9.1): orientación EXIF, sRGB, tamaño de trabajo."""

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from editor_imagen.imaging import redimensionar
from editor_imagen.library.hashing import abrir, tiene_transparencia
from editor_imagen.steps import Contexto

LADO_TRABAJO = 2048
_SRGB = ImageCms.createProfile("sRGB")


def _a_srgb(im: Image.Image) -> Image.Image:
    icc = im.info.get("icc_profile")
    if not icc:
        return im
    try:
        origen = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        modo = "RGBA" if im.mode in ("RGBA", "LA", "PA") else "RGB"
        return ImageCms.profileToProfile(im.convert(modo), origen, _SRGB, outputMode=modo)
    except (ImageCms.PyCMSError, OSError):
        return im  # perfil roto: se asume sRGB


def cargar(ruta: Path, lado_trabajo: int = LADO_TRABAJO) -> Contexto:
    im = abrir(ruta)
    transparente = tiene_transparencia(im)
    im = _a_srgb(im)
    if im.mode == "CMYK":
        im = im.convert("RGB")
    arr = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255
    rgb, alfa = arr[..., :3], arr[..., 3]
    alto, ancho = alfa.shape
    escala = lado_trabajo / max(ancho, alto)
    if escala < 1:
        rgb, alfa = redimensionar(rgb, alfa, round(ancho * escala), round(alto * escala))
    return Contexto(
        rgb=np.ascontiguousarray(rgb),
        alfa_original=alfa if transparente else None,
        resolucion_origen=(ancho, alto),
    )
