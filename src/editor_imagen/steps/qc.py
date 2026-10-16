"""Control de calidad básico (SDD §9.9). F3 suma la comparación contra una máscara por umbral."""

import numpy as np

from editor_imagen.steps import Contexto

UPSCALE_MAX = 4.0
# Advertencias que se anotan pero no mandan la foto a revisar: en el catálogo real muchas fotos
# muestran varios productos a propósito y el recorte sale bien igual.
INFORMATIVAS = ("piezas grandes separadas",)


def requiere_revision(advertencias: list[str]) -> bool:
    return any(not any(i in a for i in INFORMATIVAS) for a in advertencias)


def controlar(ctx: Contexto) -> list[str]:
    a = ctx.alfa
    adv = []
    cobertura = float((a > 0.5).mean())
    if cobertura < 0.005:
        adv.append("máscara casi vacía")
    elif cobertura > 0.95:
        adv.append("máscara ocupa casi toda la foto")
    borde = np.concatenate([a[:2].ravel(), a[-2:].ravel(), a[:, :2].ravel(), a[:, -2:].ravel()])
    if (borde > 0.5).mean() > 0.02:
        adv.append("producto toca el borde de la foto (posible recorte)")
    if ctx.piezas_grandes > 1:
        adv.append(f"{ctx.piezas_grandes} piezas grandes separadas")
    if ctx.factor_escala > UPSCALE_MAX:
        adv.append(f"foto de origen chica: necesita agrandarse x{ctx.factor_escala:.1f}")
    return adv
