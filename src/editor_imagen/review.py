"""Operaciones de revisión (F4), independientes de la interfaz: filtrar, miniaturas, editar, reprocesar."""

from pathlib import Path

from PIL import Image

from editor_imagen import batch
from editor_imagen.config import Config
from editor_imagen.library import inventory
from editor_imagen.library.biblioteca import Biblioteca
from editor_imagen.library.hashing import abrir
from editor_imagen.library.unify import Indice

ESTADOS = ["todas", "revisar", "ok", "pendiente", "error"]
FONDOS = {"gris": (128, 128, 128), "blanco": (255, 255, 255), "negro": (0, 0, 0), "azul": (35, 85, 155)}
MINIATURA = 220
# Casillas de la UI ↔ palabras de la columna `ajustes`.
CASILLAS = {"Quitar reflejo": "reflejo", "No rellenar huecos": "sin-relleno"}


class Revision:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.bib = Biblioteca(cfg.biblioteca)
        self.dir_miniaturas = self.bib.root / ".miniaturas"
        self.dir_miniaturas.mkdir(exist_ok=True)

    # --- lectura ---------------------------------------------------------------------------------------

    def filas(self) -> list[dict[str, str]]:
        return inventory.cargar(self.bib.inventario)

    def fila(self, id_: str) -> dict[str, str] | None:
        return next((f for f in self.filas() if f["id"] == id_), None)

    def carpetas(self) -> list[str]:
        return sorted({f["carpeta"] for f in self.filas()}, key=str.lower)

    @staticmethod
    def filtrar(filas: list[dict], estado: str, carpeta: str, texto: str, sin_codigo: bool) -> list[dict]:
        texto = (texto or "").strip().lower()
        out = []
        for f in filas:
            if estado and estado != "todas" and f["estado"] != estado:
                continue
            if carpeta and f["carpeta"] != carpeta:
                continue
            if sin_codigo and f["codigo"]:
                continue
            if texto and texto not in f["nombre"].lower() and texto not in f["codigo"].lower() and texto not in f["descripcion"].lower():
                continue
            out.append(f)
        return out

    def salida(self, fila: dict) -> Path | None:
        nombre = fila["salida"].split(inventory.SEPARADOR_RUTAS)[0] if fila["salida"] else ""
        ruta = self.bib.procesadas / nombre
        return ruta if nombre and ruta.exists() else None

    def miniatura(self, fila: dict) -> Path | None:
        """JPG chico sobre gris, regenerado si la salida cambió."""
        salida = self.salida(fila)
        if salida is None:
            return None
        mini = self.dir_miniaturas / f"{fila['id']}.jpg"
        if not mini.exists() or mini.stat().st_mtime < salida.stat().st_mtime:
            im = Image.open(salida).convert("RGBA")
            im.thumbnail((MINIATURA, MINIATURA), Image.LANCZOS)
            fondo = Image.new("RGBA", im.size, FONDOS["gris"] + (255,))
            Image.alpha_composite(fondo, im).convert("RGB").save(mini, quality=85)
        return mini

    def original(self, fila: dict, lado: int = 700) -> Image.Image | None:
        grupo = Indice(self.bib.indice).grupos.get(fila["id"])
        if grupo is None:
            return None
        im = abrir(self.bib.originales / grupo["archivo"]).convert("RGBA")
        im.thumbnail((lado, lado), Image.LANCZOS)
        return Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("RGB")

    def resultado(self, fila: dict, fondo: str, lado: int = 700) -> Image.Image | None:
        salida = self.salida(fila)
        if salida is None:
            return None
        im = Image.open(salida).convert("RGBA").resize((lado, lado), Image.LANCZOS)
        return Image.alpha_composite(Image.new("RGBA", im.size, FONDOS.get(fondo, FONDOS["gris"]) + (255,)), im).convert("RGB")

    @staticmethod
    def casillas(fila: dict) -> list[str]:
        palabras = {p.strip().lower() for p in fila["ajustes"].replace(";", ",").split(",")}
        return [c for c, p in CASILLAS.items() if p in palabras]

    # --- escritura ---------------------------------------------------------------------------------------

    def _actualizar(self, id_: str, **cambios: str) -> dict[str, str]:
        """Relee el inventario, cambia una fila y lo guarda (el lote o Excel pueden haberlo tocado)."""
        filas = self.filas()
        fila = next(f for f in filas if f["id"] == id_)
        fila.update(cambios)
        inventory.guardar(self.bib.inventario, filas)
        return fila

    def guardar(self, id_: str, codigo: str, descripcion: str, modelo: str, casillas: list[str]) -> tuple[dict, bool]:
        """Guarda los campos editables. Devuelve (fila, hay_que_reprocesar)."""
        anterior = self.fila(id_)
        # Se conservan las palabras de `ajustes` que no tienen casilla en la UI.
        otras = [p.strip() for p in anterior["ajustes"].replace(";", ",").split(",") if p.strip() and p.strip().lower() not in CASILLAS.values()]
        ajustes = ", ".join(otras + [CASILLAS[c] for c in casillas])
        fila = self._actualizar(id_, codigo=codigo.strip(), descripcion=descripcion.strip(), modelo=modelo or "", ajustes=ajustes)
        cambio = any(anterior[c] != fila[c] for c in ("codigo", "modelo", "ajustes"))
        return fila, cambio

    def reprocesar(self, id_: str) -> dict[str, str]:
        batch.procesar(self.cfg, filtro=lambda f: f["id"] == id_, forzar=True, con_reporte=False)
        return self.fila(id_)

    def marcar_ok(self, id_: str) -> dict[str, str]:
        fila = self._actualizar(id_, estado="ok")
        for archivo in fila["salida"].split(inventory.SEPARADOR_RUTAS):
            if archivo:
                (self.bib.revisar / archivo).unlink(missing_ok=True)
        return fila
