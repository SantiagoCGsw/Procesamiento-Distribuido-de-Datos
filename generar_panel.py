"""
Panel de ventas distribuidas: genera panel_ventas.html con los resultados reales.

Lee lo que producen los otros scripts del proyecto:
  - resultados_benchmark.json        (benchmark.py)
  - evidencia_ejecucion_N.json       (procesamiento.py; se usa el mas reciente)
y los inyecta en panel_plantilla.html. El panel no tiene numeros escritos a mano:
si se repiten las pruebas en otro equipo, basta volver a ejecutar este script.

Uso (desde la carpeta del proyecto):
    python generar_panel.py
Salida: panel_ventas.html (doble clic) y public/index.html (para publicar en Netlify)
"""
import glob
import json
import os
import sys

PLANTILLA = "panel_plantilla.html"
SALIDA = "panel_ventas.html"
SALIDA_WEB = os.path.join("public", "index.html")  # carpeta que publica Netlify
MARCA = "/*__DATOS__*/null"


def cargar(ruta, quien):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"Falta {ruta}. Ejecuta primero: {quien}")


def evidencia_reciente():
    """Devuelve la ruta del evidencia_ejecucion_N.json modificado mas recientemente."""
    rutas = glob.glob("evidencia_ejecucion_*.json")
    if not rutas:
        sys.exit("Falta evidencia_ejecucion_N.json. Ejecuta primero: "
                 "python procesamiento.py ventas_500000.csv 4")
    return max(rutas, key=os.path.getmtime)


def construir_html():
    """Devuelve el HTML del panel con los datos actuales (lo usa tambien servidor_panel.py)."""
    benchmark = cargar("resultados_benchmark.json", "python benchmark.py")
    evidencia = cargar(evidencia_reciente(), "python procesamiento.py ventas_500000.csv 4")
    with open(PLANTILLA, encoding="utf-8") as f:
        html = f.read()
    if MARCA not in html:
        sys.exit(f"{PLANTILLA} no contiene la marca {MARCA}")
    datos = json.dumps({"benchmark": benchmark, "evidencia": evidencia}, ensure_ascii=False)
    datos = datos.replace("</", "<\\/")  # evita cerrar el <script> por accidente
    return html.replace(MARCA, datos)


def main():
    html = construir_html()
    os.makedirs("public", exist_ok=True)
    for ruta in (SALIDA, SALIDA_WEB):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Panel generado: {SALIDA} y {SALIDA_WEB}")


if __name__ == "__main__":
    main()
