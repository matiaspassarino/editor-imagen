"""Segmentación (SDD §9.4): máscara alfa con BiRefNet, o la transparencia que ya traía la foto."""

import cv2
import numpy as np

from editor_imagen.config import Segmentacion
from editor_imagen.steps import Contexto

ENTRADA_MODELO = 1024  # resolución de entrenamiento de BiRefNet
_MEDIA = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_DESVIO = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _sobre_blanco(ctx: Contexto) -> np.ndarray:
    if ctx.alfa_original is None:
        return ctx.rgb
    a = ctx.alfa_original[..., None]
    return ctx.rgb * a + (1 - a)


def _transparencia_confiable(ctx: Contexto) -> bool:
    """Descarta fotos con alfa que igual traen el producto sobre un rectángulo blanco (p. ej. esquinas redondeadas)."""
    a = ctx.alfa_original
    opaco = a > 0.98
    if opaco.mean() < 0.005:
        return False
    borde = opaco & ~cv2.erode(opaco.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    blancos = ctx.rgb[borde].min(axis=1) > 0.92
    return blancos.mean() < 0.6


def _birefnet(rgb: np.ndarray) -> np.ndarray:
    import torch

    from editor_imagen.models import registry

    modelo = registry.birefnet()
    x = cv2.resize(rgb, (ENTRADA_MODELO, ENTRADA_MODELO), interpolation=cv2.INTER_AREA)
    x = (x - _MEDIA) / _DESVIO
    p = next(modelo.parameters())
    t = torch.from_numpy(x.transpose(2, 0, 1)[None].copy()).to(p.device, p.dtype)
    with torch.inference_mode():
        pred = modelo(t)[-1].sigmoid()[0, 0].float().cpu().numpy()
    return cv2.resize(pred, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)


def segmentar(ctx: Contexto, cfg: Segmentacion) -> None:
    if ctx.alfa_original is not None and cfg.usar_transparencia_existente and _transparencia_confiable(ctx):
        ctx.alfa = ctx.alfa_original
        ctx.segmentacion = "transparencia original"
        return
    if ctx.alfa_original is not None:
        # Se descarta el alfa (no confiable o desactivado): se trabaja sobre blanco como cualquier foto.
        ctx.rgb = _sobre_blanco(ctx)
        ctx.alfa_original = None
    if cfg.modelo != "birefnet":
        raise NotImplementedError(f"modelo de segmentación '{cfg.modelo}' no implementado todavía")
    ctx.alfa = _birefnet(ctx.rgb).astype(np.float32)
    ctx.segmentacion = cfg.modelo
