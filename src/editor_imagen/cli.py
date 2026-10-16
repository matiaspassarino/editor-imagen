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

        for name, fn in (("BiRefNet", _probe_birefnet), ("Real-ESRGAN x4plus", _probe_upscaler)):
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


def _probe_birefnet(registry) -> str:
    import torch

    model = registry.birefnet()
    dtype = next(model.parameters()).dtype
    x = torch.rand(1, 3, 1024, 1024, device=registry.device(), dtype=dtype)
    with torch.inference_mode():
        model(x)  # calentamiento
        t = time.perf_counter()
        out = model(x)[-1].sigmoid()
        if x.is_cuda:
            torch.cuda.synchronize()
    ms = (time.perf_counter() - t) * 1000
    return f"{registry.device()}, salida {tuple(out.shape[-2:])}, {ms:.0f} ms a 1024 px{_vram_peak()}"


def _probe_upscaler(registry) -> str:
    import torch

    model = registry.upscaler()
    x = torch.rand(1, 3, 256, 256, device=registry.device())
    with torch.inference_mode():
        t = time.perf_counter()
        out = model(x)
        if x.is_cuda:
            torch.cuda.synchronize()
    ms = (time.perf_counter() - t) * 1000
    return f"{registry.device()}, escala x{model.scale}, {ms:.0f} ms 256→{out.shape[-1]} px{_vram_peak()}"
