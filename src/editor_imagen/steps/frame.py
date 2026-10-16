"""Encuadre (SDD §9.7): recorte al producto y centrado en un cuadrado transparente."""

import numpy as np

from editor_imagen.config import Salida
from editor_imagen.imaging import bbox, redimensionar
from editor_imagen.steps import Contexto


def encuadrar(ctx: Contexto, cfg: Salida) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (rgb, alfa) de `tamano × tamano`."""
    caja = bbox(ctx.alfa)
    if caja is None:
        raise ValueError("no se detectó ningún producto (máscara vacía)")
    y0, y1, x0, x1 = caja
    rgb, alfa = ctx.rgb[y0:y1, x0:x1], ctx.alfa[y0:y1, x0:x1]
    alto, ancho = alfa.shape

    util = round(cfg.tamano * (1 - 2 * cfg.margen))
    escala = util / max(ancho, alto)
    # Respecto de la foto original (la de trabajo puede estar reducida a 2048 px).
    ctx.factor_escala = escala * max(ctx.resolucion_origen) / max(ctx.rgb.shape[:2])
    nuevo_ancho, nuevo_alto = max(1, round(ancho * escala)), max(1, round(alto * escala))
    rgb, alfa = redimensionar(rgb, alfa, nuevo_ancho, nuevo_alto)

    lienzo_rgb = np.zeros((cfg.tamano, cfg.tamano, 3), np.float32)
    lienzo_a = np.zeros((cfg.tamano, cfg.tamano), np.float32)
    oy, ox = (cfg.tamano - nuevo_alto) // 2, (cfg.tamano - nuevo_ancho) // 2
    lienzo_rgb[oy : oy + nuevo_alto, ox : ox + nuevo_ancho] = rgb
    lienzo_a[oy : oy + nuevo_alto, ox : ox + nuevo_ancho] = alfa
    return lienzo_rgb, lienzo_a
