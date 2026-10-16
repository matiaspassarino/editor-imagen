"""Mejora suave (SDD §9.6): balance de blancos y exposición tomando el fondo como referencia, y nitidez.

El fondo de las fotos de producto es (o debería ser) blanco: si sale amarillento o gris, ese mismo tinte o
falta de luz está en el producto. Se corrige solo lo necesario para neutralizar el fondo, con topes, y no se
toca nada si el fondo no es blanco y parejo (fondo negro, de color, fotos que ya venían sin fondo): ahí no
hay referencia confiable y se respetan los colores reales (RNF7).
"""

import cv2
import numpy as np

from editor_imagen.config import Mejora
from editor_imagen.steps import Contexto

FONDO_CLARO_MIN = 0.6  # luminancia mínima del fondo para usarlo de referencia
FONDO_PAREJO_MAX = 0.08  # desvío máximo de luminancia del fondo
TINTE_MAX = 0.08  # si el fondo está más teñido que esto, es un fondo de color, no un blanco mal balanceado
GANANCIA_COLOR_MAX = 0.1  # corrección máxima por canal (±10 %)
FONDO_OBJETIVO = 0.96
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def _fondo(ctx: Contexto) -> np.ndarray | None:
    """Color medio del fondo si sirve de referencia, si no None."""
    if ctx.segmentacion == "transparencia original":
        return None
    fondo = ctx.alfa < 0.02
    if fondo.mean() < 0.05:
        return None
    pix = ctx.rgb[fondo]
    if len(pix) > 200_000:
        pix = pix[:: len(pix) // 200_000]
    luma = pix @ LUMA
    color = np.median(pix, axis=0)
    if np.median(luma) < FONDO_CLARO_MIN or luma.std() > FONDO_PAREJO_MAX:
        return None
    if color.max() - color.min() > TINTE_MAX:
        return None
    return color.astype(np.float32)


def corregir_color(ctx: Contexto, cfg: Mejora) -> None:
    """Balance de blancos y exposición sobre la foto de trabajo (antes del encuadre)."""
    fondo = _fondo(ctx)
    if fondo is None:
        return
    rgb = ctx.rgb
    if cfg.balance_blancos:
        gris = float(fondo.mean())
        ganancia = np.clip(gris / np.maximum(fondo, 1e-3), 1 - GANANCIA_COLOR_MAX, 1 + GANANCIA_COLOR_MAX)
        rgb = rgb * ganancia
        fondo = fondo * ganancia
    if cfg.contraste > 0:
        luma = float(fondo @ LUMA)
        g = float(np.clip(FONDO_OBJETIVO / max(luma, 1e-3), 1.0, 1.0 + 0.5 * cfg.contraste))
        if g > 1.001:
            # Ganancia lineal con compresión suave de las altas luces, para no quemar los blancos del producto.
            x = rgb * g
            umbral = 0.9
            rgb = np.where(x > umbral, umbral + (1 - umbral) * np.tanh((x - umbral) / (1 - umbral)), x)
            ctx.mejora_exposicion = g
    ctx.rgb = np.clip(rgb, 0, 1).astype(np.float32)
    ctx.mejora_color = True


def enfocar(rgb: np.ndarray, alfa: np.ndarray, cantidad: float) -> np.ndarray:
    """Máscara de enfoque sobre la imagen final. El desenfoque se pondera por alfa, para que el fondo
    transparente (negro en RGB) no genere un halo oscuro en el borde del producto."""
    if cantidad <= 0:
        return rgb
    a = alfa[..., None]
    peso = cv2.GaussianBlur(alfa, (0, 0), 1.0)[..., None]
    desenfoque = cv2.GaussianBlur(rgb * a, (0, 0), 1.0) / np.maximum(peso, 1e-3)
    nitido = rgb + cantidad * (rgb - desenfoque)
    return np.where(a > 0, np.clip(nitido, 0, 1), rgb).astype(np.float32)
