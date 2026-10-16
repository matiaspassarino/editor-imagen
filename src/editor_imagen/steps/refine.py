"""Refinado de máscara (SDD §9.5): objeto principal + piezas cercanas, sin manchas sueltas, sin halo blanco."""

import cv2
import numpy as np

from editor_imagen.config import Segmentacion
from editor_imagen.steps import Contexto

PIEZA_GRANDE = 0.15  # fracción del área principal a partir de la cual una pieza se conserva esté donde esté
PIEZA_CERCANA = 0.005  # piezas chicas (patas separadas por reflejos) se conservan si están cerca de la principal
MARGEN_CERCANIA = 0.25  # cuánto se agranda la caja de la pieza principal para considerar "cerca"


def _componentes(alfa: np.ndarray) -> np.ndarray:
    """Máscara booleana de las piezas que se conservan."""
    binaria = (alfa >= 0.5).astype(np.uint8)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(binaria, connectivity=8)
    if n <= 1:
        return np.zeros_like(binaria, dtype=bool)
    areas = stats[1:, cv2.CC_STAT_AREA]
    principal = 1 + int(np.argmax(areas))
    x, y, w, h = stats[principal, :4]
    mx, my = w * MARGEN_CERCANIA, h * MARGEN_CERCANIA
    area_p = areas.max()
    conservar = np.zeros(n, dtype=bool)
    for i in range(1, n):
        cx, cy, cw, ch, area = stats[i]
        cerca = cx < x + w + mx and cx + cw > x - mx and cy < y + h + my and cy + ch > y - my
        conservar[i] = area >= PIEZA_GRANDE * area_p or (cerca and area >= PIEZA_CERCANA * area_p)
    return conservar[etiquetas]


def rellenar_huecos_con_piezas(alfa: np.ndarray) -> tuple[np.ndarray, int]:
    """Rellena los huecos de la máscara que tienen piezas adentro.

    Una placa blanca con LEDs sobre fondo blanco suele salir como un anillo con LEDs sueltos en el medio: el
    "hueco" no es fondo, es la placa. Un hueco real (ojo de un terminal, centro de un rollo de cable, un marco)
    no tiene nada adentro y no se toca.
    """
    binaria = (alfa >= 0.5).astype(np.uint8)
    contornos, jerarquia = cv2.findContours(binaria, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if jerarquia is None:
        return alfa, 0
    jerarquia = jerarquia[0]  # [siguiente, anterior, primer_hijo, padre]

    def profundidad(i: int) -> int:
        d = 0
        while jerarquia[i][3] >= 0:
            i, d = jerarquia[i][3], d + 1
        return d

    rellenar = []
    for i, c in enumerate(contornos):
        if profundidad(i) % 2 == 0 or jerarquia[i][2] < 0:
            continue  # contorno exterior, o hueco sin nada adentro
        area_hueco = cv2.contourArea(c)
        hijo, area_piezas = jerarquia[i][2], 0.0
        while hijo >= 0:
            area_piezas += cv2.contourArea(contornos[hijo])
            hijo = jerarquia[hijo][0]
        if area_hueco > 0 and area_piezas >= 0.01 * area_hueco:
            rellenar.append(c)
    if not rellenar:
        return alfa, 0
    zona = np.zeros_like(binaria)
    cv2.drawContours(zona, rellenar, -1, 1, thickness=cv2.FILLED)
    return np.maximum(alfa, zona.astype(np.float32)), len(rellenar)


def _fondo(rgb: np.ndarray, alfa: np.ndarray) -> np.ndarray:
    fondo = alfa < 0.02
    if fondo.sum() < 100:
        return np.ones(3, dtype=np.float32)
    return np.median(rgb[fondo], axis=0).astype(np.float32)


def refinar(ctx: Contexto, cfg: Segmentacion) -> None:
    a = ctx.alfa.copy()
    a[a < 0.02] = 0
    a[a > 0.98] = 1

    piezas = _componentes(a)
    if not piezas.any():
        ctx.alfa = a
        return
    n, _, stats, _ = cv2.connectedComponentsWithStats(piezas.astype(np.uint8), connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    ctx.piezas_grandes = int((areas >= PIEZA_GRANDE * areas.max()).sum())

    # Los bordes suaves solo valen pegados a una pieza conservada; el resto (bruma, manchas) se descarta.
    radio = max(3, round(0.004 * max(a.shape)))
    cerca = cv2.dilate(piezas.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radio + 1,) * 2)).astype(bool)
    a = np.where(cerca, a, 0)
    a = np.where(piezas | (a < 0.5), a, 0)  # piezas sólidas descartadas
    if cfg.rellenar_placas and ctx.segmentacion != "transparencia original":
        a, ctx.huecos_rellenos = rellenar_huecos_con_piezas(a)
    ctx.alfa = a.astype(np.float32)

    # Decontaminación: en los píxeles semitransparentes se resta el color del fondo (quita el halo blanco).
    if cfg.refinar_bordes and ctx.segmentacion != "transparencia original":
        fondo = _fondo(ctx.rgb, ctx.alfa)
        borde = (ctx.alfa > 0.02) & (ctx.alfa < 0.98)
        ab = np.maximum(ctx.alfa[borde][:, None], 0.05)
        ctx.rgb = ctx.rgb.copy()
        ctx.rgb[borde] = np.clip((ctx.rgb[borde] - (1 - ab) * fondo) / ab, 0, 1)
