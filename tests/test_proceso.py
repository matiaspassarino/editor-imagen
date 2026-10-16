import numpy as np
from PIL import Image

from editor_imagen import batch
from editor_imagen.config import Config, Salida, Segmentacion
from editor_imagen.library import inventory
from editor_imagen.library.unify import unificar
from editor_imagen.steps import Contexto, frame, refine


def producto_transparente(ruta, tamano=(600, 400), caja=(100, 50, 400, 250)):
    """PNG con un rectángulo opaco (con textura) sobre fondo transparente."""
    arr = np.zeros((tamano[1], tamano[0], 4), np.uint8)
    x0, y0, x1, y1 = caja
    rng = np.random.default_rng(0)
    arr[y0:y1, x0:x1, :3] = (rng.random((y1 - y0, x1 - x0, 3)) * 200).astype(np.uint8)
    arr[y0:y1, x0:x1, 3] = 255
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGBA").save(ruta)
    return ruta


def test_encuadre_centra_con_margen():
    alfa = np.zeros((500, 800), np.float32)
    alfa[100:200, 100:500] = 1  # 400 × 100
    ctx = Contexto(rgb=np.ones((500, 800, 3), np.float32), alfa=alfa, resolucion_origen=(800, 500))
    rgb, a = frame.encuadrar(ctx, Salida(tamano=1080, margen=0.04))
    assert a.shape == (1080, 1080) and rgb.shape == (1080, 1080, 3)
    filas = np.nonzero(a.max(axis=1) > 0.5)[0]
    cols = np.nonzero(a.max(axis=0) > 0.5)[0]
    assert cols[0] == 43 and cols[-1] == 1036  # lado mayor = 994 px (92 %), centrado
    assert abs((filas[0] + filas[-1]) / 2 - 539.5) <= 1
    assert abs(ctx.factor_escala - 994 / 400) < 0.01


def test_refinado_descarta_manchas_y_conserva_patas_cercanas():
    alfa = np.zeros((400, 400), np.float32)
    alfa[100:200, 100:200] = 1  # cuerpo
    alfa[205:260, 140:143] = 1  # pata fina separada por un reflejo
    alfa[350:356, 350:356] = 1  # mancha lejana
    ctx = Contexto(rgb=np.ones((400, 400, 3), np.float32), alfa=alfa, segmentacion="birefnet")
    refine.refinar(ctx, Segmentacion())
    assert ctx.alfa[150, 150] == 1 and ctx.alfa[230, 141] == 1
    assert ctx.alfa[352, 352] == 0
    assert ctx.piezas_grandes == 1


def test_decontaminacion_quita_halo_blanco():
    alfa = np.zeros((100, 100), np.float32)
    alfa[20:80, 20:80] = 1
    alfa[20:80, 80] = 0.5
    rgb = np.ones((100, 100, 3), np.float32)
    rgb[20:80, 20:80] = [1, 0, 0]
    rgb[20:80, 80] = [1, 0.5, 0.5]  # rojo mezclado al 50 % con el fondo blanco
    ctx = Contexto(rgb=rgb, alfa=alfa, segmentacion="birefnet")
    refine.refinar(ctx, Segmentacion())
    assert np.allclose(ctx.rgb[50, 80], [1, 0, 0], atol=0.02)


def test_varias_piezas_es_informativa():
    from editor_imagen.steps import qc

    assert not qc.requiere_revision(["3 piezas grandes separadas"])
    assert qc.requiere_revision(["3 piezas grandes separadas", "producto toca el borde de la foto (posible recorte)"])
    assert not qc.requiere_revision([])


def test_asignar_salidas_por_codigo_sin_choques():
    filas = [
        {"id": "i1", "nombre": "a", "codigo": "3280;3281", "salida": ""},
        {"id": "i2", "nombre": "b", "codigo": "", "salida": ""},
        {"id": "i0", "nombre": "c", "codigo": "3280", "salida": ""},
        {"id": "i3", "nombre": "d", "codigo": "4000", "salida": "4000.png"},
        {"id": "i4", "nombre": "e", "codigo": "4000", "salida": ""},
    ]
    s = batch.asignar_salidas(filas)
    assert s["i0"] == ["3280.png"] and s["i1"] == ["3280_2.png", "3281.png"]
    assert s["i2"] == ["b.png"]
    assert s["i3"] == ["4000.png"] and s["i4"] == ["4000_2.png"]  # quien ya lo tenía lo conserva


def test_procesar_de_punta_a_punta_y_reanudar(tmp_path):
    fuente = tmp_path / "FOTOS"
    producto_transparente(fuente / "plug.png")
    cfg = Config(biblioteca=tmp_path / "bib", fuentes=[fuente])
    unificar(cfg)

    res = batch.procesar(cfg)

    assert res.candidatas == 1 and res.por_estado["ok"] == 1
    salida = cfg.biblioteca / "procesadas" / "plug.png"
    im = Image.open(salida)
    assert im.size == (1080, 1080) and im.mode == "RGBA"
    assert tuple(round(d) for d in im.info["dpi"]) == (300, 300)
    a = np.asarray(im)[..., 3]
    assert a[0, 0] == 0 and a[540, 540] == 255
    fila = inventory.cargar(cfg.biblioteca / "inventario.csv")[0]
    assert fila["estado"] == "ok" and fila["salida"] == "plug.png" and fila["procesado_con"]

    # Re-ejecutar no repite trabajo; cargar un código renombra la salida.
    assert batch.procesar(cfg).candidatas == 0
    fila["codigo"] = "3280"
    fila["estado"] = "pendiente"
    inventory.guardar(cfg.biblioteca / "inventario.csv", [fila])
    batch.procesar(cfg)
    assert (cfg.biblioteca / "procesadas" / "3280.png").exists()
    assert not salida.exists()


def test_error_en_una_imagen_no_frena_el_lote(tmp_path):
    fuente = tmp_path / "FOTOS"
    producto_transparente(fuente / "bien.png")
    producto_transparente(fuente / "otra.png", caja=(10, 10, 300, 390))
    cfg = Config(biblioteca=tmp_path / "bib", fuentes=[fuente])
    unificar(cfg)
    (cfg.biblioteca / "originales" / "otra.png").write_bytes(b"no es una imagen")

    res = batch.procesar(cfg)

    assert res.por_estado == {"ok": 1, "error": 1}
    estados = {f["nombre"]: f["estado"] for f in inventory.cargar(cfg.biblioteca / "inventario.csv")}
    assert estados == {"bien": "ok", "otra": "error"}
