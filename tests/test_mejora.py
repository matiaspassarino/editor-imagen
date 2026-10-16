import numpy as np

from editor_imagen.config import Mejora
from editor_imagen.steps import Contexto
from editor_imagen.steps.enhance import corregir_color, enfocar


def _foto(fondo, producto=(0.5, 0.5, 0.5)):
    rgb = np.empty((200, 200, 3), np.float32)
    rgb[:] = fondo
    rgb[60:140, 60:140] = producto
    alfa = np.zeros((200, 200), np.float32)
    alfa[60:140, 60:140] = 1
    return Contexto(rgb=rgb, alfa=alfa, segmentacion="combinado")


def test_fondo_amarillento_se_neutraliza():
    ctx = _foto(fondo=(0.95, 0.93, 0.87), producto=(0.475, 0.465, 0.435))  # mismo tinte en el producto
    corregir_color(ctx, Mejora(contraste=0))
    p = ctx.rgb[100, 100]
    assert ctx.mejora_color and p.max() - p.min() < 0.005


def test_fondo_gris_aclara_con_tope():
    ctx = _foto(fondo=(0.7, 0.7, 0.7))
    corregir_color(ctx, Mejora(contraste=0.3))
    assert abs(ctx.mejora_exposicion - 1.15) < 1e-3  # tope: 1 + 0,5 × 0,3
    assert abs(ctx.rgb[100, 100, 0] - 0.5 * 1.15) < 0.01


def test_fondo_de_color_o_negro_no_se_toca():
    for fondo in [(0.2, 0.4, 0.9), (0.05, 0.05, 0.05)]:
        ctx = _foto(fondo=fondo)
        antes = ctx.rgb.copy()
        corregir_color(ctx, Mejora())
        assert not ctx.mejora_color and np.array_equal(ctx.rgb, antes)


def test_transparencia_original_no_se_toca():
    ctx = _foto(fondo=(0.9, 0.85, 0.8))
    ctx.segmentacion = "transparencia original"
    corregir_color(ctx, Mejora())
    assert not ctx.mejora_color


def test_enfoque_sin_halo_en_el_borde():
    rgb = np.zeros((100, 100, 3), np.float32)
    rgb[30:70, 30:70] = 0.8  # producto claro; afuera RGB negro (transparente)
    alfa = np.zeros((100, 100), np.float32)
    alfa[30:70, 30:70] = 1
    out = enfocar(rgb, alfa, 0.5)
    assert np.allclose(out[30:70, 30:70], 0.8, atol=1e-3)  # superficie pareja: el borde no se oscurece
