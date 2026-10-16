# SDD — Editor masivo de imágenes de producto

| Campo | Valor |
|---|---|
| Versión | 0.5 |
| Fecha | 2026-10-16 |
| Autor | Matías Passa |
| Estado | F0–F3 cerradas; próximo F4 (UI de revisión) |

### Historial
| Versión | Cambios |
|---|---|
| 0.1 | Borrador inicial |
| 0.2 | Destinos, tipo de producto, volumen, origen de fotos |
| 0.3 | Medidas de cards, módulo Biblioteca |
| 0.4 | **Simplificación:** una única salida (PNG 1080×1080 transparente, 300 DPI). Se descarta la detección automática de SKU por regex (los nombres reales no siguen un patrón); se reemplaza por inventario editable. Biblioteca en `C:\imagenes editadas`. Vinculación con códigos diferida al módulo de productos del CRM de Industrias Sur |
| 0.5 | F1 contra las fotos reales: el pHash no distingue variantes de color ni la misma foto usada para varios códigos → las casi idénticas solo se fusionan si el nombre es compatible; las demás se vinculan en `parecidas`. Columnas nuevas `carpeta`, `transparente`, `copias`, `parecidas`. Inventario con `;` y UTF-8 BOM para Excel |

---

## 1. Propósito

Herramienta de uso personal para procesar **lotes grandes de fotos de productos eléctricos y electrónicos** (desde resistencias y fotocontroles hasta paneles LED): unificar las fotos dispersas en una biblioteca, quitar el fondo, mejorar la calidad y exportar **una imagen cuadrada transparente de 1080×1080** que sirve tanto para el catálogo impreso como para web y redes.

## 2. Contexto

| Aspecto | Situación |
|---|---|
| Catálogo | ~5.000 productos; la mayoría son variantes de un mismo producto base |
| Fotos existentes | Fondo blanco, baja calidad, repartidas en varias carpetas |
| Nombres de archivo | Sin convención: números de parte (`1N5221B`, `SL-TF5050-1E-W (2)`), códigos internos (`3803`), descripciones (`CAPACITORES MOTOR AC CBB60`, `tira pines`), varios productos en un nombre (`SP-6305 _ SP-6306`) y nombres automáticos (`WhatsApp Image…`, `Captura de pantalla…`, `Sin título`, `Gemini_Generated_Image…`, cadenas aleatorias) |
| Código de producto | Código interno numérico (ej. `Cód: 3280` en la card) |
| Fotos nuevas | Redmi Note 13 Pro+ 5G |
| Composición | Un solo producto por foto |
| Catálogo impreso | Área de imagen en la card: 41×22, 43×55, 45×45 u 83×55 mm. Textos, código y precio van aparte |
| Web / redes | Se usan como base para publicidades sobre fondos propios |
| Volumen | Lotes de ≥ 100 imágenes por ronda |
| Hardware | Windows 11, Intel i5-10400, NVIDIA RTX 3070 Ti (8 GB VRAM) |

## 3. Objetivos

| # | Objetivo | Métrica de éxito |
|---|---|---|
| O1 | Unificar las fotos dispersas en una biblioteca única con inventario | Todas las fotos en `C:\imagenes editadas`, con inventario y duplicados identificados |
| O2 | Quitar el fondo con bordes limpios, incluso en piezas finas | ≥ 90 % sin retoque manual en el set de referencia |
| O3 | Mejorar la calidad sin deformar el producto ni los textos impresos | Textos legibles; sin artefactos a 100 % de zoom |
| O4 | Una salida estándar que sirva para todo | PNG 1080×1080 transparente, producto centrado, mismo margen en todo el catálogo |
| O5 | Procesamiento masivo | 100 imágenes en ≤ 5 min, sin intervención |
| O6 | No repetir trabajo en variantes | Fotos idénticas o casi idénticas se procesan una sola vez |
| O7 | Robustez | Una imagen fallida no frena el lote y queda en el reporte |
| O8 | Costo cero por imagen | 100 % local, modelos con licencia apta para uso comercial |

### No-objetivos (fuera de alcance v1)
- Varias salidas por imagen (se pueden agregar después como perfiles en el preset; la arquitectura lo permite).
- Edición manual tipo Photoshop.
- Diagramación del catálogo o armado de publicidades.
- Detección automática del código de producto a partir del nombre de archivo.
- Conversión a CMYK.
- Multiusuario, nube.

## 4. Casos de uso

- **CU1 — Unificar biblioteca:** indico las carpetas donde hay fotos; la herramienta las copia a `C:\imagenes editadas\originales`, agrupa duplicados y genera un inventario. Los originales no se tocan.
- **CU2 — Procesar lote:** proceso todo lo pendiente (o una selección) y obtengo un PNG 1080×1080 transparente por foto.
- **CU3 — Revisión:** veo antes/después, marco las que salieron mal y las reproceso.
- **CU4 — Producto nuevo:** saco la foto con el celular siguiendo la guía (Anexo A), la dejo en una carpeta de entrada y la proceso.
- **CU5 — Completar códigos:** completo en el inventario el código interno de cada foto (a mano o importando una lista de productos) para que la salida quede nombrada por código.

## 5. Salida

| Atributo | Valor |
|---|---|
| Tamaño | 1080 × 1080 px |
| Formato | PNG con canal alfa |
| Fondo | Transparente |
| DPI (metadato) | 300 |
| Color | sRGB |
| Encuadre | Producto centrado; margen configurable (por defecto 4 % por lado) |

### 5.1 Por qué alcanza para impresión

El DPI es solo un metadato: no cambia los píxeles. Lo que importa es cuántos píxeles quedan sobre cada milímetro impreso. Al encajar el cuadrado de 1080 px en cada área de la card (se ajusta por el lado más corto):

| Área de imagen | Lado limitante | Resolución efectiva |
|---|---|---|
| 41 × 22 mm | 22 mm | ~1.250 DPI |
| 43 × 55 mm | 43 mm | ~640 DPI |
| 45 × 45 mm | 45 mm | ~610 DPI |
| 83 × 55 mm | 55 mm | ~500 DPI |

En todos los casos se supera con holgura el estándar de 300 DPI.

- **300 DPI en el metadato:** al insertarla en el software de diagramación, entra con un tamaño de ~91 mm (manejable). Con 72 DPI entraría a ~381 mm. Para web el valor es indiferente, así que 300 sirve para los dos usos.
- **Productos alargados** (resistencias, tiras de pines) en el cuadrado dejan espacio vacío arriba y abajo. Como el fondo es transparente, en la card se ve igual de bien. El costo es que el producto queda más chico en las áreas anchas (41×22, 83×55). El margen por defecto es bajo (4 %) para minimizar esto. Si en la práctica molesta, se puede agregar una salida con recorte ajustado sin rediseñar nada.

## 6. Biblioteca

### 6.1 Flujo

```
carpetas dispersas ──► escaneo ──► hash (exacto + perceptual) ──► agrupación de duplicados ──► copia a biblioteca ──► inventario.csv
```

1. **Escaneo** recursivo de las carpetas indicadas (JPG, JPEG, PNG, WEBP, HEIC, BMP, TIFF).
2. **Hash exacto** (SHA-256) → archivos idénticos.
   **Hash perceptual** (pHash) → misma foto con otra compresión o tamaño.
3. **Agrupación:**
   - Copias exactas (mismo SHA-256) → siempre se fusionan.
   - Casi idénticas (pHash ≤ umbral y misma proporción) → se fusionan **solo si el nombre es compatible**: mismo nombre normalizado (ignorando ` (2)` y ` - copia`) o alguno genérico. Si no (`3276-BL` / `3276-O`, `3202` / `3203`), quedan separadas y vinculadas en la columna `parecidas`. Motivo: el pHash trabaja en grises y no ve variantes de color; tampoco un filtro de color sirvió (en las fotos reales el producto ocupa poco del cuadro).
   - Dos fotos que ya están en la biblioteca nunca se fusionan, para no perder datos cargados a mano.
   - Representante: la de mayor resolución. Nombre: el más útil del grupo (no genérico, sin sufijo de copia).
   - Si en una corrida posterior aparece una versión de mayor resolución, reemplaza la copia en `originales/` y la foto vuelve a `pendiente`.
4. **Copia** de las representantes a `originales/` con nombre saneado. Los originales nunca se mueven ni se modifican. Nunca se pisa un archivo existente en `originales/`.
5. **Inventario** (`inventario.csv`, abrible en Excel) e índice interno `.indice.json` (hashes y grupos; caché por tamaño + fecha para no releer archivos sin cambios).

### 6.2 Nombres

No se intenta adivinar el código desde el nombre: los nombres reales son demasiado heterogéneos y un error silencioso sería peor que no tener código.

- Se conserva el nombre original, saneado: sin caracteres problemáticos, espacios múltiples colapsados, sufijos tipo ` (2)` normalizados a `_2`.
  - `SP-6305 _ SP-6306.jpg` → `SP-6305_SP-6306.png`
  - `SL-TF5050-1E-W (2).jpg` → `SL-TF5050-1E-W_2.png`
- Choques de nombre (mismo nombre en distintas carpetas, distinto contenido) → sufijo corto del hash: `conector_a3f9c1.png`.
- Nombres automáticos (`WhatsApp Image…`, `Captura de pantalla…`, `Sin título`, `Gemini_Generated_Image…`, cadenas aleatorias) se marcan en el inventario como `nombre_generico = sí`, para priorizar completarles el código.
- Columna **`codigo`** editable en el inventario: si tiene valor, la salida se nombra `<codigo>.png`; si no, con el nombre saneado. Admite varios códigos separados por `;` (una foto usada por varias variantes → una copia por código, opcional).

### 6.3 Inventario

| Columna | Descripción |
|---|---|
| `id` | Identificador interno estable: `i` + 11 caracteres del SHA-256 (la `i` evita que Excel lo tome como número) |
| `nombre` | Nombre saneado en la biblioteca |
| `codigo` | Código interno de producto (editable; vacío al inicio) |
| `descripcion` | Libre (editable) |
| `carpeta` | Subcarpeta de origen (en las fotos reales equivale a la categoría) |
| `ruta_original` | De dónde vino la representante |
| `ancho`, `alto` | Resolución original |
| `transparente` | sí/no: la foto ya tiene fondo transparente |
| `copias` | Cantidad de archivos fusionados en esta fila |
| `duplicados` | Otras rutas fusionadas (copias exactas y casi idénticas), separadas por ` \| ` |
| `parecidas` | Nombres de otras filas casi idénticas que no se fusionaron (variantes, misma foto para otro código) |
| `nombre_generico` | sí/no |
| `estado` | pendiente / ok / revisar / error |
| `modelo` | Editable. Vacío = el de `config.yaml`. Para una foto puntual: `birefnet`, `birefnet-dynamic`, `birefnet-dis` o `combinado`; al cambiarlo, la foto se reprocesa sola |
| `ajustes` | Editable. Correcciones por foto separadas por coma: `reflejo`, `sin-reflejo`, `relleno`, `sin-relleno` |
| `procesado_con` | Versión del preset usada (programa + hash de los ajustes de `proceso`; si cambian, la foto vuelve a procesarse) |
| `salida` | Archivos generados en `procesadas/` (uno por código). Si cambia el código, la salida anterior se borra |
| `advertencias` | Resultado del control de calidad |

### 6.4 Vinculación con productos (diferida)

El sistema de gestión puede exportar productos y nombres. La vinculación foto ↔ código se deja para cuando se desarrolle el **módulo de productos del CRM de Industrias Sur**; no forma parte de esta herramienta en v1.

Para no cerrarle la puerta, v1 deja preparado:
- un `id` estable por foto (derivado del hash), que el CRM puede usar como referencia;
- la columna `codigo` del inventario y el nombrado de salida por código;
- el inventario en CSV, fácil de importar desde el CRM.

Idea para entonces: cruzar la exportación de productos con los nombres de archivo para **sugerir** códigos (ej. `1N5221B` → código 3280), siempre con confirmación manual.

## 7. Requisitos funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RF1 | Escanear carpetas (recursivo) en los formatos de §6.1 | Alta |
| RF2 | Copiar a la biblioteca sin modificar originales | Alta |
| RF3 | Detectar duplicados exactos y casi idénticos; procesar uno por grupo | Alta |
| RF4 | Inventario CSV editable; respetar códigos cargados a mano al re-ejecutar | Alta |
| RF5 | Quitar fondo con modelo de segmentación seleccionable | Alta |
| RF6 | Conservar estructuras finas (patas, cables, terminales, resortes) | Alta |
| RF7 | Eliminar la sombra de contacto de la foto original | Alta |
| RF8 | Quedarse con el objeto principal y descartar manchas sueltas | Alta |
| RF9 | Refinar bordes y quitar halos blancos | Alta |
| RF10 | Restauración: artefactos JPEG, ruido, balance de blancos, exposición, nitidez | Alta |
| RF11 | Upscaling solo si el producto no llega al tamaño de salida; modo conservador para textos | Alta |
| RF12 | Salida PNG 1080×1080 transparente, 300 DPI, producto centrado con margen configurable | Alta |
| RF13 | Reporte por lote y estado en el inventario | Media |
| RF14 | Reanudación (saltear lo ya procesado con el mismo preset) | Media |
| RF15 | Control de calidad automático (§9) | Media |
| RF16 | Carpeta de entrada para fotos nuevas (`entrada/`) que se incorpora a la biblioteca al procesar | Media |
| RF17 | Interfaz web local para revisar antes/después y reprocesar | Media (fase 4) |
| RF18 | Sugerencia de códigos desde lista de productos | Diferido (CRM) |

## 8. Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF1 | 100 % local en Windows 11 con la RTX 3070 Ti; fallback a CPU |
| RNF2 | ≤ 3 s por imagen (100 imágenes ≤ 5 min) |
| RNF3 | VRAM ≤ 7 GB |
| RNF4 | Nunca se modifican, mueven ni sobrescriben los originales |
| RNF5 | Solo modelos con licencia apta para uso comercial |
| RNF6 | Instalación reproducible con un solo comando |
| RNF7 | Fidelidad: no cambiar formas, colores reales ni textos del producto |

## 9. Pipeline de procesamiento

```
Carga → Restauración → Upscale (si hace falta) → Segmentación → Refinado → Mejora → Encuadre 1080×1080 → PNG
```

1. **Carga y normalización** — orientación EXIF, sRGB, rechazo de archivos corruptos. Fotos grandes (celular) se reducen a tamaño de trabajo (~2048 px).
2. **Restauración** — artefactos JPEG y ruido. **Decisión (F3): sin modelo aparte.** Real-ESRGAN ya está entrenado con compresión y ruido y se aplica justo a las fotos chicas, que son las afectadas; las grandes se reducen a 1080 y los artefactos desaparecen al reducir. Un modelo extra sumaría tiempo sin mejora visible.
3. **Upscale (condicional)** — si el producto recortado no llega a ~1040 px de lado mayor (1080 menos el margen). Modo `conservative` por defecto. Implementado dentro del encuadre, solo sobre el recorte del producto y si el factor es ≥ 1,15: Real-ESRGAN x4plus por bloques de 512 px; `conservative` mezcla 50/50 con Lanczos; el alfa siempre con Lanczos. Comparado en fotos x3–x10: `conservative` da textos nítidos sin la textura "pintada" que `standard` agrega en JPEG muy comprimidos. Velocidad: x2plus si el factor ≤ 2 (lo más común) y x4plus si no, en fp16, y la entrada se reduce para que la salida del modelo tenga justo el tamaño final: de 2,4 a 1,0 s/foto sin diferencia visible.
4. **Segmentación** — máscara alfa. Se trabaja a mayor resolución que la salida para captar mejor las patas finas. Si la foto ya trae transparencia confiable (no es un rectángulo blanco con esquinas transparentes), se usa esa (`usar_transparencia_existente`).
   **4.1 Elección del modelo (2026-10-16).** Con 8 fotos reportadas (carcasas blancas, placas blancas con LEDs, reflejos, blísters) se compararon 4 variantes:

   | Variante | Resuelve | Falla |
   |---|---|---|
   | BiRefNet @1024 (F2) | — | las 8 |
   | BiRefNet_HR @2048 | textos, blíster | placas blancas; 713 ms, 5 GB VRAM |
   | BiRefNet_dynamic @1536 | carcasas blancas, reflejos, textos | placas blancas (solo ve los LEDs) |
   | BiRefNet-DIS5K @1024 | placas blancas, marcos | huecos en zonas con texto |

   La **unión** dynamic ∪ DIS5K corrigió 8/8 y en 32 fotos al azar empeoró 1 (sumó el reflejo del producto en la mesa, lo aporta dynamic). Limitar los agregados de DIS5K a la envolvente del producto se probó y se descartó: recorta el borde de las placas. Para los casos puntuales está la columna `modelo` del inventario. Costo: ~0,45 s de GPU por foto, ~3 GB VRAM.
   **4.2 Reflejos en la superficie de apoyo** (`quitar_reflejo`, **por foto** con `ajustes = reflejo`). Aplicado a todo el catálogo acertó 7 y cortó mal 11 (dos filas de productos, mangos de pinzas, lazos de cable, pilas de placas), así que queda desactivado por defecto. Casos reales: renders de IA de cajas de cable UTP "con reflejo en la base" y fotos sobre acrílico. Medido: el reflejo no es un espejo exacto (correlación baja), pero siempre está mucho más claro que el producto (+0,3 a +0,5). Se prueban dos líneas de apoyo por columna: el borde inferior del modelo general (que suele excluir el reflejo; solo si cubre ≥ 85 % del producto, así no se usa en placas con LEDs) y el punto medio de la máscara (si todos los modelos lo incluyen; exige "cintura" en V en esa línea). Se corta si lo de abajo está ≥ 0,15 más claro. Sin falsos positivos en productos simétricos (diodos, detector redondo, terminales).
5. **Refinado de máscara** — componente principal + piezas cercanas (patas separadas por reflejos); huecos con piezas adentro se rellenan (`rellenar_placas`: placa blanca con LEDs que el modelo ve como anillo + LEDs sueltos; un hueco real —ojo de terminal, rollo de cable, marco— no tiene nada adentro y se respeta); eliminación de sombra de contacto; matting de bordes y decontaminación de color (sin halo blanco).
6. **Mejora** — balance de blancos, exposición y nitidez suaves. El fondo blanco es la referencia: se neutraliza su tinte (máx. ±10 % por canal) y, si sale gris, se aclara hasta 1 + 0,5 × `contraste` (1,15 por defecto) con compresión de altas luces. No se toca nada si el fondo no es claro, parejo y casi neutro (fondo negro o de color, fotos con transparencia original). Enfoque final con máscara de enfoque ponderada por alfa (sin halo), a la mitad si hubo upscale con IA. Validado en las 963: 556 con referencia; tinte mediano 0, máximo 3 %; 16 fotos aclaradas.
7. **Encuadre** — recorte al producto, escalado para que el lado mayor ocupe el 92 % del lienzo, centrado en 1080×1080 transparente.
8. **Exportación** — PNG, 300 DPI, nombre según §6.2.
9. **Control de calidad** — marca para revisión:
   - máscara casi vacía o que ocupa casi toda la imagen;
   - producto tocando el borde de la foto original (posible recorte);
   - ~~discrepancia grande entre la máscara del modelo y una máscara simple por umbral de blanco~~ — **descartado como aviso (F3)**: se mide (`discrepancia` = 1 − IoU, columna del reporte) pero de las 13 fotos con valor más alto, 12 eran productos blancos bien recortados que el umbral no ve y solo 1 tenía un problema real. Queda como dato informativo;
   - upscale necesario > 4x (foto de origen muy pobre);
   - varias piezas grandes separadas (¿más de un producto?, ¿captura de pantalla con interfaz?).

## 10. Arquitectura

```
┌───────────────────────┐     ┌──────────────┐
│ CLI (Typer)           │     │ UI web local │  ← fase 4 (Gradio)
└──────────┬────────────┘     └──────┬───────┘
           └───────────┬─────────────┘
         ┌─────────────┴──────────────┐
         ▼                            ▼
┌─────────────────┐  inventario  ┌─────────────────┐
│   Biblioteca    │ ───────────► │  Batch runner   │  cola, reanudación, reporte
└─────────────────┘              └────────┬────────┘
                                          ▼
                                 ┌─────────────────┐     ┌─────────────────┐
                                 │    Pipeline     │ ◄── │ Model registry  │  carga una vez por lote
                                 └─────────────────┘     └─────────────────┘
```

Principios:
- **Núcleo independiente de la interfaz.**
- **Pasos intercambiables** con una interfaz común (`process(image, ctx) -> image`), para cambiar de modelo sin tocar el resto.
- **Biblioteca separada del procesamiento:** se puede unificar sin procesar y procesar cualquier subconjunto.

## 11. Stack tecnológico

| Componente | Elección | Motivo |
|---|---|---|
| Lenguaje | Python 3.12 (venv dedicado) | Mejor soporte de PyTorch/CUDA que la 3.14 instalada |
| Gestor de entorno | `uv` | Instalación rápida y reproducible |
| Segmentación (principal) | **BiRefNet** (MIT), modo `combinado`: unión de `BiRefNet_dynamic` @1536 y `BiRefNet-DIS5K` @1024 | Ver §9.4.1 |
| Segmentación (alternativa) | **rembg** (isnet-general-use) | Más rápida para productos simples |
| Restauración / upscale | **Real-ESRGAN** (BSD-3) + otros modelos vía **spandrel** (MIT) | Cambiar de modelo sin cambiar código; el definitivo se elige comparando en el set de referencia |
| Procesamiento clásico | OpenCV, Pillow, NumPy | Color, máscaras, composición |
| Deduplicación | `hashlib` + `imagehash` | SHA-256 + pHash |
| HEIC | `pillow-heif` | Fotos de celular |
| Inferencia | PyTorch + CUDA | GPU |
| CLI | Typer + Rich | Progreso legible |
| Configuración | YAML + Pydantic | Presets validados |
| UI (fase 4) | Gradio | Galería antes/después local |
| Tests | pytest | — |

> Se descarta BRIA RMBG-2.0 como default por licencia no comercial. Se verifica la licencia de cada modelo de upscaling antes de adoptarlo.

## 12. Configuración

```yaml
# config.yaml
biblioteca: "C:/imagenes editadas"
fuentes:                       # carpetas a unificar (se completan al usarla)
  - "C:/ruta/fotos 1"
  - "C:/ruta/fotos 2"
dedup:
  phash_umbral: 4

proceso:
  segmentacion:
    modelo: birefnet           # birefnet | rembg-isnet
    quitar_sombra: true
    refinar_bordes: true
  restauracion:
    artefactos_jpeg: true
    ruido: 0.3
  upscale:
    modo: conservative         # conservative | standard | off
  mejora:
    balance_blancos: true
    contraste: 0.3
    nitidez: 0.3
  salida:
    tamano: 1080
    margen: 0.04
    dpi: 300
```

## 13. Estructura

### Proyecto

```
editor de imagen/
├── docs/
│   ├── SDD.md
│   └── guia-captura.md
├── pyproject.toml
├── config.yaml
├── src/editor_imagen/
│   ├── cli.py
│   ├── config.py
│   ├── library/
│   │   ├── scan.py
│   │   ├── hashing.py
│   │   ├── naming.py
│   │   └── inventory.py
│   ├── batch.py
│   ├── pipeline.py
│   ├── models/registry.py
│   ├── steps/
│   │   ├── load.py
│   │   ├── restore.py
│   │   ├── upscale.py
│   │   ├── segment.py
│   │   ├── refine.py
│   │   ├── enhance.py
│   │   ├── frame.py
│   │   ├── export.py
│   │   └── qc.py
│   └── ui/app.py            # fase 4
├── tests/fixtures/
└── models/                  # pesos (fuera de git)
```

### Biblioteca (`C:\imagenes editadas`)

```
C:\imagenes editadas\
├── entrada\          fotos nuevas a incorporar
├── originales\       copias de las fotos fuente (una por grupo de duplicados)
├── procesadas\       PNG 1080×1080 transparentes
├── _revisar\         copias de las procesadas con advertencias
├── inventario.csv    separador ; y UTF-8 con BOM (Excel en español)
├── .indice.json      estado interno, no editar
└── reportes\
```

### Comandos

```
editor unificar                  # escanea fuentes + entrada, copia, actualiza inventario
editor estado                    # total, únicas, duplicados, pendientes, a revisar
editor procesar                  # procesa lo pendiente (saltea lo ya hecho con el mismo preset)
editor procesar --nombre conector --forzar
editor procesar --estado revisar --forzar
editor procesar --limite 40      # prueba rápida
editor check                     # GPU, modelos, configuración
```

## 14. Errores y reporte

- Cada imagen se procesa aislada; un fallo se registra y el lote sigue.
- Falta de memoria GPU → se libera caché y se reintenta una vez (F2); tiles más chicos y CPU quedan para F3 si hiciera falta.
- El inventario se guarda cada 20 imágenes: si el lote se corta, al relanzarlo sigue desde ahí.
- Reporte por lote en `reportes/`: `id, nombre, estado, tiempo_ms, resolucion_origen, upscale_factor, advertencias, error`.
- El estado de cada foto se guarda en el inventario (permite reanudar).

## 15. Calidad y pruebas

- **Set de referencia (40–50 fotos)** que cubra: componentes con patas finas (`1N5221B`), conectores metálicos con resorte (como el PLUG 3,5 mm de la card de ejemplo), productos con texto/serigrafía (fotocontroles, capacitores), paneles LED blancos, tiras de pines, capturas de pantalla, imágenes de WhatsApp y fotos nuevas del celular.
- **Hoja de contacto** antes/después para comparar modelos y ajustes.
- **Prueba de impresión** de 5–10 productos difíciles en las 4 medidas de card.
- **Benchmark** de tiempo por imagen y VRAM.
- **Tests unitarios:** saneado de nombres, choques, dedup, encuadre, exportación (tamaño, alfa, DPI), respeto de códigos editados en el inventario.

## 16. Roadmap

| Fase | Entregable | Criterio de cierre |
|---|---|---|
| **F0 — Setup** | Python 3.12 + CUDA, modelos, `editor check` | GPU y modelos OK |
| **F1 — Biblioteca** | Escaneo, dedup, nombres, copia, inventario, `editor estado` | Todas las carpetas unificadas; número real de fotos únicas conocido |
| **F2 — MVP proceso** | Segmentación + refinado básico + encuadre + exportación | 100 fotos procesadas de punta a punta |
| **F3 — Calidad** | Restauración, upscale (comparativa), refinado avanzado, QC | ≥ 90 % de aceptación en el set de referencia + prueba de impresión OK |
| **F4 — Revisión** | UI Gradio de revisión y reproceso | Revisión y reproceso desde el navegador |
| **Futuro** | Integración con el módulo de productos del CRM de Industrias Sur | Se define en ese proyecto |

## 17. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Patas finas o resortes recortados | Alto | BiRefNet a alta resolución, conservar componentes cercanos al principal |
| Productos blancos o metálicos claros confundidos con el fondo blanco | Alto | Comparar modelos; QC por discrepancia con umbral; reproceso en la UI |
| Upscaler deforma textos | Bajo | Se necesita poco upscale (salida 1080); modo conservador |
| Capturas de pantalla o imágenes de WhatsApp con elementos extra | Medio | QC detecta varias piezas grandes; quedan para revisión |
| Dedup agrupa productos que se ven casi iguales (misma carcasa, distinta serigrafía) | Medio | Umbral conservador; grupos listados en el inventario para revisar |
| Productos alargados quedan chicos en áreas anchas de la card | Bajo | Margen bajo (4 %); salida con recorte ajustado como extensión futura |
| Mejora cambia colores reales | Medio | Intensidades bajas; balance de blancos desactivable |

## 18. Preguntas abiertas

Ninguna bloqueante.

### Resultado F1 (2026-10-16)
Fuente: `C:\Users\Usuario Ventas\Desktop\FOTOS PRODCUTOS` — 999 imágenes → **963 únicas** (8 copias exactas, 28 casi idénticas fusionadas), 88 con parecidas, 24 nombres genéricos, 315 ya transparentes, 0 errores. Unificar tarda ~75 s la primera vez.

### Resultado F3 (2026-10-16)
Segmentación combinada (dynamic ∪ DIS5K), relleno de placas, reflejos por foto, upscale conservative (x2/x4, fp16), mejora de color con el fondo como referencia y enfoque. Catálogo completo: **899 ok, 64 a revisar, 0 errores, 1,1 s/foto** (objetivo ≤ 3 s). Restauración sin modelo aparte y QC por umbral solo informativo (ver §9). **Prueba de impresión OK** (2026-10-16): 12 casos difíciles en las 4 medidas de card (`scripts/prueba_impresion.py`). F3 cerrada.

### Resultado F2 (2026-10-16)
963 fotos procesadas en ~7,5 min (0,47 s/foto, RTX 3070 Ti): **898 ok, 64 a revisar, 1 error** (`Obsidian-background1`, un fondo sin producto). 308 usaron su transparencia original, 614 BiRefNet. En muestras al azar las patas finas, cables y fondos negros/grises salen bien y sin halo.
- "Varias piezas grandes" quedó como advertencia **informativa** (no manda a revisar): en el catálogo muchas fotos muestran varios productos a propósito (112 casos, todos bien recortados).
- Mandan a revisar: producto que toca el borde de la foto (cables y patas cortados en el original), máscara vacía/llena, upscale > 4x.

### Decisiones cerradas
| Tema | Decisión |
|---|---|
| Vinculación con códigos de producto | Se difiere al módulo de productos del CRM de Industrias Sur (§6.4) |

---

## Anexo A — Guía de captura con el Redmi Note 13 Pro+ 5G

1. **Fondo:** cartulina blanca mate en curva (sin pliegue entre base y fondo).
2. **Luz:** luz natural indirecta o dos lámparas difusas a los costados. Sin flash.
3. **Modo:** cámara principal, **sin** modo 200 MP, sin filtros ni "belleza", HDR automático.
4. **Distancia:** para piezas chicas, alejarse ~25–30 cm y usar zoom 2x (evita distorsión).
5. **Enfoque:** tocar el producto para enfocar; bajar un poco la exposición si el blanco se quema.
6. **Encuadre:** producto centrado, completo, con aire alrededor; un producto por foto.
7. **Estabilidad:** apoyar el celular o usar trípode.
8. **Nombre:** renombrar la foto con el código interno y dejarla en `C:\imagenes editadas\entrada`.
