"""Pipeline de una imagen (SDD §9): carga → segmentación → refinado → encuadre → control.

El upscale (Real-ESRGAN) ocurre dentro del encuadre, sobre el recorte del producto. La corrección de color
va antes del encuadre (necesita el fondo como referencia) y el enfoque al final, sobre la imagen 1080.
"""

import hashlib
import json
from pathlib import Path

from PIL import Image

from editor_imagen import __version__
from editor_imagen.config import Proceso
from editor_imagen.steps import Contexto, enhance, export, frame, load, qc, reflection, refine, segment


def version_preset(proceso: Proceso) -> str:
    """Identifica versión del programa + ajustes: si cambia cualquiera, las fotos vuelven a procesarse."""
    ajustes = json.dumps(proceso.model_dump(mode="json"), sort_keys=True)
    return f"{__version__}+{hashlib.sha1(ajustes.encode()).hexdigest()[:6]}"


def procesar(ruta: Path, proceso: Proceso) -> tuple[Image.Image, Contexto]:
    ctx = load.cargar(ruta)
    segment.segmentar(ctx, proceso.segmentacion)
    if proceso.segmentacion.quitar_reflejo:
        reflection.quitar_reflejo(ctx)
    refine.refinar(ctx, proceso.segmentacion)
    enhance.corregir_color(ctx, proceso.mejora)
    rgb, alfa = frame.encuadrar(ctx, proceso.salida, proceso.upscale.modo)
    # Menos enfoque si el agrandado con IA ya dio nitidez.
    rgb = enhance.enfocar(rgb, alfa, proceso.mejora.nitidez * (0.5 if ctx.upscale_modelo else 1.0))
    ctx.advertencias = qc.controlar(ctx)
    return export.a_imagen(rgb, alfa), ctx
