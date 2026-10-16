"""Estructura de carpetas de la biblioteca (SDD §13)."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Biblioteca:
    root: Path

    @property
    def entrada(self) -> Path:
        return self.root / "entrada"

    @property
    def originales(self) -> Path:
        return self.root / "originales"

    @property
    def procesadas(self) -> Path:
        return self.root / "procesadas"

    @property
    def revisar(self) -> Path:
        return self.root / "_revisar"

    @property
    def reportes(self) -> Path:
        return self.root / "reportes"

    @property
    def inventario(self) -> Path:
        return self.root / "inventario.csv"

    @property
    def indice(self) -> Path:
        # Estado interno (hashes, grupos); no se edita a mano.
        return self.root / ".indice.json"

    def crear(self) -> None:
        for d in (self.entrada, self.originales, self.procesadas, self.revisar, self.reportes):
            d.mkdir(parents=True, exist_ok=True)
