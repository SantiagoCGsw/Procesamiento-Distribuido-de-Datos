"""
Fase 4. Pruebas de rendimiento: secuencial vs paralelo (simulado).

Para cada tamano de datos y cada cantidad de nodos se mide el tiempo
secuencial (Ts) y el paralelo (Tp) tomando la MEDIANA de varias repeticiones,
y se calcula la aceleracion = Ts / Tp. Tambien verifica que el resultado
paralelo sea identico al secuencial y ejecuta una prueba de tolerancia a fallos.

Uso: python benchmark.py
Salida: resultados_benchmark.csv y resultados_benchmark.txt
"""
import csv
import json
import os
import platform
import statistics
import time

from procesamiento import comparar, paralelo, paralelo_bloques, secuencial

TAMANOS = [1000, 10000, 100000, 500000]
NODOS = [2, 4]
REPETICIONES = 5


def info_equipo():
    modelo = "desconocido"
    try:
        with open("/proc/cpuinfo") as f:
            for linea in f:
                if linea.startswith("model name"):
                    modelo = linea.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    mem = "desconocida"
    try:
        with open("/proc/meminfo") as f:
            kb = int(f.readline().split()[1])
            mem = f"{kb / 1024 / 1024:.1f} GB"
    except (OSError, ValueError):
        pass
    return {"SO": platform.platform(), "Procesador": modelo,
            "Nucleos logicos": os.cpu_count(), "RAM": mem,
            "Python": platform.python_version()}


def mediana(f, reps):
    tiempos, ultimo = [], None
    for _ in range(reps):
        ultimo = f()
        tiempos.append(ultimo[1])
    return statistics.median(tiempos), ultimo


def main():
    equipo = info_equipo()
    filas, lineas, filas_json = [], [], []
    lineas.append("CARACTERISTICAS DEL EQUIPO")
    for k, v in equipo.items():
        lineas.append(f"  {k}: {v}")
    lineas.append(f"\nRepeticiones por medicion: {REPETICIONES} (se reporta la mediana)")
    lineas.append("Paralelismo SIMULADO con procesos del SO (multiprocessing), sin cluster real.\n")
    lineas.append("Variante v1: el coordinador lee y envia las filas a los nodos.")
    lineas.append("Variante v2: cada nodo lee su propio bloque (byte range) del archivo.\n")
    lineas.append(f"{'Registros':>10} {'Nodos':>6} {'Ts (s)':>9} {'Tp v1 (s)':>10} {'Acel v1':>8} "
                  f"{'Tp v2 (s)':>10} {'Acel v2':>8} {'Iguales':>8}")
    for n in TAMANOS:
        ruta = f"ventas_{n}.csv"
        ts, (rs, _) = mediana(lambda: secuencial(ruta), REPETICIONES)
        for k in NODOS:
            tp1, (r1, _, _, _) = mediana(lambda: paralelo(ruta, k), REPETICIONES)
            tp2, (r2, _, _, _) = mediana(lambda: paralelo_bloques(ruta, k), REPETICIONES)
            igual = comparar(rs, r1) and comparar(rs, r2)
            filas_json.append({"registros": n, "nodos": k, "ts": round(ts, 4),
                               "tp_v1": round(tp1, 4), "acel_v1": round(ts / tp1, 4),
                               "tp_v2": round(tp2, 4), "acel_v2": round(ts / tp2, 4),
                               "iguales": bool(igual)})
            filas.append([n, k, round(ts, 4), round(tp1, 4), round(ts / tp1, 3),
                          round(tp2, 4), round(ts / tp2, 3), igual])
            lineas.append(f"{n:>10,} {k:>6} {ts:>9.4f} {tp1:>10.4f} {ts/tp1:>7.2f}x "
                          f"{tp2:>10.4f} {ts/tp2:>7.2f}x {str(igual):>8}")

    # ---- tolerancia a fallos: el nodo 1 falla antes de entregar ----
    ruta, k = "ventas_100000.csv", 4
    rs, _ = secuencial(ruta)
    lineas.append("\nPRUEBA DE TOLERANCIA A FALLOS (variante v2, 100.000 registros, 4 nodos, falla el nodo 1)")
    aborta = False
    try:
        paralelo_bloques(ruta, k, nodo_fallido=1, reintentar=False)
        lineas.append("  Sin reintento: no fallo (inesperado)")
    except RuntimeError as e:
        aborta = True
        lineas.append(f"  Sin reintento: el trabajo completo se aborta -> {e}")
    t0 = time.perf_counter()
    rp, tp, _, info = paralelo_bloques(ruta, k, nodo_fallido=1, reintentar=True)
    lineas.append(f"  Con reintento: fallos={info['fallos']}, reintentos={info['reintentos']}, "
                  f"tiempo={tp:.4f} s, resultado correcto={comparar(rs, rp)}")
    tp_ok, _ = mediana(lambda: paralelo_bloques(ruta, k)[:2], 3)
    lineas.append(f"  Tiempo sin fallo (mediana de 3): {tp_ok:.4f} s")

    equipo_json = {"so": equipo["SO"], "procesador": equipo["Procesador"],
                   "nucleos": equipo["Nucleos logicos"], "ram": equipo["RAM"],
                   "python": equipo["Python"]}
    with open("resultados_benchmark.json", "w", encoding="utf-8") as f:
        json.dump({"equipo": equipo_json, "repeticiones": REPETICIONES, "filas": filas_json,
                   "fallo": {"registros": 100000, "nodos": k, "nodo_fallido": 1,
                             "aborta_sin_reintento": aborta, "fallos": info["fallos"],
                             "reintentos": info["reintentos"], "tp_con_reintento": round(tp, 4),
                             "tp_sin_fallo": round(tp_ok, 4), "correcto": bool(comparar(rs, rp))}},
                  f, ensure_ascii=False, indent=2)
    with open("resultados_benchmark.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["registros", "nodos", "Ts_s", "Tp_v1_s", "aceleracion_v1", "Tp_v2_s", "aceleracion_v2", "resultados_iguales"])
        w.writerows(filas)
    texto = "\n".join(lineas)
    with open("resultados_benchmark.txt", "w") as f:
        f.write(texto + "\n")
    print(texto)


if __name__ == "__main__":
    main()
