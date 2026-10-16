from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from editor_imagen.config import Config
from editor_imagen.library import inventory
from editor_imagen.library.unify import estado, unificar


def foto(ruta: Path, semilla: int, tamano=(400, 300), alfa=False) -> Path:
    """Imagen con estructura (no ruido puro) para que el pHash sea estable al redimensionar."""
    rng = np.random.default_rng(semilla)
    chica = (rng.random((6, 8, 3)) * 255).astype(np.uint8)
    im = Image.fromarray(chica).resize(tamano, Image.BILINEAR)
    if alfa:
        im = im.convert("RGBA")
        a = np.asarray(im).copy()
        a[: tamano[1] // 3, :, 3] = 0
        im = Image.fromarray(a)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    im.save(ruta)
    return ruta


@pytest.fixture
def entorno(tmp_path):
    fuente = tmp_path / "FOTOS"
    cfg = Config(biblioteca=tmp_path / "bib", fuentes=[fuente])
    return fuente, cfg


def test_unificar_agrupa_y_copia(entorno):
    fuente, cfg = entorno
    a = foto(fuente / "Audio" / "3064 _ 3071.png", 1)
    (fuente / "otra").mkdir()
    (fuente / "otra" / "copia.png").write_bytes(a.read_bytes())  # duplicado exacto
    # Casi idéntica, más grande y con nombre genérico: aporta la resolución, no el nombre.
    Image.open(a).resize((800, 600)).save(fuente / "otra" / "WhatsApp Image 2026-01-01.jpg", quality=95)
    foto(fuente / "SL-TF5050-1E-W (2).png", 2, alfa=True)
    foto(fuente / "WhatsApp Image 2026.png", 3)
    (fuente / "catalogo.pdf").write_bytes(b"%PDF")

    res = unificar(cfg)

    assert res.unicas == 3
    assert res.copias_exactas == 1
    assert res.casi_identicas == 1
    assert res.ignorados == {".pdf": 1}
    filas = {f["nombre"]: f for f in inventory.cargar(cfg.biblioteca / "inventario.csv")}
    assert set(filas) == {"3064_3071", "SL-TF5050-1E-W_2", "WhatsApp Image 2026"}
    g = filas["3064_3071"]
    assert g["copias"] == "3"
    assert (g["ancho"], g["alto"]) == ("800", "600")  # representante = mayor resolución
    assert g["ruta_original"].endswith("WhatsApp Image 2026-01-01.jpg")
    assert g["carpeta"] == "otra"
    assert g["nombre_generico"] == "no"
    assert (cfg.biblioteca / "originales" / "3064_3071.jpg").exists()
    assert filas["SL-TF5050-1E-W_2"]["transparente"] == "sí"
    assert filas["WhatsApp Image 2026"]["nombre_generico"] == "sí"
    assert all(f["estado"] == "pendiente" for f in filas.values())


def test_variantes_con_nombre_distinto_no_se_fusionan(entorno):
    fuente, cfg = entorno
    a = foto(fuente / "3276-BL.png", 1)
    Image.open(a).resize((440, 330)).save(fuente / "3276-O.png")  # para el pHash, la misma foto
    Image.open(a).resize((800, 600)).save(fuente / "3276-BL - copia.jpg")  # misma foto, nombre compatible

    res = unificar(cfg)

    filas = {f["nombre"]: f for f in inventory.cargar(cfg.biblioteca / "inventario.csv")}
    assert res.unicas == 2 and res.casi_identicas == 1 and res.con_parecidas == 2
    assert filas["3276-BL"]["parecidas"] == "3276-O"
    assert filas["3276-O"]["parecidas"] == "3276-BL"
    assert filas["3276-BL"]["copias"] == "2" and filas["3276-BL"]["ancho"] == "800"


def test_nombre_generico_no_bloquea_la_fusion_ni_une_variantes(entorno):
    fuente, cfg = entorno
    a = foto(fuente / "3202.png", 1)
    Image.open(a).resize((440, 330)).save(fuente / "3203.png")
    Image.open(a).resize((800, 600)).save(fuente / "WhatsApp Image 2026.jpg")

    res = unificar(cfg)

    # La genérica se fusiona con una sola de las dos; 3202 y 3203 siguen separadas.
    filas = {f["nombre"]: f for f in inventory.cargar(cfg.biblioteca / "inventario.csv")}
    assert set(filas) == {"3202", "3203"}
    assert res.casi_identicas == 1
    assert filas["3202"]["parecidas"] == "3203"


def test_reejecutar_respeta_codigos_editados(entorno):
    fuente, cfg = entorno
    foto(fuente / "a.png", 1)
    foto(fuente / "b.png", 2)
    unificar(cfg)
    ruta_inv = cfg.biblioteca / "inventario.csv"
    filas = inventory.cargar(ruta_inv)
    ids = {f["id"] for f in filas}
    for f in filas:
        if f["nombre"] == "a":
            f["codigo"] = "3280;3281"
            f["descripcion"] = "Plug 3,5 mm"
    inventory.guardar(ruta_inv, filas)

    foto(fuente / "c.png", 3)
    res = unificar(cfg)

    filas2 = {f["nombre"]: f for f in inventory.cargar(ruta_inv)}
    assert res.nuevas == 1 and res.unicas == 3
    assert ids <= {f["id"] for f in filas2.values()}
    assert filas2["a"]["codigo"] == "3280;3281"
    assert filas2["a"]["descripcion"] == "Plug 3,5 mm"


def test_choque_de_nombres(entorno):
    fuente, cfg = entorno
    foto(fuente / "x" / "conector.png", 1)
    foto(fuente / "y" / "conector.png", 2)
    unificar(cfg)
    nombres = sorted(f["nombre"] for f in inventory.cargar(cfg.biblioteca / "inventario.csv"))
    assert nombres[0] == "conector" and nombres[1].startswith("conector_") and len(nombres[1]) == len("conector_") + 6


def test_indice_borrado_reutiliza_identicos_y_no_pisa_distintos(entorno):
    fuente, cfg = entorno
    foto(fuente / "a.png", 1)
    foto(fuente / "b.png", 2)
    unificar(cfg)
    orig = cfg.biblioteca / "originales"
    (cfg.biblioteca / ".indice.json").unlink()
    (cfg.biblioteca / "inventario.csv").unlink()
    (orig / "b.png").unlink()
    foto(orig / "b.png", 99)  # un archivo ajeno con el mismo nombre

    res = unificar(cfg)

    assert res.unicas == 2
    assert sorted(p.name for p in orig.iterdir())[:2] == ["a.png", "b.png"]
    assert len(list(orig.iterdir())) == 3  # a.png reutilizado, b.png ajeno intacto, b_<hash>.png nuevo
    nombres = {f["nombre"] for f in inventory.cargar(cfg.biblioteca / "inventario.csv")}
    assert "a" in nombres and any(n.startswith("b_") for n in nombres)


def test_inventario_guardado_por_excel_con_comas_y_ansi(entorno):
    fuente, cfg = entorno
    foto(fuente / "a.png", 1)
    unificar(cfg)
    ruta_inv = cfg.biblioteca / "inventario.csv"
    filas = inventory.cargar(ruta_inv)
    filas[0]["descripcion"] = "Fotocélula ñandú"
    # Simula "CSV (delimitado por comas)" de Excel: separador coma, codificación ANSI.
    import csv
    with open(ruta_inv, "w", encoding="cp1252", newline="") as f:
        w = csv.DictWriter(f, fieldnames=inventory.COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    unificar(cfg)
    assert inventory.cargar(ruta_inv)[0]["descripcion"] == "Fotocélula ñandú"


def test_no_escanea_la_biblioteca_pero_si_entrada(tmp_path):
    bib = tmp_path / "bib"
    cfg = Config(biblioteca=bib, fuentes=[tmp_path])  # la biblioteca está dentro de la fuente
    foto(tmp_path / "a.png", 1)
    unificar(cfg)
    foto(bib / "entrada" / "4813.png", 5)
    res = unificar(cfg)
    assert res.unicas == 2 and res.nuevas == 1
    filas = {f["nombre"]: f for f in inventory.cargar(bib / "inventario.csv")}
    assert filas["4813"]["carpeta"] == "entrada"
    assert estado(cfg).total == 2
