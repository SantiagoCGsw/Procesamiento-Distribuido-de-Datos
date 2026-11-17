"""
Fase 1. Generador de datos sinteticos de ventas.

Columnas: id_venta, fecha, ciudad, producto, cantidad, precio_unitario
No contiene datos personales (ni clientes, ni documentos, ni contactos).

Uso:
    python generar_datos.py            # genera 1.000, 10.000, 100.000 y 500.000
    python generar_datos.py 250000     # genera un tamano personalizado
"""
import csv
import random
import sys
from datetime import date, timedelta

SEMILLA = 42  # semilla fija para que el dataset sea reproducible

CIUDADES = ["Bogota", "Medellin", "Cali", "Barranquilla", "Cartagena",
            "Bucaramanga", "Pereira", "Manizales", "Cucuta", "Santa Marta"]

# producto -> precio base unitario (COP)
PRODUCTOS = {
    "Laptop": 2500000, "Celular": 1800000, "Tablet": 1200000,
    "Audifonos": 150000, "Teclado": 120000, "Mouse": 60000,
    "Monitor": 900000, "Impresora": 700000, "Camara": 1100000,
    "Cargador": 50000, "Parlante": 250000, "Disco Duro": 320000,
}

FECHA_INICIO = date(2025, 1, 1)
DIAS = 365  # un anio completo para poder agrupar por mes


def generar(n, ruta):
    rnd = random.Random(SEMILLA)
    nombres = list(PRODUCTOS)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id_venta", "fecha", "ciudad", "producto",
                    "cantidad", "precio_unitario"])
        for i in range(1, n + 1):
            producto = rnd.choice(nombres)
            # el precio varia +-10% alrededor del precio base
            precio = round(PRODUCTOS[producto] * rnd.uniform(0.9, 1.1))
            fecha = FECHA_INICIO + timedelta(days=rnd.randrange(DIAS))
            w.writerow([i, fecha.isoformat(), rnd.choice(CIUDADES),
                        producto, rnd.randint(1, 10), precio])
    print(f"Generado {ruta} con {n:,} registros")


if __name__ == "__main__":
    tamanos = [int(a) for a in sys.argv[1:]] or [1000, 10000, 100000, 500000]
    for n in tamanos:
        generar(n, f"ventas_{n}.csv")
