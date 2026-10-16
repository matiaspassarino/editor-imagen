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
MODELOS = {2: "realesrgan-x2plus", 4: "realesrgan-x4plus"}  # escala → modelo; x2 cuesta la mitad
BLOQUE = 512
SOLAPE = 16
MEZCLA_CONSERVADOR = 0.5


def _modelo_por_bloques(rgb: np.ndarray, escala: int) -> np.ndarray:
    """Real-ESRGAN sobre la imagen, por bloques con solape para acotar la memoria de video."""
    import torch

    from editor_imagen.models import registry

    modelo = registry.upscaler(MODELOS[escala])
    disp = registry.device()
    dtype = next(modelo.model.parameters()).dtype
    alto, ancho = rgb.shape[:2]
    s = escala
    salida = np.zeros((alto * s, ancho * s, 3), np.float32)
    for y in range(0, alto, BLOQUE):
        for x in range(0, ancho, BLOQUE):
            ya, xa = max(0, y - SOLAPE), max(0, x - SOLAPE)
            yb, xb = min(alto, y + BLOQUE + SOLAPE), min(ancho, x + BLOQUE + SOLAPE)
            t = torch.from_numpy(rgb[ya:yb, xa:xb].transpose(2, 0, 1)[None].copy()).to(disp, dtype)
            with torch.inference_mode():
                out = modelo(t)[0].clamp(0, 1).float().cpu().numpy().transpose(1, 2, 0)
            # Se conserva solo la parte central del bloque (sin el solape).
            oy, ox = (y - ya) * s, (x - xa) * s
            h, w = (min(y + BLOQUE, alto) - y) * s, (min(x + BLOQUE, ancho) - x) * s
            salida[y * s : y * s + h, x * s : x * s + w] = out[oy : oy + h, ox : ox + w]
    return salida


def agrandar(rgb: np.ndarray, alfa: np.ndarray, factor: float, modo: str) -> tuple[np.ndarray, np.ndarray, bool]:
    """Agranda el recorte con el modelo si `factor` lo justifica. Devuelve (rgb, alfa, se_usó_modelo).

    Usa x2 si alcanza y x4 si no. Si el modelo daría más de lo necesario, la entrada se achica antes para
    que la salida tenga justo el tamaño final: mismo resultado con mucho menos cómputo. El encuadre después
    ajusta los últimos píxeles.
    """
    if modo == "off" or factor < FACTOR_MIN:
        return rgb, alfa, False
    escala = 2 if factor <= 2 else 4
    alto, ancho = alfa.shape
    # Tamaño de entrada para que la salida del modelo sea ~ el tamaño final (nunca más grande que el recorte).
    reduccion = min(1.0, factor / escala)
    if reduccion < 1.0:
        entrada_tam = (max(1, round(ancho * reduccion)), max(1, round(alto * reduccion)))
        rgb_in, alfa_in = cv2.resize(rgb, entrada_tam, interpolation=cv2.INTER_AREA), cv2.resize(alfa, entrada_tam, interpolation=cv2.INTER_AREA)
    else:
        rgb_in, alfa_in = rgb, alfa
    alto, ancho = alfa_in.shape
    tam = (ancho * escala, alto * escala)
    # El color de los píxeles transparentes es fondo o basura: se compone sobre gris neutro para que el
    # modelo no invente bordes contra un color arbitrario.
    a = alfa_in[..., None]
    entrada = rgb_in * a + 0.5 * (1 - a)
    ia = _modelo_por_bloques(entrada.astype(np.float32), escala)
    if modo == "conservative":
        # La mitad clásica sale del recorte sin reducir, que tiene más detalle.
        completo = rgb * alfa[..., None] + 0.5 * (1 - alfa[..., None])
        lanczos = cv2.resize(completo, tam, interpolation=cv2.INTER_LANCZOS4)
        ia = MEZCLA_CONSERVADOR * ia + (1 - MEZCLA_CONSERVADOR) * lanczos
    # El alfa de salida también sale del recorte sin reducir: borde más fiel.
    alfa_g = np.clip(cv2.resize(alfa, tam, interpolation=cv2.INTER_LANCZOS4), 0, 1)
    # Deshacer la composición sobre gris en los bordes semitransparentes.
    ag = alfa_g[..., None]
    color = np.where(ag > 1e-3, (ia - 0.5 * (1 - ag)) / np.maximum(ag, 1e-3), 0)
    return np.clip(color, 0, 1).astype(np.float32), alfa_g.astype(np.float32), True
