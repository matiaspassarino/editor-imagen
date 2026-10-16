"""Saneado de nombres y detección de nombres genéricos (SDD §6.2)."""

import re
import unicodedata

_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SUFIJO_COPIA = re.compile(r"\s*\((\d+)\)$")
_COPIA_WINDOWS = re.compile(r"\s*\(\d+\)$|\s+-\s+(copia|copy)(\s*\(\d+\))?$", re.IGNORECASE)
_RESERVADOS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
LARGO_MAX = 100

_GENERICOS = re.compile(
    r"""^(
        whatsapp[\s_-]image | captura[\s_-]de[\s_-]pantalla | screenshot | screen[\s_-]shot
      | sin[\s_-]t[ií]tulo | untitled | gemini[\s_-]generated[\s_-]image | chatgpt[\s_-]image
      | img[\s_-]?\d | dsc[n_]?\d | pxl[\s_-]\d | photo[\s_-]?\d | descarga | download
      | (image|imagen|foto|images)[\s_-]?\d*$
      | D_N[QP]_N?P?_  # descargas de MercadoLibre
    )
    | mesa[\s_-]de[\s_-]trabajo
    """,
    re.IGNORECASE | re.VERBOSE,
)
_HEX = re.compile(r"[0-9a-f]{16,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def sanear(stem: str) -> str:
    """`SP-6305 _ SP-6306` → `SP-6305_SP-6306`; `SL-TF5050-1E-W (2)` → `SL-TF5050-1E-W_2`."""
    s = unicodedata.normalize("NFC", stem)
    s = _SUFIJO_COPIA.sub(r"_\1", s)
    s = _INVALIDOS.sub("_", s)
    s = re.sub(r"\s*_\s*", "_", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip(" ._")[:LARGO_MAX].rstrip(" ._")
    if s.upper() in _RESERVADOS:
        s += "_"
    return s or "sin_nombre"


def es_generico(stem: str) -> bool:
    s = _SUFIJO_COPIA.sub("", stem.strip())
    if _GENERICOS.search(s) or _HEX.fullmatch(s):
        return True
    # Cadenas aleatorias tipo id de CDN: largas, sin espacios, mezclan mayúsculas, minúsculas y dígitos.
    return (
        len(s) >= 20
        and re.fullmatch(r"[A-Za-z0-9_-]+", s) is not None
        and re.search(r"[a-z]", s) is not None
        and re.search(r"[A-Z]", s) is not None
        and re.search(r"\d", s) is not None
    )


def es_copia(stem: str) -> bool:
    return _COPIA_WINDOWS.search(stem.strip()) is not None


def clave(stem: str) -> str | None:
    """Nombre normalizado para comparar (`3722 (2)` ≈ `3722`); None si es genérico."""
    if es_generico(stem):
        return None
    s = stem.strip()
    while (t := _COPIA_WINDOWS.sub("", s)) != s:
        s = t
    return sanear(s).lower()


def nombre_unico(base: str, sha: str, usados: set[str]) -> str:
    """Si el nombre ya está tomado (sin distinguir mayúsculas), agrega un sufijo corto del hash."""
    nombre = base
    if nombre.lower() in usados:
        nombre = f"{base}_{sha[:6]}"
    n = 6
    while nombre.lower() in usados:
        n += 2
        nombre = f"{base}_{sha[:n]}"
    usados.add(nombre.lower())
    return nombre
