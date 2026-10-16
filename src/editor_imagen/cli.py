"""CLI `editor` (SDD §13)."""

import platform
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from editor_imagen.config import DEFAULT_CONFIG, load_config

app = typer.Typer(help="Editor masivo de imágenes de producto — Industrias Sur", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    pass


@app.command()
def unificar(config: Path = typer.Option(DEFAULT_CONFIG, help="Archivo de configuración")) -> None:
    """Escanea fuentes + entrada, copia a la biblioteca y actualiza el inventario."""
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn

    from editor_imagen.library import inventory
    from editor_imagen.library.unify import unificar as _unificar

    cfg = load_config(config)
    if not cfg.fuentes:
        console.print("[yellow]No hay fuentes en config.yaml; solo se escanea la carpeta entrada.[/]")

    with Progress(TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn(), console=console) as prog:
        tarea = prog.add_task("Analizando", total=None)

        def avance(i: int, total: int, ruta: Path) -> None:
            prog.update(tarea, completed=i + 1, total=total, description=f"Analizando {ruta.name[:40]:<40}")

        try:
            res = _unificar(cfg, avance)
        except inventory.InventarioBloqueado as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(1)

    t = Table("", "", show_header=False)
    t.add_row("Archivos escaneados", str(res.archivos))
    if res.ignorados:
        t.add_row("Ignorados (no imagen)", ", ".join(f"{e} ×{n}" for e, n in res.ignorados.most_common()))
    t.add_row("Fotos únicas en biblioteca", f"[bold]{res.unicas}[/]")
    t.add_row("  nuevas en esta corrida", str(res.nuevas))
    if res.reemplazadas:
        t.add_row("  reemplazadas por mayor resolución", str(res.reemplazadas))
    t.add_row("Copias exactas descartadas", str(res.copias_exactas))
    t.add_row("Casi idénticas fusionadas", str(res.casi_identicas))
    t.add_row("Con parecidas sin fusionar", f"{res.con_parecidas} (ver columna 'parecidas')")
    t.add_row("Nombres genéricos", str(res.genericos))
    t.add_row("Ya transparentes", str(res.transparentes))
    t.add_row("Errores", f"[red]{len(res.errores)}[/]" if res.errores else "0")
    console.print(t)
    for ruta, err in res.errores:
        console.print(f"  [red]✗[/] {ruta}: {err}")
    console.print(f"Inventario: {cfg.biblioteca / 'inventario.csv'}")


@app.command()
def procesar(
    nombre: str = typer.Option(None, "--nombre", help="Solo fotos cuyo nombre o código contenga este texto"),
    estado: str = typer.Option(None, "--estado", help="Solo fotos con este estado (pendiente, ok, revisar, error)"),
    forzar: bool = typer.Option(False, "--forzar", help="Reprocesar aunque ya estén procesadas con el mismo preset"),
    limite: int = typer.Option(None, "--limite", help="Procesar como máximo N fotos"),
    config: Path = typer.Option(DEFAULT_CONFIG, help="Archivo de configuración"),
) -> None:
    """Procesa lo pendiente: quita el fondo y exporta PNG 1080×1080 transparente."""
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeRemainingColumn

    from editor_imagen import batch
    from editor_imagen.library import inventory

    cfg = load_config(config)
    texto = nombre.lower() if nombre else None

    def filtro(f: dict) -> bool:
        if texto and texto not in f["nombre"].lower() and texto not in f["codigo"].lower():
            return False
        return not estado or f["estado"] == estado

    with Progress(TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), TimeRemainingColumn(), console=console) as prog:
        tarea = prog.add_task("Cargando modelo…", total=None)

        def avance(i: int, total: int, actual: str) -> None:
            prog.update(tarea, completed=i, total=total, description=f"Procesando {actual[:40]:<40}")

        try:
            res = batch.procesar(cfg, filtro, forzar, limite, avance)
        except inventory.InventarioBloqueado as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(1)
        prog.update(tarea, completed=res.candidatas, total=max(res.candidatas, 1), description="Listo")

    t = Table("", "", show_header=False)
    t.add_row("Procesadas", f"[bold]{res.candidatas}[/]")
    t.add_row("  ok", f"[green]{res.por_estado['ok']}[/]")
    t.add_row("  revisar", f"[yellow]{res.por_estado['revisar']}[/] (copias en _revisar)")
    t.add_row("  error", f"[red]{res.por_estado['error']}[/]" if res.por_estado["error"] else "0")
    if res.salteadas:
        t.add_row("Ya procesadas (salteadas)", f"{res.salteadas} (usar --forzar para repetir)")
    if res.candidatas:
        t.add_row("Tiempo", f"{res.segundos:.0f} s ({res.segundos / res.candidatas:.2f} s por foto)")
    console.print(t)
    console.print(f"Salida: {cfg.biblioteca / 'procesadas'}")
    console.print(f"Reporte: {res.reporte}")


@app.command()
def estado(config: Path = typer.Option(DEFAULT_CONFIG, help="Archivo de configuración")) -> None:
    """Total, únicas, duplicados, pendientes, a revisar."""
    from editor_imagen.library.unify import estado as _estado

    e = _estado(load_config(config))
    t = Table("", "", show_header=False)
    t.add_row("Fotos únicas", f"[bold]{e.total}[/]")
    for nombre in ("pendiente", "ok", "revisar", "error"):
        t.add_row(f"  {nombre}", str(e.por_estado.get(nombre, 0)))
    t.add_row("Copias descartadas (duplicadas)", str(e.copias))
    t.add_row("Con parecidas sin fusionar", str(e.con_parecidas))
    t.add_row("Sin código", str(e.sin_codigo))
    t.add_row("  con nombre genérico", str(e.genericos))
    t.add_row("Ya transparentes", str(e.transparentes))
    console.print(t)


@app.command()
def check(
    config: Path = typer.Option(DEFAULT_CONFIG, help="Archivo de configuración"),
    sin_modelos: bool = typer.Option(False, "--sin-modelos", help="No descargar ni probar modelos"),
) -> None:
    """Verifica GPU, modelos y configuración."""
    table = Table("Ítem", "Estado", "Detalle")
    ok = True

    def row(item: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok &= passed
        table.add_row(item, "[green]OK[/]" if passed else "[red]FALLA[/]", detail)

    row("Python", sys.version_info[:2] == (3, 12), f"{platform.python_version()}")

    try:
        cfg = load_config(config)
        row("Configuración", True, str(config.name))
    except Exception as e:  # noqa: BLE001
        row("Configuración", False, str(e).splitlines()[0])
        cfg = None

    if cfg is not None:
        lib = cfg.biblioteca
        try:
            lib.mkdir(parents=True, exist_ok=True)
            probe = lib / ".check"
            probe.write_text("ok")
            probe.unlink()
            row("Biblioteca", True, str(lib))
        except OSError as e:
            row("Biblioteca", False, f"{lib}: {e}")
        missing = [str(f) for f in cfg.fuentes if not f.is_dir()]
        row("Fuentes", not missing, f"{len(cfg.fuentes)} configuradas" + (f"; no existen: {', '.join(missing)}" if missing else ""))

    import torch

    cuda = torch.cuda.is_available()
    if cuda:
        props = torch.cuda.get_device_properties(0)
        row("GPU", True, f"{props.name}, {props.total_memory / 2**30:.1f} GB, CUDA {torch.version.cuda}, torch {torch.__version__}")
    else:
        row("GPU", False, f"CUDA no disponible (torch {torch.__version__}); se usaría CPU")

    if not sin_modelos:
        from editor_imagen.models import registry

        sondas = [
            ("BiRefNet dynamic", lambda r: _probe_birefnet(r, "birefnet-dynamic")),
            ("BiRefNet DIS5K", lambda r: _probe_birefnet(r, "birefnet-dis")),
            ("Real-ESRGAN x2plus", lambda r: _probe_upscaler(r, "realesrgan-x2plus")),
            ("Real-ESRGAN x4plus", lambda r: _probe_upscaler(r, "realesrgan-x4plus")),
        ]
        for name, fn in sondas:
            with console.status(f"Probando {name} (la primera vez descarga los pesos)…"):
                try:
                    detail = fn(registry)
                    row(name, True, detail)
                except Exception as e:  # noqa: BLE001
                    row(name, False, f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}")

    console.print(table)
    raise typer.Exit(0 if ok else 1)


def _vram_peak() -> str:
    import torch

    if not torch.cuda.is_available():
        return ""
    peak = torch.cuda.max_memory_allocated() / 2**30
    torch.cuda.reset_peak_memory_stats()
    return f", VRAM pico {peak:.2f} GB"


def _probe_birefnet(registry, nombre: str) -> str:
    import torch

    model, entrada = registry.birefnet(nombre)
    dtype = next(model.parameters()).dtype
    x = torch.rand(1, 3, entrada, entrada, device=registry.device(), dtype=dtype)
    with torch.inference_mode():
        model(x)  # calentamiento
        t = time.perf_counter()
        out = model(x)[-1].sigmoid()
        if x.is_cuda:
            torch.cuda.synchronize()
    ms = (time.perf_counter() - t) * 1000
    return f"{registry.device()}, {ms:.0f} ms a {entrada} px{_vram_peak()}"


def _probe_upscaler(registry, nombre: str) -> str:
    import torch

    model = registry.upscaler(nombre)
    dtype = next(model.model.parameters()).dtype
    x = torch.rand(1, 3, 256, 256, device=registry.device(), dtype=dtype)
    with torch.inference_mode():
        t = time.perf_counter()
        out = model(x)
        if x.is_cuda:
            torch.cuda.synchronize()
    ms = (time.perf_counter() - t) * 1000
    return f"{registry.device()}, escala x{model.scale}, {ms:.0f} ms 256→{out.shape[-1]} px{_vram_peak()}"
