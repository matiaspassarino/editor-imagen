"""Inventario CSV editable en Excel (SDD §6.3).

Se escribe con `;` y UTF-8 con BOM, que es lo que Excel en español abre directo. Al leer se acepta
también lo que guarde Excel (`,` o `;`, UTF-8 o ANSI).
"""

import csv
import io
import os
from pathlib import Path

COLUMNAS = [
    "id",
    "nombre",
    "codigo",
    "descripcion",
    "carpeta",
    "ruta_original",
    "ancho",
    "alto",
    "transparente",
    "copias",
    "duplicados",
    "parecidas",
    "nombre_generico",
    "estado",
    "procesado_con",
    "advertencias",
]
# Campos que no se recalculan al re-ejecutar `unificar`.
CONSERVADOS = ["codigo", "descripcion", "estado", "procesado_con", "advertencias"]
SEPARADOR_RUTAS = " | "


class InventarioBloqueado(Exception):
    pass


def _decodificar(datos: bytes) -> str:
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("cp1252")


def cargar(ruta: Path) -> list[dict[str, str]]:
    if not ruta.exists():
        return []
    texto = _decodificar(ruta.read_bytes())
    encabezado = texto.split("\n", 1)[0]
    delim = ";" if encabezado.count(";") >= encabezado.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto, newline=""), delimiter=delim)
    return [{c: (fila.get(c) or "").strip() for c in COLUMNAS} for fila in lector if fila.get("id")]


def verificar_escritura(ruta: Path) -> None:
    """Falla temprano si el inventario está abierto en Excel."""
    if ruta.exists():
        try:
            with open(ruta, "r+b"):
                pass
        except PermissionError as e:
            raise InventarioBloqueado(f"{ruta} está abierto en otro programa (¿Excel?). Cerralo y volvé a intentar.") from e


def guardar(ruta: Path, filas: list[dict[str, str]]) -> None:
    verificar_escritura(ruta)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    os.replace(tmp, ruta)
