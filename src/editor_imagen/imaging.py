"""Utilidades de imagen compartidas por los pasos. Convención: RGB float32 [0,1] HxWx3 y alfa float32 [0,1] HxW."""

import cv2
import numpy as np


def redimensionar(rgb: np.ndarray, alfa: np.ndarray, ancho: int, alto: int) -> tuple[np.ndarray, np.ndarray]:
    """Redimensiona con alfa premultiplicado, para que el color de los píxeles transparentes no manche los bordes."""
    achica = ancho * alto < rgb.shape[0] * rgb.shape[1]
    interp = cv2.INTER_AREA if achica else cv2.INTER_LANCZOS4
    pre = rgb * alfa[..., None]
    pre = cv2.resize(pre, (ancho, alto), interpolation=interp)
    a = np.clip(cv2.resize(alfa, (ancho, alto), interpolation=interp), 0, 1)
    color = np.where(a[..., None] > 1e-4, pre / np.maximum(a[..., None], 1e-4), 0)
    return np.clip(color, 0, 1).astype(np.float32), a.astype(np.float32)


def bbox(alfa: np.ndarray, umbral: float = 8 / 255) -> tuple[int, int, int, int] | None:
    """(y0, y1, x0, x1) del área con alfa > umbral; None si está vacía."""
    filas = np.nonzero((alfa > umbral).any(axis=1))[0]
    if filas.size == 0:
        return None
    cols = np.nonzero((alfa > umbral).any(axis=0))[0]
    return int(filas[0]), int(filas[-1]) + 1, int(cols[0]), int(cols[-1]) + 1
