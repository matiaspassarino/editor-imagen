# Manual de usuario — Editor masivo de imágenes de producto

Herramienta local para unificar las fotos de productos de Industrias Sur, quitarles el fondo y exportar una imagen estándar por producto: **PNG 1080 × 1080, fondo transparente, 300 DPI**, que sirve tanto para el catálogo impreso como para web y redes.

Todo corre en esta PC (usa la placa de video). No sube nada a internet.

---

## 1. Uso rápido

1. Abrí la carpeta del proyecto `C:\Users\Usuario Ventas\Desktop\editor de imagen` en el Explorador.
2. Hacé clic en la barra de direcciones, escribí `cmd` y apretá Enter. Se abre una terminal ya ubicada en esa carpeta.
3. Escribí los comandos:

```
editor unificar      ← incorpora las fotos nuevas a la biblioteca
editor procesar      ← quita el fondo y exporta lo pendiente
editor revisar       ← abre la pantalla de revisión en el navegador
editor estado        ← muestra cuántas hay, cuántas faltan, cuántas revisar
```

Las imágenes terminadas quedan en **`C:\imagenes editadas\procesadas`**.

> En PowerShell o en la terminal de VS Code, anteponé `.\`: `.\editor procesar`.

---

## 2. El trabajo de todos los días

### Agregar fotos nuevas

Dejá las fotos en cualquiera de estos dos lugares:

- `C:\imagenes editadas\entrada`, o
- cualquier subcarpeta de `C:\Users\Usuario Ventas\Desktop\FOTOS PRODCUTOS` (el nombre de la subcarpeta queda como categoría en el inventario).

Formatos aceptados: JPG, PNG, WEBP, HEIC (iPhone/Android), AVIF, BMP, TIFF. Los PDF, ZIP, etc. se ignoran.

Para fotos nuevas con el celular, seguí la guía de captura (sección 9).

### Incorporarlas y procesarlas

```
editor unificar
editor procesar
```

- `unificar` solo incorpora lo nuevo. Si una foto ya estaba (aunque tenga otro nombre o esté en otra carpeta) la reconoce y no la duplica. Si llega una versión de mayor resolución de una foto existente, reemplaza la anterior y la vuelve a marcar como pendiente.
- `procesar` solo procesa lo pendiente. Lo que ya está hecho se saltea.
- Tus fotos originales **nunca se mueven ni se modifican**: se trabaja sobre copias.

Tiempo de referencia: ~1 segundo por foto. El catálogo completo (~960 fotos) tarda unos 15 minutos.

### Revisar el resultado

La forma más cómoda es la **pantalla de revisión**:

```
editor revisar
```

Se abre en el navegador (dirección `http://127.0.0.1:7860`, solo en esta PC). Para cerrarla, cerrá la ventana de la terminal o apretá Ctrl+C.

- **Izquierda:** galería filtrable por estado (arranca en `revisar`), carpeta, texto o "solo sin código". Las que tienen ⚠ están para revisar o con error.
- **Derecha:** al hacer clic en una foto se ve el original y el resultado. El resultado se puede ver sobre fondo gris, blanco, negro o azul, para detectar bordes o halos.
- **Código y descripción:** se completan ahí mismo. **Guardar** los anota en el inventario; si cambia el código, la foto se reprocesa sola para renombrar la salida.
- **Modelo de recorte y ajustes** ("Quitar reflejo", "No rellenar huecos"): elegí y apretá **Reprocesar**. En ~1 segundo se ve el resultado nuevo (la primera vez tarda unos segundos más porque carga los modelos).
- **Marcar OK:** la foto sale de `revisar` (y de la carpeta `_revisar`).
- **◀ Anterior / Siguiente ▶** recorre las fotos del filtro actual.

No hace falta cerrar la pantalla para usar Excel, pero **no edites el inventario en Excel mientras la pantalla está guardando**, y cerrá Excel antes de guardar desde la pantalla.

También se puede revisar a mano:

- Todo lo procesado: `C:\imagenes editadas\procesadas`.
- Lo que conviene mirar: `C:\imagenes editadas\_revisar` (copias de las que tuvieron alguna advertencia; ver sección 5).
- Cada corrida deja un reporte en `C:\imagenes editadas\reportes`.

---

## 3. Comandos

| Comando | Qué hace |
|---|---|
| `editor unificar` | Escanea las carpetas fuente y `entrada`, copia lo nuevo a la biblioteca y actualiza el inventario |
| `editor procesar` | Procesa todo lo pendiente |
| `editor estado` | Resumen: total, pendientes, ok, a revisar, errores, sin código |
| `editor revisar` | Abre la pantalla de revisión en el navegador (ver sección 2) |
| `editor check` | Verifica que la placa de video, los modelos y la configuración estén bien |

Opciones de `procesar` (se pueden combinar):

| Opción | Ejemplo | Para qué |
|---|---|---|
| `--nombre TEXTO` | `editor procesar --nombre 3280` | Solo fotos cuyo nombre o código contenga ese texto |
| `--estado ESTADO` | `editor procesar --estado revisar` | Solo fotos en ese estado (`pendiente`, `ok`, `revisar`, `error`) |
| `--forzar` | `editor procesar --nombre conector --forzar` | Rehacer aunque ya estén procesadas |
| `--limite N` | `editor procesar --limite 20` | Procesar como máximo N (para probar rápido) |

Para ver la ayuda: `editor --help` o `editor procesar --help`.

---

## 4. El inventario (`C:\imagenes editadas\inventario.csv`)

Es una planilla con una fila por foto única. Se abre con doble clic en Excel.

### Columnas que podés editar

| Columna | Para qué |
|---|---|
| `codigo` | Código interno del producto. Si está cargado, la salida se llama `<codigo>.png` en vez del nombre de la foto. Si la misma foto sirve para varios códigos, separalos con `;` (ej. `3280;3281`) y se genera una copia por código |
| `descripcion` | Texto libre |
| `modelo` | Para forzar otro modelo de recorte en esa foto (ver sección 6). Vacío = el normal |
| `ajustes` | Correcciones puntuales para esa foto, separadas por coma: `reflejo` (quitar el reflejo sobre la mesa), `sin-relleno` (no completar huecos). Ver sección 6 |
| `estado` | Poné `pendiente` para que `procesar` la vuelva a hacer |

Lo que cargues a mano **se conserva** aunque vuelvas a correr `unificar` o `procesar`.

### Cómo guardarlo

- Guardá con **Archivo → Guardar** y aceptá mantener el formato CSV.
- **Cerralo en Excel antes de correr `unificar` o `procesar`**: si está abierto, el programa avisa y no hace nada.

### Columnas informativas

| Columna | Significado |
|---|---|
| `nombre` | Nombre de la foto en la biblioteca (saneado) |
| `carpeta` | Subcarpeta de origen (categoría) |
| `ruta_original` | De dónde salió la foto |
| `ancho`, `alto` | Resolución original |
| `transparente` | `sí` si la foto ya venía sin fondo (se respeta su recorte) |
| `copias` / `duplicados` | Cuántas fotos iguales se encontraron y dónde |
| `parecidas` | Otras fotos casi idénticas con distinto nombre (variantes de color, misma foto para otro código). No se fusionan: cada una tiene su salida |
| `nombre_generico` | `sí` si el archivo se llamaba "WhatsApp Image…", "Gemini…", "Captura…", etc. Son las primeras a las que conviene cargarles el código |
| `estado` | `pendiente`, `ok`, `revisar` o `error` |
| `procesado_con` | Versión y ajustes con que se procesó |
| `salida` | Archivo(s) generados en `procesadas` |
| `advertencias` | Lo que detectó el control de calidad (sección 5) |

---

## 5. Advertencias y estados

| Advertencia | ¿Manda a revisar? | Qué significa |
|---|---|---|
| producto toca el borde de la foto | Sí | En la foto original el producto está cortado (cables, patas). El programa no puede inventar lo que falta |
| foto de origen chica: necesita agrandarse xN | Sí | La foto original es muy chica; puede verse borrosa. Conviene sacar una nueva |
| máscara casi vacía / ocupa casi toda la foto | Sí | El recorte probablemente salió mal |
| N piezas grandes separadas | No | La foto muestra varios productos. Normal en el catálogo |
| reflejo quitado | No | Se quitó el reflejo del producto sobre la mesa (solo en fotos con `reflejo` en `ajustes`) |
| huecos rellenados (placa con componentes) | No | Se completó una placa blanca que el modelo veía solo como LEDs sueltos |

Estado `error`: la foto no se pudo procesar (archivo dañado, o no se encontró ningún producto). El motivo queda en `advertencias`. El resto del lote sigue normalmente.

---

## 6. Si una foto sale mal

Lo más simple es hacerlo desde la pantalla de revisión (`editor revisar`): elegís la foto, cambiás el modelo o tildás un ajuste y apretás **Reprocesar**. Lo mismo se puede hacer desde el inventario:

1. **Probá otro modelo de recorte** para esa foto: en el inventario, columna `modelo`, escribí uno de estos valores, guardá y corré `editor procesar` (se rehace sola):

   | Valor | Cuándo probarlo |
   |---|---|
   | `birefnet` | El modelo original. Suele ir mejor cuando aparece un reflejo o una sombra que no debería |
   | `birefnet-dynamic` | Carcasas blancas, reflejos de luz, productos con texto |
   | `birefnet-dis` | Placas y objetos blancos que se pierden contra el fondo |
   | `combinado` | El normal (une dynamic + dis) |

2. **Si el producto aparece con su reflejo sobre la mesa** (típico de renders o fotos sobre vidrio/acrílico): en la columna `ajustes` escribí `reflejo`, guardá y corré `editor procesar`. No está activado para todas las fotos porque confunde dos filas de productos o los mangos de una pinza con un reflejo.

3. **Si se rellenó un hueco que debía quedar vacío** (placa con un agujero real, logo): en `ajustes` escribí `sin-relleno`.

4. **Si la foto es muy chica o está muy comprimida**, la mejor solución es una foto nueva siguiendo la guía de la sección 9.

5. **Si el problema se repite en varias fotos**, anotá los nombres: suele haber un patrón que se puede corregir para todas.

---

## 7. Carpetas

### Biblioteca (`C:\imagenes editadas`)

```
entrada\        fotos nuevas a incorporar
originales\     copias de las fotos fuente (una por foto única) — no editar
procesadas\     PNG 1080×1080 transparentes  ← el resultado
_revisar\       copias de las procesadas con advertencias
reportes\       un CSV por corrida de procesar
inventario.csv  la planilla
.indice.json    datos internos (oculto) — no editar ni borrar
.miniaturas\    miniaturas de la pantalla de revisión (se regeneran solas)
```

### Proyecto (`C:\Users\Usuario Ventas\Desktop\editor de imagen`)

```
editor.cmd      atajo para correr el programa
config.yaml     configuración
docs\           este manual y el documento de diseño (SDD.md)
models\         modelos de IA descargados (~2 GB)
src\, tests\    código
```

---

## 8. Configuración (`config.yaml`)

Se edita con el Bloc de notas. Las opciones más útiles:

```yaml
fuentes:                        # carpetas que se escanean (se pueden agregar más)
  - "C:/Users/Usuario Ventas/Desktop/FOTOS PRODCUTOS"

proceso:
  segmentacion:
    modelo: combinado           # modelo de recorte por defecto
    usar_transparencia_existente: true   # respetar fotos que ya vienen sin fondo
    quitar_reflejo: false       # para todas las fotos: NO recomendado (usar la columna ajustes)
    rellenar_placas: true       # completar placas blancas con LEDs
  upscale:
    modo: conservative          # agrandado de fotos chicas con IA: off | conservative | standard
  salida:
    tamano: 1080                # lado del cuadrado en píxeles
    margen: 0.04                # margen por lado (4 %)
    dpi: 300
```

Al cambiar cualquier ajuste de `proceso`, la próxima vez que corras `procesar` se rehacen todas las fotos con los ajustes nuevos.

Las rutas van con barras `/` y entre comillas.

---

## 9. Guía para sacar fotos nuevas (Redmi Note 13 Pro+)

1. **Fondo:** cartulina blanca mate en curva (sin pliegue entre base y fondo).
2. **Luz:** natural indirecta o dos lámparas difusas a los costados. Sin flash.
3. **Cámara:** principal, **sin** modo 200 MP, sin filtros ni "belleza".
4. **Distancia:** para piezas chicas, alejarse 25–30 cm y usar zoom 2x.
5. **Enfoque:** tocar el producto; bajar un poco la exposición si el blanco se quema.
6. **Encuadre:** producto completo, centrado, con aire alrededor. Un producto por foto.
7. **Estabilidad:** apoyar el celular o usar trípode.
8. **Nombre:** renombrar la foto con el código interno y dejarla en `C:\imagenes editadas\entrada`.

Evitá superficies brillantes (vidrio, acrílico): generan reflejos.

---

## 10. Prueba de impresión

Genera un PDF A4 apaisado con productos en las 4 áreas de imagen de la card (41×22, 43×55, 45×45 y 83×55 mm) a tamaño real, con instrucciones y una regla de 100 mm para controlar la escala:

```
uv run --with reportlab python scripts/prueba_impresion.py
```

Sin nombres usa 12 casos difíciles. Para elegir otros productos, agregá sus nombres (columna `nombre` del inventario):

```
uv run --with reportlab python scripts/prueba_impresion.py 3280 in02 "CAPACITORES MOTOR AC CBB60"
```

El PDF queda en `C:\imagenes editadas\reportes\prueba_impresion_<fecha>.pdf`. Imprimilo al **100 %** (sin "ajustar a la página").

---

## 11. Problemas frecuentes

| Problema | Solución |
|---|---|
| `"editor" no se reconoce como un comando` | La terminal no está en la carpeta del proyecto (ver sección 1). Si estás en la carpeta correcta, escribilo con `.\` adelante: `.\editor procesar` (algunas configuraciones de Windows lo exigen) |
| `inventario.csv está abierto en otro programa` | Cerrá el archivo en Excel y volvé a correr el comando |
| No se puede borrar un archivo en `originales` o `procesadas` | Windows lo tiene abierto (vista previa del Explorador, antivirus). Esperá un momento o cerrá la ventana del Explorador |
| Muy lento (varios segundos por foto) | Corré `editor check`: si la GPU figura como "FALLA" se está usando el procesador. Reiniciar la PC suele resolverlo |
| Se cortó en el medio (corte de luz, se cerró la ventana) | Volvé a correr `editor procesar`: sigue desde donde quedó |
| Quiero rehacer todo | `editor procesar --forzar` |

---

## 12. Instalar en otra PC

Requisitos: Windows 10/11, placa NVIDIA (recomendado), ~5 GB libres, conexión a internet para la instalación.

1. Instalar `uv`: `py -m pip install --user uv` (o desde https://docs.astral.sh/uv/).
2. Clonar el repositorio: `git clone https://github.com/matiaspassarino/editor-imagen`.
3. En la carpeta del proyecto: `uv sync` (instala Python 3.12 y todas las dependencias).
4. `editor check` (descarga los modelos la primera vez y verifica todo).
5. Revisar `config.yaml` (rutas de la biblioteca y de las fuentes).
