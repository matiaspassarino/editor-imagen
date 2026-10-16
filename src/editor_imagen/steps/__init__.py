"""Pasos del pipeline (SDD §9). Cada uno recibe y modifica un `Contexto`."""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Contexto:
    rgb: np.ndarray  # color sin premultiplicar, float32 [0,1]
    alfa_original: np.ndarray | None = None  # transparencia que ya traía la foto
    alfa: np.ndarray | None = None  # máscara resultante
    resolucion_origen: tuple[int, int] = (0, 0)  # ancho, alto
    factor_escala: float = 1.0
    segmentacion: str = ""  # modelo usado o "transparencia original"
    advertencias: list[str] = field(default_factory=list)
    piezas_grandes: int = 0
