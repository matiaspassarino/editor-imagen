"""Pasos del pipeline (SDD §9). Cada uno recibe y modifica un `Contexto`."""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Contexto:
    rgb: np.ndarray  # color sin premultiplicar, float32 [0,1]
    alfa_original: np.ndarray | None = None  # transparencia que ya traía la foto
    alfa: np.ndarray | None = None  # máscara resultante
    alfa_referencia: np.ndarray | None = None  # máscara de BiRefNet general (para detectar reflejos)
    resolucion_origen: tuple[int, int] = (0, 0)  # ancho, alto
    factor_escala: float = 1.0
    upscale_modelo: bool = False  # si el agrandado usó Real-ESRGAN
    mejora_color: bool = False  # si se corrigió balance de blancos/exposición con el fondo
    mejora_exposicion: float = 1.0
    discrepancia: float | None = None  # QC: 1 − IoU entre el modelo y una detección simple del fondo
    segmentacion: str = ""  # modelo usado o "transparencia original"
    advertencias: list[str] = field(default_factory=list)
    piezas_grandes: int = 0
    reflejo_quitado: bool = False
    huecos_rellenos: int = 0
