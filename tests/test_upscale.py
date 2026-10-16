import cv2
import numpy as np

from editor_imagen.config import Salida
from editor_imagen.steps import Contexto, frame, upscale


def _falso_modelo(rgb):
    return cv2.resize(rgb, (rgb.shape[1] * 4, rgb.shape[0] * 4), interpolation=cv2.INTER_NEAREST)


def _recorte():
    rgb = np.zeros((50, 80, 3), np.float32)
    rgb[..., 0] = 1  # rojo
    alfa = np.zeros((50, 80), np.float32)
    alfa[5:45, 5:75] = 1
    return rgb, alfa


def test_no_agranda_si_no_hace_falta(monkeypatch):
    monkeypatch.setattr(upscale, "_modelo_por_bloques", lambda x: (_ for _ in ()).throw(AssertionError("no debía usarse")))
    rgb, alfa = _recorte()
    assert upscale.agrandar(rgb, alfa, 1.1, "conservative")[2] is False
    assert upscale.agrandar(rgb, alfa, 3.0, "off")[2] is False


def test_conservador_x4_mantiene_color_y_borde(monkeypatch):
    monkeypatch.setattr(upscale, "_modelo_por_bloques", _falso_modelo)
    rgb, alfa = _recorte()
    r, a, usado = upscale.agrandar(rgb, alfa, 3.0, "conservative")
    assert usado and r.shape == (200, 320, 3) and a.shape == (200, 320)
    assert np.allclose(r[100, 160], [1, 0, 0], atol=0.02)  # el color no se mezcla con el gris de composición
    assert a[0, 0] == 0 and a[100, 160] == 1


def test_encuadre_con_upscale_da_el_tamano_final(monkeypatch):
    monkeypatch.setattr(upscale, "_modelo_por_bloques", _falso_modelo)
    rgb, alfa = _recorte()
    ctx = Contexto(rgb=rgb, alfa=alfa, resolucion_origen=(80, 50))
    out_rgb, out_a = frame.encuadrar(ctx, Salida(), "conservative")
    assert out_a.shape == (1080, 1080) and ctx.upscale_modelo
    cols = np.nonzero(out_a.max(axis=0) > 0.5)[0]
    assert abs((cols[-1] - cols[0] + 1) - 994) <= 2
