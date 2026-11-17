# Procesamiento distribuido (simulado) de ventas

Proyecto de procesamiento distribuido de ventas en Python. **No hay clúster real:**
los nodos se simulan con procesos independientes del sistema operativo
(`multiprocessing`), todos en una sola máquina y sin red.

## Archivos

| Archivo | Descripción |
| --- | --- |
| `generar_datos.py` | Fase 1. Genera `ventas_N.csv` (1.000, 10.000, 100.000 y 500.000 registros) |
| `procesamiento.py` | Fase 3. Secuencial, paralelo v1, paralelo v2 (por bloques), consolidación y reportes |
| `benchmark.py` | Fase 4. Tiempos, aceleración Ts / Tp y prueba de fallo de un nodo |
| `generar_panel.py` | Panel. Lee los JSON de `benchmark.py` y `procesamiento.py` y genera `panel_ventas.html` |
| `servidor_panel.py` | Servidor local que sirve el panel y permite ejecutar las pruebas desde la página |
| `panel_plantilla.html` | Plantilla del panel (sin datos). No se abre directamente: la usa `generar_panel.py` |
| `panel_ventas.html` | Panel interactivo ya generado con los resultados incluidos (abrir en el navegador) |
| `diagrama_arquitectura.svg` / `.png` | Fase 2. Diagrama de arquitectura |
| `resultados_benchmark.csv` / `.txt` / `.json` | Salida de `benchmark.py` (equipo donde se ejecutó incluido) |
| `evidencia_ejecucion_500000.txt` / `.json` | Parciales por nodo vs consolidado y los tres reportes |
| `ventas_*.csv` | Datasets sintéticos, sin datos personales |

## Cómo ejecutar

Requiere Python 3.8 o superior. No usa bibliotecas externas.

```bash
python generar_datos.py                          # crea los 4 datasets
python procesamiento.py ventas_500000.csv 4      # archivo y número de nodos
python benchmark.py                              # pruebas de rendimiento
python generar_panel.py                          # panel_ventas.html con los resultados
python servidor_panel.py                         # panel en http://127.0.0.1:8000 con botones para ejecutar
```

`servidor_panel.py` abre el panel en el navegador y añade la sección «Ejecutar las pruebas»:
elige un archivo y un número de nodos, o lanza el benchmark completo, y al terminar la página
se recarga con los resultados nuevos. Solo escucha en tu equipo (127.0.0.1) y solo ejecuta
`procesamiento.py` y `benchmark.py`. Si abres `panel_ventas.html` con doble clic, esa sección
no aparece (un archivo local no puede ejecutar Python).

El panel no tiene números escritos a mano: se arma con `resultados_benchmark.json` y
`evidencia_ejecucion_N.json` (se usa el más reciente). Para actualizarlo con tus propias pruebas,
ejecuta en orden `procesamiento.py`, `benchmark.py` y `generar_panel.py`.

## Importante antes de entregar

Los resultados incluidos se obtuvieron en una máquina virtual de 2 núcleos, no en el
equipo del grupo. Ejecute `python benchmark.py` en su propio computador y reemplace en
el documento la tabla de características del equipo y la tabla de tiempos. Luego vuelve a
ejecutar `python generar_panel.py` para que el panel muestre tus resultados.

## Publicar el panel en Netlify

`generar_panel.py` también escribe `public/index.html`, que es lo que publica Netlify
(`netlify.toml` ya apunta a esa carpeta y no necesita comando de build). En la versión
publicada el panel es de solo lectura: los botones para ejecutar pruebas solo aparecen con
`python servidor_panel.py`, porque Netlify no ejecuta Python.

Para actualizar el sitio con nuevos resultados: ejecuta las pruebas, luego
`python generar_panel.py`, y haz `git add public && git commit && git push`.
