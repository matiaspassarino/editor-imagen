"""`editor procesar`: cola, reanudación, nombres de salida, reporte (SDD §10, §14)."""

import csv
import shutil
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import get_args

from editor_imagen import pipeline
from editor_imagen.config import Config, Proceso, Segmentacion
from editor_imagen.library import inventory, naming
from editor_imagen.library.biblioteca import Biblioteca
from editor_imagen.library.unify import Indice
from editor_imagen.steps import export, qc

GUARDAR_CADA = 20  # imágenes; si el lote se corta, se pierde como mucho esto
TERMINADOS = {"ok", "revisar"}
COLUMNAS_REPORTE = ["id", "nombre", "salida", "estado", "tiempo_ms", "resolucion_origen", "upscale_factor", "segmentacion", "advertencias", "error"]


@dataclass
class ResumenLote:
    candidatas: int = 0
    salteadas: int = 0
    por_estado: Counter = field(default_factory=Counter)
    segundos: float = 0.0
    reporte: Path | None = None


def codigos(fila: dict[str, str]) -> list[str]:
    return [c.strip() for c in fila["codigo"].replace(",", ";").split(";") if c.strip()]


def asignar_salidas(filas: list[dict[str, str]]) -> dict[str, list[str]]:
    """id → nombres de archivo de salida. `<codigo>.png` (uno por código) o `<nombre>.png` si no tiene.

    Los choques (dos fotos con el mismo código) se resuelven con `_2`, `_3`… y quien ya tenía un nombre lo conserva.
    """
    deseados = {f["id"]: [naming.sanear(c) for c in codigos(f)] or [f["nombre"]] for f in filas}
    previos = {f["id"]: {s.lower() for s in f["salida"].split(inventory.SEPARADOR_RUTAS) if s} for f in filas}
    usados: set[str] = set()
    asignados: dict[str, list[str]] = {i: [] for i in deseados}
    pendientes: list[tuple[str, str]] = []
    # Primera pasada: se respetan los nombres que cada foto ya tenía.
    for i in sorted(deseados):
        for base in deseados[i]:
            archivo = f"{base}.png"
            if archivo.lower() in previos[i] and archivo.lower() not in usados:
                usados.add(archivo.lower())
                asignados[i].append(archivo)
            else:
                pendientes.append((i, base))
    for i, base in pendientes:
        archivo, n = f"{base}.png", 2
        while archivo.lower() in usados:
            archivo, n = f"{base}_{n}.png", n + 1
        usados.add(archivo.lower())
        asignados[i].append(archivo)
    return asignados


def procesar(
    cfg: Config,
    filtro: Callable[[dict[str, str]], bool] = lambda f: True,
    forzar: bool = False,
    limite: int | None = None,
    avance: Callable[[int, int, str], None] | None = None,
) -> ResumenLote:
    bib = Biblioteca(cfg.biblioteca)
    bib.crear()
    inventory.verificar_escritura(bib.inventario)
    filas = inventory.cargar(bib.inventario)
    idx = Indice(bib.indice)
    salidas = asignar_salidas(filas)
    res = ResumenLote()

    elegidas = [f for f in filas if filtro(f)]
    cola = [f for f in elegidas if forzar or not (f["estado"] in TERMINADOS and f["procesado_con"] == _preset(cfg, f))]
    res.salteadas = len(elegidas) - len(cola)
    if limite is not None:
        cola = cola[:limite]
    res.candidatas = len(cola)

    bib.reportes.mkdir(exist_ok=True)
    res.reporte = bib.reportes / f"proceso_{datetime.now():%Y%m%d_%H%M%S}.csv"
    inicio = time.perf_counter()
    with open(res.reporte, "w", encoding="utf-8-sig", newline="") as frep:
        rep = csv.DictWriter(frep, fieldnames=COLUMNAS_REPORTE, delimiter=";")
        rep.writeheader()
        for n, fila in enumerate(cola):
            if avance:
                avance(n, len(cola), fila["nombre"])
            rep.writerow(_procesar_fila(fila, salidas[fila["id"]], idx, bib, cfg))
            frep.flush()
            res.por_estado[fila["estado"]] += 1
            if (n + 1) % GUARDAR_CADA == 0:
                inventory.guardar(bib.inventario, filas)
    inventory.guardar(bib.inventario, filas)
    res.segundos = time.perf_counter() - inicio
    return res


# Palabras de la columna `ajustes` → cambio sobre `proceso.segmentacion`.
AJUSTES = {
    "reflejo": {"quitar_reflejo": True},
    "sin-reflejo": {"quitar_reflejo": False},
    "relleno": {"rellenar_placas": True},
    "sin-relleno": {"rellenar_placas": False},
}


def _proceso(cfg: Config, fila: dict) -> Proceso:
    """Ajustes para esta foto: los de config.yaml, con las columnas `modelo` y `ajustes` aplicadas encima."""
    cambios: dict = {}
    modelo = fila.get("modelo", "").strip().lower()
    if modelo:
        validos = get_args(Segmentacion.model_fields["modelo"].annotation)
        if modelo not in validos:
            raise ValueError(f"modelo '{fila['modelo']}' no válido; opciones: {', '.join(validos)}")
        cambios["modelo"] = modelo
    for palabra in fila.get("ajustes", "").replace(";", ",").split(","):
        palabra = palabra.strip().lower()
        if not palabra:
            continue
        if palabra not in AJUSTES:
            raise ValueError(f"ajuste '{palabra}' no válido; opciones: {', '.join(AJUSTES)}")
        cambios.update(AJUSTES[palabra])
    if not cambios:
        return cfg.proceso
    seg = cfg.proceso.segmentacion.model_copy(update=cambios)
    return cfg.proceso.model_copy(update={"segmentacion": seg})


def _preset(cfg: Config, fila: dict) -> str:
    try:
        return pipeline.version_preset(_proceso(cfg, fila))
    except ValueError:
        return ""  # modelo inválido: nunca coincide, así se intenta y queda el error en el inventario


def _procesar_fila(fila: dict, nombres: list[str], idx: Indice, bib: Biblioteca, cfg: Config) -> dict:
    t0 = time.perf_counter()
    reg = {"id": fila["id"], "nombre": fila["nombre"], "salida": inventory.SEPARADOR_RUTAS.join(nombres)}
    try:
        grupo = idx.grupos.get(fila["id"])
        if grupo is None:
            raise FileNotFoundError("la foto no figura en el índice; correr `editor unificar`")
        origen = bib.originales / grupo["archivo"]
        proceso = _proceso(cfg, fila)
        preset = pipeline.version_preset(proceso)
        im, ctx = _con_reintento_gpu(lambda: pipeline.procesar(origen, proceso))

        for archivo in nombres:
            export.guardar(im, bib.procesadas / archivo, cfg.proceso.salida.dpi)
        anteriores = [s for s in fila["salida"].split(inventory.SEPARADOR_RUTAS) if s and s not in nombres]
        for viejo in anteriores:  # p. ej. se le cargó código y cambió el nombre de salida
            (bib.procesadas / viejo).unlink(missing_ok=True)
        for archivo in nombres + anteriores:
            (bib.revisar / archivo).unlink(missing_ok=True)
        revisar = qc.requiere_revision(ctx.advertencias)
        if revisar:
            for archivo in nombres:
                shutil.copy2(bib.procesadas / archivo, bib.revisar / archivo)

        fila.update(
            estado="revisar" if revisar else "ok",
            procesado_con=preset,
            salida=reg["salida"],
            advertencias="; ".join(ctx.advertencias),
        )
        reg.update(
            resolucion_origen="x".join(map(str, ctx.resolucion_origen)),
            upscale_factor=f"{ctx.factor_escala:.2f}",
            segmentacion=ctx.segmentacion,
            advertencias=fila["advertencias"],
        )
    except Exception as e:  # noqa: BLE001 — una imagen fallida no frena el lote (O7)
        fila.update(estado="error", advertencias=f"{type(e).__name__}: {e}")
        reg["error"] = fila["advertencias"]
    reg["estado"] = fila["estado"]
    reg["tiempo_ms"] = round((time.perf_counter() - t0) * 1000)
    return reg


def _con_reintento_gpu(fn):
    import torch

    try:
        return fn()
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return fn()
