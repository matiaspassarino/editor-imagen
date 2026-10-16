import cv2
import numpy as np

from editor_imagen.steps import Contexto
from editor_imagen.steps.reflection import quitar_reflejo
from editor_imagen.steps.refine import rellenar_huecos_con_piezas


def _textura(alto, ancho, semilla=0):
    rng = np.random.default_rng(semilla)
    chica = rng.random((max(2, alto // 12), max(2, ancho // 12)))
    return cv2.resize(chica, (ancho, alto), interpolation=cv2.INTER_CUBIC).clip(0, 1).astype(np.float32)


def _con_reflejo(largo_reflejo: int):
    rgb = np.ones((400, 300, 3), np.float32)
    alfa = np.zeros((400, 300), np.float32)
    prod = _textura(160, 200) * 0.8  # producto con contraste, filas 60..220
    rgb[60:220, 50:250] = prod[..., None]
    reflejo = 1 - (1 - prod[::-1]) * 0.35  # espejo, aclarado hacia el blanco
    rgb[220 : 220 + largo_reflejo, 50:250] = reflejo[:largo_reflejo, :, None]
    alfa[60 : 220 + largo_reflejo, 50:250] = 1  # el modelo tomó producto + reflejo
    return rgb, alfa


def _verificar_corte(ctx):
    assert ctx.alfa[150, 150] == 1
    assert ctx.alfa[260, 150] == 0
    filas = np.nonzero(ctx.alfa[:, 150])[0]
    assert abs(filas[-1] - 220) <= 6


def test_quita_reflejo_con_referencia_que_lo_excluye():
    rgb, alfa = _con_reflejo(120)
    ref = np.zeros_like(alfa)
    ref[60:220, 50:250] = 1
    ctx = Contexto(rgb=rgb, alfa=alfa, alfa_referencia=ref)
    assert quitar_reflejo(ctx)
    _verificar_corte(ctx)


def test_quita_reflejo_completo_sin_referencia():
    rgb, alfa = _con_reflejo(160)  # todos los modelos lo incluyeron: el eje es la mitad
    for d in range(30):  # muesca en V entre la base y el reflejo (vista isométrica)
        alfa[220 - (30 - d) // 6 : 221 + (30 - d) // 6, 50 + d] = 0
        alfa[220 - (30 - d) // 6 : 221 + (30 - d) // 6, 249 - d] = 0
    ctx = Contexto(rgb=rgb, alfa=alfa)
    assert quitar_reflejo(ctx)
    _verificar_corte(ctx)


def test_sin_reflejo_la_referencia_no_corta():
    rgb, alfa = _con_reflejo(0)
    ref = alfa.copy()
    ctx = Contexto(rgb=rgb, alfa=alfa, alfa_referencia=ref)
    assert not quitar_reflejo(ctx)


def test_no_corta_producto_simetrico():
    rgb = np.ones((400, 300, 3), np.float32)
    alfa = np.zeros((400, 300), np.float32)
    mitad = _textura(100, 200, semilla=3) * 0.8
    rgb[100:200, 50:250] = mitad[..., None]
    rgb[200:300, 50:250] = mitad[::-1, :, None]  # simétrico, mismo contraste
    alfa[100:300, 50:250] = 1
    ctx = Contexto(rgb=rgb, alfa=alfa)

    assert not quitar_reflejo(ctx)
    assert ctx.alfa[290, 150] == 1


def test_rellena_placa_con_leds_pero_no_huecos_vacios():
    alfa = np.zeros((300, 600), np.float32)
    # Placa: anillo con LEDs sueltos adentro.
    cv2.circle(alfa, (150, 150), 120, 1, thickness=15)
    for x, y in [(110, 110), (190, 120), (150, 190), (120, 170)]:
        alfa[y - 8 : y + 8, x - 8 : x + 8] = 1
    # Terminal: anillo con el ojo vacío.
    cv2.circle(alfa, (450, 150), 80, 1, thickness=25)

    a, n = rellenar_huecos_con_piezas(alfa)

    assert n == 1
    assert a[150, 150] == 1  # centro de la placa
    assert a[150, 450] == 0  # ojo del terminal
