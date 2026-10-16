import pytest

from editor_imagen.library.naming import clave, es_generico, nombre_unico, sanear


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("SP-6305 _ SP-6306", "SP-6305_SP-6306"),
        ("SL-TF5050-1E-W (2)", "SL-TF5050-1E-W_2"),
        ("CAPACITORES   MOTOR AC CBB60", "CAPACITORES MOTOR AC CBB60"),
        ("3064 _ 3071", "3064_3071"),
        ('a:b*c?"d', "a_b_c_d"),
        ("Termocontraible 3760 _ 3779", "Termocontraible 3760_3779"),
        ("  .raro. ", "raro"),
        ("CON", "CON_"),
        ("", "sin_nombre"),
    ],
)
def test_sanear(entrada, esperado):
    assert sanear(entrada) == esperado


@pytest.mark.parametrize(
    "stem",
    [
        "WhatsApp Image 2026-03-01 at 10.22.11",
        "Captura de pantalla 2026-05-02 101010",
        "Sin título",
        "Gemini_Generated_Image_abc123",
        "ChatGPT Image 9 sept 2026, 09_33_05 a.m.",
        "highPower_Mesa-de-trabajo-1",
        "IMG_20260101_120000",
        "image",
        "images (3)",
        "3f9a1c7e2b4d6f8a0c1e",
        "aB3dE5fG7hJ9kL1mN3pQ5",
    ],
)
def test_genericos(stem):
    assert es_generico(stem)


@pytest.mark.parametrize("stem", ["3280", "1N5221B", "SL-TF5050-1E-W (2)", "CAPACITORES MOTOR AC CBB60", "tira pines", "TEMP-01", "medus_cc125_studio"])
def test_no_genericos(stem):
    assert not es_generico(stem)


@pytest.mark.parametrize(
    ("a", "b", "iguales"),
    [
        ("3722 (2)", "3722", True),
        ("SL-TF5050-1E-W (2)", "SL-TF5050-1E-W", True),
        ("antena - copia", "antena", True),
        ("b3", "B3", True),
        ("3276-BL", "3276-O", False),
        ("LED_12", "LED_24", False),
        ("in06", "in-06", False),
    ],
)
def test_clave(a, b, iguales):
    assert (clave(a) == clave(b)) is iguales


def test_clave_de_generico_es_none():
    assert clave("WhatsApp Image 2026-01-01") is None
    assert clave("D_NQ_NP_2X_649098-MLA95962637273_102025-F") is None


def test_nombre_unico_agrega_sufijo_de_hash():
    usados = {"conector"}
    assert nombre_unico("Conector", "a3f9c1ffff", usados) == "Conector_a3f9c1"
    assert nombre_unico("otro", "a3f9c1ffff", usados) == "otro"
    assert {"conector_a3f9c1", "otro"} <= usados
