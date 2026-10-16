"""Escaneo recursivo de carpetas fuente (SDD §6.1 paso 1)."""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ARCHIVOS_SISTEMA = {"thumbs.db", "desktop.ini", ".ds_store"}
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif", ".bmp", ".tif", ".tiff"}


@dataclass
class Archivo:
    ruta: Path
    fuente: Path
    tamano: int
    mtime: float


@dataclass
class Escaneo:
    imagenes: list[Archivo] = field(default_factory=list)
    ignorados: Counter = field(default_factory=Counter)  # extensión -> cantidad


def _dentro(ruta: Path, carpeta: Path) -> bool:
    return ruta == carpeta or carpeta in ruta.parents


def escanear(fuentes: list[Path], excluir: Path | None = None, permitir: Path | None = None) -> Escaneo:
    """Recorre las fuentes. Se saltea `excluir` (la biblioteca) salvo lo que esté dentro de `permitir` (entrada)."""
    res = Escaneo()
    vistos: set[Path] = set()
    for fuente in fuentes:
        fuente = fuente.resolve()
        if not fuente.is_dir():
            continue
        for p in sorted(fuente.rglob("*")):
            if not p.is_file() or p in vistos:
                continue
            if excluir and _dentro(p, excluir) and not (permitir and _dentro(p, permitir)):
                continue
            vistos.add(p)
            if p.name.lower() in ARCHIVOS_SISTEMA:
                continue
            ext = p.suffix.lower()
            if ext not in EXTENSIONES:
                res.ignorados[ext or "(sin extensión)"] += 1
                continue
            st = p.stat()
            res.imagenes.append(Archivo(p, fuente, st.st_size, st.st_mtime))
    return res
