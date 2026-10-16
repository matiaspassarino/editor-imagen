"""Upscale condicional (SDD §9.3): solo el recorte del producto y solo si hace falta agrandarlo.

Modos:
- off: Lanczos (lo de F2).
- standard: Real-ESRGAN x4plus.
- conservative: mitad Real-ESRGAN y mitad Lanczos; gana nitidez sin inventar textura ni deformar textos.

El alfa se agranda siempre con Lanczos: el modelo está entrenado para fotos, no para máscaras, y un borde
suave queda mejor que uno "afilado".
"""

import cv2
import numpy as np

FACTOR_MIN = 1.15  # por debajo no vale la pena el modelo
ESCALA_MODELO = 4
BLOQUE = 512
SOLAPE = 16
MEZCLA_CONSERVADOR = 0.5


def _modelo_por_bloques(rgb: np.ndarray) -> np.ndarray:
    """Real-ESRGAN x4 sobre la imagen, por bloques con solape para acotar la memoria de video."""
    import torch

    from editor_imagen.models import registry

    modelo = registry.upscaler()
    disp = registry.device()
    alto, ancho = rgb.shape[:2]
    s = ESCALA_MODELO
    salida = np.zeros((alto * s, ancho * s, 3), np.float32)
    for y in range(0, alto, BLOQUE):
        for x in range(0, ancho, BLOQUE):
            ya, xa = max(0, y - SOLAPE), max(0, x - SOLAPE)
            yb, xb = min(alto, y + BLOQUE + SOLAPE), min(ancho, x + BLOQUE + SOLAPE)
            t = torch.from_numpy(rgb[ya:yb, xa:xb].transpose(2, 0, 1)[None].copy()).to(disp)
            with torch.inference_mode():
                out = modelo(t)[0].clamp(0, 1).float().cpu().numpy().transpose(1, 2, 0)
            # Se conserva solo la parte central del bloque (sin el solape).
            oy, ox = (y - ya) * s, (x - xa) * s
            h, w = (min(y + BLOQUE, alto) - y) * s, (min(x + BLOQUE, ancho) - x) * s
            salida[y * s : y * s + h, x * s : x * s + w] = out[oy : oy + h, ox : ox + w]
    return salida


def agrandar(rgb: np.ndarray, alfa: np.ndarray, factor: float, modo: str) -> tuple[np.ndarray, np.ndarray, bool]:
    """Agranda el recorte x4 con el modelo si `factor` lo justifica. Devuelve (rgb, alfa, se_usó_modelo).

    El encuadre después lo lleva al tamaño final (achicando desde x4 con INTER_AREA, que no agrega artefactos).
    """
    if modo == "off" or factor < FACTOR_MIN:
        return rgb, alfa, False
    alto, ancho = alfa.shape
    tam = (ancho * ESCALA_MODELO, alto * ESCALA_MODELO)
    # El color de los píxeles transparentes es fondo o basura: se compone sobre gris neutro para que el
    # modelo no invente bordes contra un color arbitrario.
    a = alfa[..., None]
    entrada = rgb * a + 0.5 * (1 - a)
    ia = _modelo_por_bloques(entrada.astype(np.float32))
    lanczos = cv2.resize(entrada, tam, interpolation=cv2.INTER_LANCZOS4)
    if modo == "conservative":
        ia = MEZCLA_CONSERVADOR * ia + (1 - MEZCLA_CONSERVADOR) * lanczos
    alfa_g = np.clip(cv2.resize(alfa, tam, interpolation=cv2.INTER_LANCZOS4), 0, 1)
    # Deshacer la composición sobre gris en los bordes semitransparentes.
    ag = alfa_g[..., None]
    color = np.where(ag > 1e-3, (ia - 0.5 * (1 - ag)) / np.maximum(ag, 1e-3), 0)
    return np.clip(color, 0, 1).astype(np.float32), alfa_g.astype(np.float32), True
