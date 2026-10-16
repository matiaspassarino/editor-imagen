"""PDF de prueba de impresión (SDD §15): productos en las 4 áreas de imagen de la card, a tamaño real.

Uso (desde la carpeta del proyecto):
    uv run --with reportlab python scripts/prueba_impresion.py [nombre1 nombre2 ...]

Sin nombres usa una selección de casos difíciles. El PDF queda en C:\\imagenes editadas\\reportes.
"""

import csv
import sys
from datetime import date
from pathlib import Path

from reportlab.lib.colors import Color, black, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from editor_imagen.config import load_config  # noqa: E402

AREAS = [(41, 22), (43, 55), (45, 45), (83, 55)]  # ancho × alto en mm (SDD §2)
PX = 1080
CASOS = [
    ("1N5221B", "patas finas"),
    ("1786456588049", "LED: patas finas, fondo gris"),
    ("3036", "plug 3,5 mm metálico"),
    ("CAPACITORES MOTOR AC CBB60", "texto, producto blanco"),
    ("0X450VAC-CAB", "texto, cables"),
    ("2N3055", "texto en metal"),
    ("in02", "blanco sobre blanco, texto chico"),
    ("SPOTLED-R7W-W_SPOTLED-C7W-WW", "carcasa blanca"),
    ("AR-111W-5050", "placa blanca con LEDs"),
    ("3722", "cables finos"),
    ("sw", "foto chica agrandada x4,8"),
    ("10", "foto chica agrandada x3, texto"),
]
GRIS_LINEA = Color(0.6, 0.6, 0.6)
GRIS_FONDO = Color(0.9, 0.9, 0.9)
MARGEN = 12 * mm
SEP = 7 * mm
FILA = 92 * mm
POR_PAGINA = 2


def dpi_efectivo(ancho_mm: float, alto_mm: float) -> int:
    return round(PX / (min(ancho_mm, alto_mm) / 25.4))


def portada(c: canvas.Canvas, ancho: float, alto: float, n: int) -> None:
    y = alto - MARGEN - 8 * mm
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGEN, y, "Prueba de impresión — imágenes de producto")
    c.setFont("Helvetica", 10)
    c.drawString(MARGEN, y - 7 * mm, f"Industrias Sur · {date.today():%d/%m/%Y} · {n} productos · PNG 1080×1080 transparente, 300 DPI")
    titulos = {"CÓMO IMPRIMIR", "QUÉ MIRAR (con lupa o de cerca)"}
    lineas = [
        "CÓMO IMPRIMIR",
        "  • Escala 100 % / \"Tamaño real\". Desactivar \"Ajustar a la página\".",
        "  • Mejor calidad de la impresora y el papel que se use para el catálogo.",
        "  • Verificar la escala con la regla de abajo: tiene que medir exactamente 100 mm.",
        "",
        "QUÉ MIRAR (con lupa o de cerca)",
        "  • Bordes: sin halo blanco ni sombra oscura alrededor del producto (el área de 83×55 tiene fondo gris para que se note).",
        "  • Estructuras finas: patas, cables y resortes completos y nítidos, sin cortes.",
        "  • Textos y serigrafías: legibles en el área más chica (41×22 mm).",
        "  • Colores: parecidos al producto real.",
        "  • Fotos agrandadas (las dos últimas): sin aspecto \"pintado\" ni pixelado.",
        "",
        "Cada recuadro es el área de imagen de la card. La imagen cuadrada entra por el lado más corto (SDD §5.1);",
        "debajo figura la resolución efectiva con que queda impresa (el estándar de imprenta es 300 DPI).",
    ]
    c.setFont("Helvetica", 10)
    yy = y - 20 * mm
    for linea in lineas:
        if linea in titulos:
            c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGEN, yy, linea)
        c.setFont("Helvetica", 10)
        yy -= 5.5 * mm
    # Regla de 100 mm
    yr = yy - 10 * mm
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(MARGEN, yr, MARGEN + 100 * mm, yr)
    for i in range(0, 101, 5):
        largo = 4 * mm if i % 10 == 0 else 2 * mm
        c.line(MARGEN + i * mm, yr, MARGEN + i * mm, yr + largo)
        if i % 10 == 0:
            c.setFont("Helvetica", 7)
            c.drawCentredString(MARGEN + i * mm, yr + 5 * mm, str(i))
    c.setFont("Helvetica", 9)
    c.drawString(MARGEN + 103 * mm, yr, "← tiene que medir 100 mm")


def fila(c: canvas.Canvas, y_top: float, nombre: str, nota: str, png: Path) -> None:
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGEN, y_top, nombre[:60])
    c.setFont("Helvetica", 9)
    c.drawString(MARGEN + c.stringWidth(nombre[:60], "Helvetica-Bold", 10) + 4 * mm, y_top, f"— {nota}")
    x = MARGEN
    base = y_top - 4 * mm - 55 * mm  # todas las áreas alineadas abajo
    for i, (w, h) in enumerate(AREAS):
        W, H = w * mm, h * mm
        y0 = base
        if i == len(AREAS) - 1:
            c.setFillColor(GRIS_FONDO)
            c.rect(x, y0, W, H, stroke=0, fill=1)
        lado = min(W, H)
        c.drawImage(str(png), x + (W - lado) / 2, y0 + (H - lado) / 2, lado, lado, mask="auto")
        c.setStrokeColor(GRIS_LINEA)
        c.setLineWidth(0.25)
        c.setDash(1, 1.5)
        c.rect(x, y0, W, H, stroke=1, fill=0)
        c.setDash()
        c.setFillColor(black)
        c.setFont("Helvetica", 7)
        c.drawString(x, y0 - 3.5 * mm, f"{w}×{h} mm · ~{dpi_efectivo(w, h)} DPI")
        x += W + SEP


def main() -> None:
    cfg = load_config()
    inv = {f["nombre"]: f for f in csv.DictReader(open(cfg.biblioteca / "inventario.csv", encoding="utf-8-sig"), delimiter=";")}
    pedidos = [(n, "") for n in sys.argv[1:]] or CASOS
    casos = []
    for nombre, nota in pedidos:
        f = inv.get(nombre)
        if not f or not f["salida"]:
            print(f"  (salteado, no está procesado: {nombre})")
            continue
        casos.append((nombre, nota or f["advertencias"][:60], cfg.biblioteca / "procesadas" / f["salida"].split(" | ")[0]))

    destino = cfg.biblioteca / "reportes" / f"prueba_impresion_{date.today():%Y%m%d}.pdf"
    ancho, alto = landscape(A4)
    c = canvas.Canvas(str(destino), pagesize=(ancho, alto))
    c.setTitle("Prueba de impresión — imágenes de producto")
    c.setAuthor("Industrias Sur")
    portada(c, ancho, alto, len(casos))
    c.showPage()
    for p in range(0, len(casos), POR_PAGINA):
        y = alto - MARGEN - 4 * mm
        for nombre, nota, png in casos[p : p + POR_PAGINA]:
            fila(c, y, nombre, nota, png)
            y -= FILA
        c.setFont("Helvetica", 7)
        c.setFillColor(black)
        c.drawRightString(ancho - MARGEN, MARGEN / 2, f"Página {p // POR_PAGINA + 2} · imprimir al 100 %")
        c.showPage()
    c.save()
    print(destino)


if __name__ == "__main__":
    main()
