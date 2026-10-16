"""UI web local de revisión (F4): galería antes/después, edición y reproceso de una foto.

Toda la lógica está en `editor_imagen.review`; acá solo se arma la pantalla.
"""

import os

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # 100 % local: sin telemetría

import gradio as gr

from editor_imagen.config import Config
from editor_imagen.review import CASILLAS, ESTADOS, FONDOS, Revision

POR_PAGINA = 48
MODELOS = ["(el de config.yaml)", "combinado", "birefnet", "birefnet-dynamic", "birefnet-dis"]


def crear_app(cfg: Config) -> gr.Blocks:
    rev = Revision(cfg)

    # ---------- funciones ----------

    def listar(estado, carpeta, texto, sin_codigo, pagina):
        filas = rev.filtrar(rev.filas(), estado, carpeta, texto, sin_codigo)
        ids = [f["id"] for f in filas]
        paginas = max(1, (len(ids) + POR_PAGINA - 1) // POR_PAGINA)
        pagina = min(max(0, pagina), paginas - 1)
        galeria, ids_pagina = [], []
        for f in filas[pagina * POR_PAGINA : (pagina + 1) * POR_PAGINA]:
            mini = rev.miniatura(f)
            if mini:
                marca = "⚠ " if f["estado"] in ("revisar", "error") else ""
                galeria.append((str(mini), f"{marca}{f['codigo'] or f['nombre']}"[:40]))
                ids_pagina.append(f["id"])
        resumen = f"**{len(ids)}** fotos · página {pagina + 1} de {paginas}"
        return galeria, ids, pagina, resumen, ids_pagina

    def detalle(id_, fondo):
        f = rev.fila(id_) if id_ else None
        if f is None:
            vacio = gr.update(value="")
            return None, None, "_Elegí una foto de la galería._", vacio, vacio, MODELOS[0], [], ""
        info = [
            f"### {f['nombre']}",
            f"**Estado:** {f['estado'] or 'pendiente'} · **Carpeta:** {f['carpeta'] or '—'} · **Original:** {f['ancho']}×{f['alto']} px",
            f"**Salida:** {f['salida'] or '—'}",
        ]
        if f["advertencias"]:
            info.append(f"**Advertencias:** {f['advertencias']}")
        if f["parecidas"]:
            info.append(f"**Parecidas:** {f['parecidas']}")
        modelo = f["modelo"] if f["modelo"] in MODELOS else MODELOS[0]
        return (
            rev.original(f),
            rev.resultado(f, fondo),
            "\n\n".join(info),
            f["codigo"],
            f["descripcion"],
            modelo,
            rev.casillas(f),
            "",
        )

    def elegir(ids_pagina, fondo, evt: gr.SelectData):
        id_ = ids_pagina[evt.index] if evt.index < len(ids_pagina) else None
        return (id_, *detalle(id_, fondo))

    def mover(id_, ids, delta, fondo):
        if not ids:
            return (id_, *detalle(id_, fondo))
        i = ids.index(id_) if id_ in ids else -1
        nuevo = ids[min(max(0, i + delta), len(ids) - 1)]
        return (nuevo, *detalle(nuevo, fondo))

    def guardar(id_, codigo, descripcion, modelo, casillas, fondo, progreso=gr.Progress()):
        if not id_:
            return (*detalle(id_, fondo)[:-1], "Elegí una foto primero.")
        modelo = "" if modelo == MODELOS[0] else modelo
        _, cambio = rev.guardar(id_, codigo, descripcion, modelo, casillas)
        msg = "Guardado."
        if cambio:
            progreso(0.3, desc="Reprocesando (la primera vez carga los modelos)…")
            f = rev.reprocesar(id_)
            msg = f"Guardado y reprocesado → **{f['estado']}**."
        return (*detalle(id_, fondo)[:-1], msg)

    def reprocesar(id_, codigo, descripcion, modelo, casillas, fondo, progreso=gr.Progress()):
        if not id_:
            return (*detalle(id_, fondo)[:-1], "Elegí una foto primero.")
        modelo = "" if modelo == MODELOS[0] else modelo
        rev.guardar(id_, codigo, descripcion, modelo, casillas)
        progreso(0.3, desc="Reprocesando (la primera vez carga los modelos)…")
        f = rev.reprocesar(id_)
        return (*detalle(id_, fondo)[:-1], f"Reprocesado → **{f['estado']}**.")

    def marcar_ok(id_, fondo):
        if not id_:
            return (*detalle(id_, fondo)[:-1], "Elegí una foto primero.")
        rev.marcar_ok(id_)
        return (*detalle(id_, fondo)[:-1], "Marcada como **ok**.")

    # ---------- pantalla ----------

    with gr.Blocks(title="Revisión de imágenes — Industrias Sur") as app:
        ids_filtrados = gr.State([])
        ids_pagina = gr.State([])
        pagina = gr.State(0)
        actual = gr.State(None)

        gr.Markdown("## Revisión de imágenes de producto")
        with gr.Row():
            with gr.Column(scale=5):
                with gr.Row():
                    estado = gr.Radio(ESTADOS, value="revisar", label="Estado")
                    sin_codigo = gr.Checkbox(label="Solo sin código")
                with gr.Row():
                    carpeta = gr.Dropdown([""] + rev.carpetas(), value="", label="Carpeta", allow_custom_value=False)
                    texto = gr.Textbox(label="Buscar (nombre, código o descripción)")
                resumen = gr.Markdown()
                galeria = gr.Gallery(columns=6, height=620, allow_preview=False, object_fit="contain", show_label=False)
                with gr.Row():
                    btn_ant_pag = gr.Button("◀ Página anterior", size="sm")
                    btn_sig_pag = gr.Button("Página siguiente ▶", size="sm")
            with gr.Column(scale=6):
                with gr.Row():
                    img_original = gr.Image(label="Original", interactive=False, height=380)
                    img_resultado = gr.Image(label="Resultado", interactive=False, height=380)
                fondo = gr.Radio(list(FONDOS), value="gris", label="Fondo para ver el resultado")
                info = gr.Markdown("_Elegí una foto de la galería._")
                with gr.Row():
                    codigo = gr.Textbox(label="Código (varios: 3280;3281)")
                    descripcion = gr.Textbox(label="Descripción")
                with gr.Row():
                    modelo = gr.Dropdown(MODELOS, value=MODELOS[0], label="Modelo de recorte")
                    casillas = gr.CheckboxGroup(list(CASILLAS), label="Ajustes")
                with gr.Row():
                    btn_guardar = gr.Button("Guardar", variant="secondary")
                    btn_reprocesar = gr.Button("Reprocesar", variant="primary")
                    btn_ok = gr.Button("Marcar OK")
                estado_msg = gr.Markdown()
                with gr.Row():
                    btn_ant = gr.Button("◀ Anterior")
                    btn_sig = gr.Button("Siguiente ▶")

        filtros = [estado, carpeta, texto, sin_codigo]
        salida_lista = [galeria, ids_filtrados, pagina, resumen, ids_pagina]
        salida_detalle = [img_original, img_resultado, info, codigo, descripcion, modelo, casillas, estado_msg]
        editables = [actual, codigo, descripcion, modelo, casillas, fondo]

        def recargar(*args):
            return listar(*args, 0)

        for comp in (estado, carpeta, sin_codigo):
            comp.change(recargar, filtros, salida_lista)
        texto.submit(recargar, filtros, salida_lista)
        app.load(recargar, filtros, salida_lista)
        btn_ant_pag.click(lambda *a: listar(*a[:-1], a[-1] - 1), filtros + [pagina], salida_lista)
        btn_sig_pag.click(lambda *a: listar(*a[:-1], a[-1] + 1), filtros + [pagina], salida_lista)

        galeria.select(elegir, [ids_pagina, fondo], [actual] + salida_detalle)
        fondo.change(detalle, [actual, fondo], salida_detalle)
        btn_ant.click(lambda i, ids, f: mover(i, ids, -1, f), [actual, ids_filtrados, fondo], [actual] + salida_detalle)
        btn_sig.click(lambda i, ids, f: mover(i, ids, 1, f), [actual, ids_filtrados, fondo], [actual] + salida_detalle)

        btn_guardar.click(guardar, editables, salida_detalle)
        btn_reprocesar.click(reprocesar, editables, salida_detalle)
        btn_ok.click(marcar_ok, [actual, fondo], salida_detalle)
        # Tras editar, refrescar la galería (cambian miniatura, estado y código).
        for btn in (btn_guardar, btn_reprocesar, btn_ok):
            btn.click(lambda *a: listar(*a), filtros + [pagina], salida_lista)

    return app


def lanzar(cfg: Config, puerto: int = 7860) -> None:
    app = crear_app(cfg)
    app.queue(default_concurrency_limit=1)  # una operación a la vez: el inventario y la GPU son compartidos
    app.launch(inbrowser=True, server_name="127.0.0.1", server_port=puerto, allowed_paths=[str(cfg.biblioteca)])
