"""`editor unificar`: escaneo → hash → agrupación → copia → inventario (SDD §6.1)."""

import glob
import json
import os
import shutil
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from editor_imagen.config import Config
from editor_imagen.library import dedup, hashing, inventory, naming, scan
from editor_imagen.library.biblioteca import Biblioteca

VERSION_INDICE = 1


@dataclass
class Resumen:
    archivos: int = 0
    ignorados: Counter = field(default_factory=Counter)
    errores: list[tuple[str, str]] = field(default_factory=list)
    unicas: int = 0
    nuevas: int = 0
    reemplazadas: int = 0
    copias_exactas: int = 0
    casi_identicas: int = 0  # fotos distintas fusionadas por ser casi iguales y de nombre compatible
    con_parecidas: int = 0  # fotos que tienen parecidas sin fusionar
    genericos: int = 0
    transparentes: int = 0


class Indice:
    """Estado interno en `.indice.json`.

    - archivos: ruta → {tamano, mtime, sha}  (evita releer archivos sin cambios)
    - hashes:   sha  → {ancho, alto, transparente, phash, bytes, rutas, id}
    - grupos:   id   → {rep: sha, archivo: nombre del archivo en originales/}
    """

    def __init__(self, ruta: Path):
        self.ruta = ruta
        data = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        self.archivos: dict[str, dict] = data.get("archivos", {})
        self.hashes: dict[str, dict] = data.get("hashes", {})
        self.grupos: dict[str, dict] = data.get("grupos", {})

    def guardar(self) -> None:
        tmp = self.ruta.with_suffix(".tmp")
        data = {"version": VERSION_INDICE, "archivos": self.archivos, "hashes": self.hashes, "grupos": self.grupos}
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.ruta)


def _carpeta(ruta: Path, fuente: Path, bib: Biblioteca) -> str:
    if bib.entrada.resolve() in ruta.parents:
        return "entrada"
    rel = ruta.parent.relative_to(fuente)
    return rel.as_posix() if rel.parts else ""


def _pixeles(h: dict) -> tuple[int, int]:
    return (h["ancho"] * h["alto"], h["bytes"])


def _mejor_nombre(rutas_rep: list[str], otras: list[str]) -> Path:
    """El nombre más útil del grupo: no genérico, sin sufijo de copia (` (2)`, ` - copia`), y si no la representante."""
    candidatas = [Path(r) for r in rutas_rep + sorted(otras)]
    return min(candidatas, key=lambda p: (naming.es_generico(p.stem), naming.es_copia(p.stem)))


def unificar(cfg: Config, avance: Callable[[int, int, Path], None] | None = None) -> Resumen:
    bib = Biblioteca(cfg.biblioteca)
    bib.crear()
    inventory.verificar_escritura(bib.inventario)
    idx = Indice(bib.indice)
    filas = {f["id"]: f for f in inventory.cargar(bib.inventario)}
    res = Resumen()

    # 1. Escaneo
    fuentes = [Path(f) for f in cfg.fuentes] + [bib.entrada]
    esc = scan.escanear(fuentes, excluir=bib.root.resolve(), permitir=bib.entrada.resolve())
    res.archivos = len(esc.imagenes) + sum(esc.ignorados.values())
    res.ignorados = esc.ignorados

    # 2. Hashes (con caché por tamaño + fecha de modificación)
    rutas_por_sha: dict[str, list[str]] = defaultdict(list)
    fuente_de: dict[str, Path] = {}
    archivos_vigentes: dict[str, dict] = {}
    for i, a in enumerate(esc.imagenes):
        if avance:
            avance(i, len(esc.imagenes), a.ruta)
        clave = str(a.ruta)
        try:
            cache = idx.archivos.get(clave)
            if cache and cache["tamano"] == a.tamano and cache["mtime"] == a.mtime:
                sha = cache["sha"]
            else:
                sha = hashing.sha256(a.ruta)
            if sha not in idx.hashes:
                idx.hashes[sha] = {**hashing.analizar(a.ruta), "bytes": a.tamano, "rutas": [], "id": None}
        except Exception as e:  # noqa: BLE001 — un archivo roto no frena el resto
            res.errores.append((clave, f"{type(e).__name__}: {e}"))
            continue
        archivos_vigentes[clave] = {"tamano": a.tamano, "mtime": a.mtime, "sha": sha}
        rutas_por_sha[sha].append(clave)
        fuente_de[clave] = a.fuente
    idx.archivos = archivos_vigentes
    for sha, rutas in rutas_por_sha.items():
        idx.hashes[sha]["rutas"] = sorted(rutas)

    # 3. Agrupación (incluye hashes de corridas anteriores aunque su fuente ya no exista)
    ids = {sha: h.get("id") for sha, h in idx.hashes.items()}

    def nombres(sha: str) -> set[str]:
        return {c for r in idx.hashes[sha]["rutas"] if (c := naming.clave(Path(r).stem))}

    grupos, vinculos = dedup.agrupar(idx.hashes, cfg.dedup.phash_umbral, ids, nombres)
    usados = {Path(g["archivo"]).stem.lower() for g in idx.grupos.values()}

    # 4. Copia a originales/ y armado de filas
    for grupo in sorted(grupos, key=lambda g: min((r for s in g for r in idx.hashes[s]["rutas"]), default="")):
        presentes = [s for s in grupo if rutas_por_sha.get(s)]
        mejor = max(presentes, key=lambda s: _pixeles(idx.hashes[s])) if presentes else None
        gid = next((ids[s] for s in grupo if ids.get(s)), None)
        advertencia = ""

        if gid is None or gid not in idx.grupos:
            if mejor is None:
                continue
            gid = gid or f"i{mejor[:11]}"
            origen = Path(rutas_por_sha[mejor][0])
            otras = [r for s in grupo if s != mejor for r in rutas_por_sha.get(s, [])]
            base = _mejor_nombre(rutas_por_sha[mejor], otras).stem
            nombre = naming.sanear(base)
            archivo = nombre + origen.suffix.lower()
            existente = bib.originales / archivo
            if existente.exists() and nombre.lower() not in usados and hashing.sha256(existente) == mejor:
                usados.add(nombre.lower())  # quedó de una corrida anterior (p. ej. índice borrado): se reutiliza
            else:
                # Nunca se pisa un archivo que ya esté en originales/ aunque no figure en el índice.
                ocupados = usados | {p.stem.lower() for p in bib.originales.glob(f"{glob.escape(nombre)}*")}
                nombre = naming.nombre_unico(nombre, mejor, ocupados)
                usados.add(nombre.lower())
                archivo = nombre + origen.suffix.lower()
                shutil.copy2(origen, bib.originales / archivo)
            idx.grupos[gid] = {"rep": mejor, "archivo": archivo}
            res.nuevas += 1
        else:
            g = idx.grupos[gid]
            actual = g["rep"]
            if mejor and mejor != actual and _pixeles(idx.hashes[mejor]) > _pixeles(idx.hashes[actual]):
                origen = Path(rutas_por_sha[mejor][0])
                archivo = Path(g["archivo"]).stem + origen.suffix.lower()
                tmp = bib.originales / (archivo + ".tmp")
                shutil.copy2(origen, tmp)
                (bib.originales / g["archivo"]).unlink(missing_ok=True)
                os.replace(tmp, bib.originales / archivo)
                g.update(rep=mejor, archivo=archivo)
                res.reemplazadas += 1
                advertencia = "original reemplazado por una versión de mayor resolución"

        for s in grupo:
            idx.hashes[s]["id"] = gid

        g = idx.grupos[gid]
        rep = idx.hashes[g["rep"]]
        rutas_rep = rep["rutas"]
        ruta_original = rutas_rep[0] if rutas_rep else filas.get(gid, {}).get("ruta_original", "")
        casi = [r for s in grupo if s != g["rep"] for r in idx.hashes[s]["rutas"]]
        duplicados = rutas_rep[1:] + casi
        fuente = fuente_de.get(ruta_original)
        generico = naming.es_generico(Path(g["archivo"]).stem)

        anterior = filas.get(gid, {})
        fila = {
            "id": gid,
            "nombre": Path(g["archivo"]).stem,
            "carpeta": _carpeta(Path(ruta_original), fuente, bib) if fuente else anterior.get("carpeta", ""),
            "ruta_original": ruta_original,
            "ancho": str(rep["ancho"]),
            "alto": str(rep["alto"]),
            "transparente": "sí" if rep["transparente"] else "no",
            "copias": str(1 + len(duplicados)),
            "duplicados": inventory.SEPARADOR_RUTAS.join(duplicados),
            "parecidas": "",
            "nombre_generico": "sí" if generico else "no",
            **{c: anterior.get(c, "") for c in inventory.CONSERVADOS},
        }
        fila["estado"] = fila["estado"] or "pendiente"
        if advertencia:
            fila["estado"] = "pendiente"
            fila["advertencias"] = advertencia
        filas[gid] = fila

        res.copias_exactas += sum(max(len(idx.hashes[s]["rutas"]) - 1, 0) for s in grupo)
        res.casi_identicas += len(grupo) - 1
        res.genericos += generico
        res.transparentes += rep["transparente"]

    # Parecidas: casi idénticas con nombres distintos (variantes de color, misma foto para varios códigos).
    parecidas: dict[str, set[str]] = defaultdict(set)
    for a, b in vinculos:
        ga, gb = idx.hashes[a]["id"], idx.hashes[b]["id"]
        if ga in filas and gb in filas and ga != gb:
            parecidas[ga].add(filas[gb]["nombre"])
            parecidas[gb].add(filas[ga]["nombre"])
    for gid, nombres_parecidos in parecidas.items():
        filas[gid]["parecidas"] = inventory.SEPARADOR_RUTAS.join(sorted(nombres_parecidos, key=str.lower))
    res.con_parecidas = len(parecidas)

    res.unicas = len(filas)
    # El índice va primero: si el inventario falla (Excel abierto), la próxima corrida lo regenera sin recopiar.
    idx.guardar()
    orden = sorted(filas.values(), key=lambda f: (f["carpeta"].lower(), f["nombre"].lower()))
    inventory.guardar(bib.inventario, orden)
    return res


@dataclass
class Estado:
    total: int
    por_estado: Counter
    copias: int
    con_parecidas: int
    genericos: int
    sin_codigo: int
    transparentes: int


def estado(cfg: Config) -> Estado:
    filas = inventory.cargar(Biblioteca(cfg.biblioteca).inventario)
    return Estado(
        total=len(filas),
        por_estado=Counter(f["estado"] or "pendiente" for f in filas),
        copias=sum(int(f["copias"] or 1) - 1 for f in filas),
        con_parecidas=sum(bool(f["parecidas"]) for f in filas),
        genericos=sum(f["nombre_generico"] == "sí" for f in filas),
        sin_codigo=sum(not f["codigo"] for f in filas),
        transparentes=sum(f["transparente"] == "sí" for f in filas),
    )
