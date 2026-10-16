"""Agrupación de duplicados exactos y casi idénticos (SDD §6.1 paso 3).

El pHash compara en escala de grises: no distingue variantes de color (`3276-BL` / `3276-O`) ni la
misma foto reutilizada para códigos distintos (`3202` / `3203`). Por eso dos fotos casi idénticas
solo se fusionan si sus nombres no se contradicen; si no, quedan separadas y vinculadas como parecidas.
"""

import math
from collections.abc import Callable

import numpy as np

TOLERANCIA_ASPECTO = 0.05  # diferencia máxima de log(ancho/alto) para considerar dos fotos iguales


def agrupar(
    hashes: dict[str, dict],
    umbral: int,
    ids: dict[str, str | None],
    nombres: Callable[[str], set[str]],
) -> tuple[list[list[str]], set[tuple[str, str]]]:
    """Devuelve (grupos de SHA-256, pares de grupos parecidos no fusionados).

    - `ids`: grupos ya existentes en la biblioteca; dos grupos existentes nunca se fusionan,
      para no perder los datos cargados a mano en ninguno de los dos.
    - `nombres(sha)`: nombres informativos normalizados de ese archivo (vacío si son genéricos).
      Dos grupos se fusionan solo si comparten un nombre o alguno no tiene nombre informativo.
    """
    shas = sorted(hashes)
    padre = {s: s for s in shas}
    gid = {s: ids.get(s) for s in shas}
    nom = {s: set(nombres(s)) for s in shas}
    bloqueados: list[tuple[str, str]] = []

    def raiz(s: str) -> str:
        while padre[s] != s:
            padre[s] = padre[padre[s]]
            s = padre[s]
        return s

    def unir(a: str, b: str) -> None:
        ra, rb = raiz(a), raiz(b)
        if ra == rb:
            return
        if (gid[ra] and gid[rb] and gid[ra] != gid[rb]) or (nom[ra] and nom[rb] and not nom[ra] & nom[rb]):
            bloqueados.append((a, b))
            return
        padre[rb] = ra
        gid[ra] = gid[ra] or gid[rb]
        nom[ra] |= nom[rb]

    if umbral > 0 and len(shas) > 1:
        ph = np.array([int(hashes[s]["phash"], 16) for s in shas], dtype=np.uint64)
        aspecto = np.array([math.log(hashes[s]["ancho"] / hashes[s]["alto"]) for s in shas])
        # Imágenes casi uniformes dan pHash degenerado y chocarían entre sí.
        bits = np.bitwise_count(ph)
        validos = (bits > 4) & (bits < 60)
        pares = []
        for i in range(len(shas) - 1):
            if not validos[i]:
                continue
            dist = np.bitwise_count(ph[i] ^ ph[i + 1 :])
            similares = (dist <= umbral) & validos[i + 1 :] & (np.abs(aspecto[i + 1 :] - aspecto[i]) < TOLERANCIA_ASPECTO)
            pares += [(int(dist[j]), shas[i], shas[i + 1 + j]) for j in np.nonzero(similares)[0]]
        # Primero los más parecidos, para que la fusión no dependa del orden alfabético de los hashes.
        for _, a, b in sorted(pares):
            unir(a, b)

    grupos: dict[str, list[str]] = {}
    for s in shas:
        grupos.setdefault(raiz(s), []).append(s)
    vinculos = {tuple(sorted((raiz(a), raiz(b)))) for a, b in bloqueados if raiz(a) != raiz(b)}
    return list(grupos.values()), vinculos
