"""Quitar el reflejo del producto en la superficie de apoyo (renders y fotos sobre vidrio o acrílico).

Se activa POR FOTO (columna `ajustes` = `reflejo`), no para todo el catálogo: aplicado a las 963 fotos
acertó en 7 y cortó mal en 11 (dos filas de productos, mangos de pinzas, lazos de cable, pilas de placas).
Cuando la foto tiene reflejo de verdad, el corte sale bien.

Medido en las fotos reales: los reflejos (sobre todo en renders de IA) no son espejos exactos, la
correlación con el producto es baja o negativa, pero siempre están mucho más "lavados" hacia el blanco
(+0,3 a +0,5 de luminosidad respecto del producto). Un producto simétrico no tiene esa diferencia.

Se prueban dos líneas de apoyo, columna por columna (soporta perspectiva):

1. Borde inferior de la máscara de referencia (BiRefNet general), que suele excluir el reflejo que los
   otros modelos incluyen. Se usa solo si la referencia es "sólida" (cubre casi todo el producto por
   encima de esa línea): en placas blancas con LEDs la referencia solo ve LEDs sueltos y se ignora.
2. Punto medio vertical de la máscara, para cuando todos los modelos incluyen el reflejo (cajas en vista
   isométrica). Además de estar lavada, la máscara tiene que tener una "cintura" en esa línea (la muesca
   en V entre la base y el reflejo); así no se corta un producto blanco con la parte de arriba oscura.
"""

import cv2
import numpy as np

from editor_imagen.imaging import bbox
from editor_imagen.steps import Contexto

LADO_ANALISIS = 512
ACLARADO_MIN = 0.15  # cuánto más claro (0-1) tiene que ser el reflejo que el producto
COBERTURA_REF_MIN = 0.85  # la referencia tiene que cubrir esto del producto por encima de la línea
ALTO_REFLEJO_MIN = 0.1  # el agregado debajo de la línea, fracción de la altura del producto
CINTURA_MAX = 0.85  # ancho de la máscara en la línea / ancho mediano, para la candidata del punto medio
VENTANA = 0.25  # franja del producto (sobre la línea) contra la que se compara, fracción de su altura


def _extremos(m: np.ndarray, x0: int, x1: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fila superior e inferior de la máscara por columna (columnas vacías interpoladas) y qué columnas tienen máscara."""
    sub = m[:, x0:x1]
    hay = sub.any(axis=0)
    filas = np.arange(m.shape[0])[:, None]
    arriba = np.where(sub, filas, m.shape[0]).min(axis=0).astype(float)
    abajo = np.where(sub, filas, -1).max(axis=0).astype(float)
    xs = np.arange(x0, x1)
    if hay.sum() >= 2:
        arriba = np.interp(xs, xs[hay], arriba[hay])
        abajo = np.interp(xs, xs[hay], abajo[hay])
    return arriba, abajo, hay


def _regiones(m: np.ndarray, linea: np.ndarray, x0: int, x1: int) -> tuple[np.ndarray, np.ndarray]:
    filas = np.arange(m.shape[0])[:, None]
    lim = np.full(m.shape[1], np.inf)
    lim[x0:x1] = linea
    debajo = m & (filas > lim[None, :])
    encima = m & (filas <= lim[None, :])
    return encima, debajo


def _lavado(gris: np.ndarray, encima: np.ndarray, debajo: np.ndarray, linea: np.ndarray, x0: int, x1: int, alto_prod: float) -> float:
    """Luminosidad media de lo de debajo menos la de una franja del producto justo encima de la línea."""
    filas = np.arange(gris.shape[0])[:, None]
    lim = np.full(gris.shape[1], np.inf)
    lim[x0:x1] = linea
    franja = encima & (filas > lim[None, :] - VENTANA * alto_prod)
    if franja.sum() < 20 or debajo.sum() < 20:
        return 0.0
    return float(gris[debajo].mean() - gris[franja].mean())


def _detectar(gris: np.ndarray, m: np.ndarray, ref: np.ndarray | None) -> np.ndarray | None:
    caja = bbox(m.astype(np.float32), 0.5)
    if caja is None:
        return None
    y0, y1, x0, x1 = caja
    if y1 - y0 < 40 or x1 - x0 < 10:
        return None
    arriba, abajo, hay = _extremos(m, x0, x1)

    # Candidata 1: borde inferior de la referencia.
    if ref is not None and ref.any():
        _, fondo_ref, hay_ref = _extremos(ref, x0, x1)
        if hay_ref.any():
            encima, debajo = _regiones(m, fondo_ref, x0, x1)
            alto_prod = float(np.median((fondo_ref - arriba)[hay_ref]))
            cobertura = (ref & encima).sum() / max(encima.sum(), 1)
            alto_reflejo = float(np.median((abajo - fondo_ref)[hay_ref]))
            if (
                cobertura >= COBERTURA_REF_MIN
                and alto_reflejo >= ALTO_REFLEJO_MIN * alto_prod
                and _lavado(gris, encima, debajo, fondo_ref, x0, x1, alto_prod) >= ACLARADO_MIN
            ):
                return fondo_ref

    # Candidata 2: punto medio, con cintura.
    medio = (arriba + abajo) / 2
    filas_medio = np.round(medio).astype(int)
    anchos = m.sum(axis=1)
    ancho_mediano = np.median(anchos[y0:y1])
    fila_cintura = int(np.median(filas_medio[hay]))
    ventana = slice(max(y0, fila_cintura - 3), min(y1, fila_cintura + 4))
    cintura = anchos[ventana].min() / max(ancho_mediano, 1)
    encima, debajo = _regiones(m, medio, x0, x1)
    alto_prod = float(np.median((medio - arriba)[hay]))
    if cintura <= CINTURA_MAX and _lavado(gris, encima, debajo, medio, x0, x1, alto_prod) >= ACLARADO_MIN:
        return medio
    return None


def _pieza_principal(m: np.ndarray) -> np.ndarray:
    """La referencia a veces separa producto y parte del reflejo en dos piezas: se usa solo la más grande."""
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n <= 2:
        return m
    return etiquetas == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))


def quitar_reflejo(ctx: Contexto) -> bool:
    alto, ancho = ctx.alfa.shape
    escala = min(1.0, LADO_ANALISIS / max(alto, ancho))
    chico = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    escala = chico[0] / ancho
    gris = cv2.cvtColor(cv2.resize(ctx.rgb, chico, interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    m = cv2.resize(ctx.alfa, chico, interpolation=cv2.INTER_AREA) >= 0.5
    ref = None
    if ctx.alfa_referencia is not None:
        ref = _pieza_principal(cv2.resize(ctx.alfa_referencia, chico, interpolation=cv2.INTER_AREA) >= 0.5)
    caja = bbox(m.astype(np.float32), 0.5)
    linea_caja = _detectar(gris, m, ref)
    if linea_caja is None:
        return False
    _, _, x0, x1 = caja
    linea = np.full(chico[0], np.inf)
    linea[x0:x1] = linea_caja
    xs = np.clip(np.round((np.arange(ancho) + 0.5) * escala - 0.5).astype(int), 0, chico[0] - 1)
    corte = linea[xs] / escala
    filas = np.arange(alto)[:, None]
    ctx.alfa = np.where(filas > corte[None, :] + 1, 0, ctx.alfa).astype(np.float32)
    ctx.reflejo_quitado = True
    return True
