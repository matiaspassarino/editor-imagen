"""Control de calidad básico (SDD §9.9). F3 suma la comparación contra una máscara por umbral."""

import cv2
import numpy as np

from editor_imagen.steps import Contexto

UPSCALE_MAX = 4.0
# Advertencias que se anotan pero no mandan la foto a revisar: en el catálogo real muchas fotos
# muestran varios productos a propósito y el recorte sale bien igual.
INFORMATIVAS = ("piezas grandes separadas", "reflejo quitado", "huecos rellenados")


def requiere_revision(advertencias: list[str]) -> bool:
    return any(not any(i in a for i in INFORMATIVAS) for a in advertencias)


def discrepancia_umbral(ctx: Contexto) -> float | None:
    """1 − IoU entre la máscara del modelo y una detección simple "todo lo que difiere del fondo".

    Solo tiene sentido con fondo blanco y parejo (si no, None). Queda solo como dato del reporte, sin aviso:
    en el catálogo, de las 13 fotos con valor más alto 12 eran productos blancos bien recortados (el umbral
    no los ve) y solo 1 tenía un problema real.
    """
    from editor_imagen.steps.enhance import _fondo

    fondo = _fondo(ctx)
    if fondo is None:
        return None
    dif = np.abs(ctx.rgb - fondo).max(axis=2)
    dif = cv2.GaussianBlur(dif, (0, 0), 2)
    simple = cv2.morphologyEx((dif > 0.1).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    modelo = ctx.alfa >= 0.5
    union = (simple | modelo).sum()
    if union == 0:
        return None
    return float(1 - (simple & modelo).sum() / union)


def controlar(ctx: Contexto) -> list[str]:
    a = ctx.alfa
    adv = []
    ctx.discrepancia = discrepancia_umbral(ctx)
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
    if ctx.reflejo_quitado:
        adv.append("reflejo quitado")
    if ctx.huecos_rellenos:
        adv.append(f"huecos rellenados ({ctx.huecos_rellenos}, placa con componentes)")
    if ctx.factor_escala > UPSCALE_MAX:
        adv.append(f"foto de origen chica: necesita agrandarse x{ctx.factor_escala:.1f}")
    return adv
