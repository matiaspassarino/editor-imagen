from editor_imagen import batch
from editor_imagen.config import Config
from editor_imagen.library import inventory
from editor_imagen.library.unify import unificar
from editor_imagen.review import Revision
from tests.test_proceso import producto_transparente


def _biblioteca(tmp_path):
    fuente = tmp_path / "FOTOS"
    producto_transparente(fuente / "Audio" / "plug.png")
    producto_transparente(fuente / "otro.png", caja=(50, 50, 300, 300))
    cfg = Config(biblioteca=tmp_path / "bib", fuentes=[fuente])
    unificar(cfg)
    batch.procesar(cfg)
    return cfg, Revision(cfg)


def test_filtrar(tmp_path):
    _, rev = _biblioteca(tmp_path)
    filas = rev.filas()
    assert len(rev.filtrar(filas, "todas", "", "", False)) == 2
    assert [f["nombre"] for f in rev.filtrar(filas, "todas", "Audio", "", False)] == ["plug"]
    assert [f["nombre"] for f in rev.filtrar(filas, "ok", "", "PLU", False)] == ["plug"]
    assert rev.filtrar(filas, "revisar", "", "", False) == []


def test_miniatura_y_vistas(tmp_path):
    _, rev = _biblioteca(tmp_path)
    f = rev.filas()[0]
    mini = rev.miniatura(f)
    assert mini.exists() and mini.suffix == ".jpg"
    assert rev.original(f).mode == "RGB"
    assert rev.resultado(f, "negro").size == (700, 700)


def test_guardar_conserva_ajustes_sin_casilla_y_avisa_si_hay_que_reprocesar(tmp_path):
    cfg, rev = _biblioteca(tmp_path)
    f = rev.filas()[0]
    rev._actualizar(f["id"], ajustes="relleno")
    fila, cambio = rev.guardar(f["id"], " 3280 ", "Plug", "", ["Quitar reflejo"])
    assert cambio and fila["codigo"] == "3280" and fila["ajustes"] == "relleno, reflejo"
    assert rev.casillas(fila) == ["Quitar reflejo"]
    _, cambio = rev.guardar(f["id"], "3280", "Plug 3,5 mm", "", ["Quitar reflejo"])
    assert not cambio  # solo cambió la descripción


def test_reprocesar_renombra_y_marcar_ok(tmp_path):
    cfg, rev = _biblioteca(tmp_path)
    f = rev.filas()[0]
    rev.guardar(f["id"], "4000", "", "", [])
    fila = rev.reprocesar(f["id"])
    assert fila["salida"] == "4000.png" and (cfg.biblioteca / "procesadas" / "4000.png").exists()
    (cfg.biblioteca / "_revisar" / "4000.png").write_bytes(b"x")
    rev._actualizar(f["id"], estado="revisar")
    fila = rev.marcar_ok(f["id"])
    assert fila["estado"] == "ok" and not (cfg.biblioteca / "_revisar" / "4000.png").exists()
    assert inventory.cargar(cfg.biblioteca / "inventario.csv")  # el inventario sigue legible
