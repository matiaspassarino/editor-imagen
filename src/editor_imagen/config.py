"""Carga y validación de config.yaml (SDD §12)."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


class Dedup(BaseModel):
    phash_umbral: int = Field(4, ge=0, le=64)


class Segmentacion(BaseModel):
    modelo: Literal["combinado", "birefnet", "birefnet-dynamic", "birefnet-dis", "rembg-isnet"] = "combinado"
    usar_transparencia_existente: bool = True
    quitar_sombra: bool = True
    refinar_bordes: bool = True


class Restauracion(BaseModel):
    artefactos_jpeg: bool = True
    ruido: float = Field(0.3, ge=0, le=1)


class Upscale(BaseModel):
    modo: Literal["conservative", "standard", "off"] = "conservative"


class Mejora(BaseModel):
    balance_blancos: bool = True
    contraste: float = Field(0.3, ge=0, le=1)
    nitidez: float = Field(0.3, ge=0, le=1)


class Salida(BaseModel):
    tamano: int = Field(1080, gt=0)
    margen: float = Field(0.04, ge=0, lt=0.5)
    dpi: int = Field(300, gt=0)


class Proceso(BaseModel):
    segmentacion: Segmentacion = Segmentacion()
    restauracion: Restauracion = Restauracion()
    upscale: Upscale = Upscale()
    mejora: Mejora = Mejora()
    salida: Salida = Salida()


class Config(BaseModel):
    biblioteca: Path = Path("C:/imagenes editadas")
    fuentes: list[Path] = []
    dedup: Dedup = Dedup()
    proceso: Proceso = Proceso()


def load_config(path: Path = DEFAULT_CONFIG) -> Config:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config.model_validate(data)
