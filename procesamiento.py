"""
Fase 3. Procesamiento secuencial y distribuido (SIMULADO) de ventas.

IMPORTANTE: no hay un cluster real. El procesamiento "distribuido" se SIMULA
con procesos independientes del sistema operativo (multiprocessing). Cada
proceso trabaja sobre su propia particion y no comparte memoria con los demas;
solo devuelve un resultado parcial al proceso coordinador, tal como lo haria un
nodo worker en un cluster. La comunicacion es por IPC local, no por red.

Calcula:
  1. Ingresos totales por ciudad
  2. Top 5 productos por cantidad vendida
  3. Ingresos por mes
"""
import csv
import json
import os
import time
from collections import Counter, defaultdict
from multiprocessing import Pool


# ---------------------------------------------------------------- lectura
def leer_filas(ruta):
    """Lee el CSV completo como lista de tuplas (fecha, ciudad, producto, cant, precio)."""
    # Se usa csv.reader (igual que los nodos de la v2) para que secuencial y
    # paralelo midan exactamente el mismo trabajo de parseo.
    with open(ruta, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)  # encabezado
        return [(x[1], x[2], x[3], int(x[4]), int(x[5])) for x in r]


def particionar(filas, k):
    """Reparte las filas en k particiones de tamano casi igual (por rangos)."""
    n = len(filas)
    base, resto = divmod(n, k)
    partes, inicio = [], 0
    for i in range(k):
        fin = inicio + base + (1 if i < resto else 0)
        partes.append(filas[inicio:fin])
        inicio = fin
    return partes


# ---------------------------------------------------- tarea de cada nodo
def procesar_particion(args):
    """
    Tarea 'map' que ejecuta un nodo sobre su particion.
    Devuelve agregados parciales (no las filas), lo que reduce la
    cantidad de datos que hay que mover hacia el coordinador.
    """
    id_nodo, filas, falla = args
    if falla:  # simulacion de fallo de nodo (ver pruebas de tolerancia)
        raise RuntimeError(f"Nodo {id_nodo} fallo antes de entregar su resultado")
    t0 = time.perf_counter()
    ciudad = defaultdict(int)
    producto = defaultdict(int)
    mes = defaultdict(int)
    for fecha, c, p, cant, precio in filas:
        ciudad[c] += cant * precio
        producto[p] += cant
        mes[fecha[:7]] += cant * precio  # AAAA-MM
    return {"nodo": id_nodo, "registros": len(filas),
            "pid": os.getpid(), "t": time.perf_counter() - t0,
            "ciudad": dict(ciudad), "producto": dict(producto),
            "mes": dict(mes)}


# ------------------------------------------------------- consolidacion
def consolidar(parciales):
    """Fase 'reduce': suma los resultados parciales de todos los nodos."""
    ciudad, producto, mes = Counter(), Counter(), Counter()
    for p in parciales:
        ciudad.update(p["ciudad"])
        producto.update(p["producto"])
        mes.update(p["mes"])
    return {"ciudad": dict(ciudad),
            "top5": producto.most_common(5),
            "mes": dict(sorted(mes.items()))}


# ----------------------------------------------------------- secuencial
def secuencial(ruta):
    """Linea base: un solo proceso lee y procesa todo. Devuelve (resultado, tiempo)."""
    t0 = time.perf_counter()
    filas = leer_filas(ruta)
    parcial = procesar_particion((0, filas, False))
    res = consolidar([parcial])
    return res, time.perf_counter() - t0


# ------------------------------------------------------------- paralelo
def paralelo(ruta, nodos, nodo_fallido=None, reintentar=True):
    """
    Version distribuida simulada.
    Tiempo total = lectura + particionado + trabajo en nodos + consolidacion.
    Si nodo_fallido no es None, ese nodo falla en su primer intento; con
    reintentar=True el coordinador reasigna solo esa particion.
    Devuelve (resultado, tiempo, parciales, info).
    """
    t0 = time.perf_counter()
    filas = leer_filas(ruta)
    partes = particionar(filas, nodos)
    tareas = [(i, partes[i], i == nodo_fallido) for i in range(nodos)]
    info = {"fallos": 0, "reintentos": 0}
    parciales = []
    with Pool(processes=nodos) as pool:
        asincronos = [pool.apply_async(procesar_particion, (t,)) for t in tareas]
        for i, a in enumerate(asincronos):
            try:
                parciales.append(a.get())
            except RuntimeError:
                info["fallos"] += 1
                if not reintentar:
                    raise
                # el coordinador reasigna la particion perdida (sin falla)
                info["reintentos"] += 1
                parciales.append(
                    pool.apply((procesar_particion), ((i, partes[i], False),)))
    res = consolidar(parciales)
    return res, time.perf_counter() - t0, parciales, info


# ------------------------------------------- paralelo por bloques (v2)
def particionar_bytes(ruta, k):
    """
    Divide el ARCHIVO en k rangos de bytes alineados a fin de linea, como lo
    haria HDFS con sus bloques. El coordinador solo calcula offsets (barato);
    no lee ni parsea datos.
    Devuelve [(inicio, fin), ...] sin incluir la linea de encabezado.
    """
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as f:
        f.readline()  # saltar encabezado
        inicio_datos = f.tell()
        cortes = [inicio_datos]
        for i in range(1, k):
            f.seek(inicio_datos + (tam - inicio_datos) * i // k)
            f.readline()  # avanzar hasta el siguiente salto de linea
            cortes.append(f.tell())
    cortes.append(tam)
    return list(zip(cortes[:-1], cortes[1:]))


def procesar_bloque(args):
    """Tarea del nodo: lee SU rango de bytes del CSV, lo parsea y agrega."""
    id_nodo, ruta, inicio, fin, falla = args
    if falla:
        raise RuntimeError(f"Nodo {id_nodo} fallo antes de entregar su resultado")
    with open(ruta, "rb") as f:
        f.seek(inicio)
        texto = f.read(fin - inicio).decode("utf-8")
    filas = [(r[1], r[2], r[3], int(r[4]), int(r[5]))
             for r in csv.reader(texto.splitlines())]
    return procesar_particion((id_nodo, filas, False))


def paralelo_bloques(ruta, nodos, nodo_fallido=None, reintentar=True):
    """
    Version distribuida simulada v2: cada proceso lee su propio bloque del
    archivo, de modo que la lectura y el parseo tambien se reparten.
    Misma firma de retorno que paralelo().
    """
    t0 = time.perf_counter()
    rangos = particionar_bytes(ruta, nodos)
    tareas = [(i, ruta, a, b, i == nodo_fallido) for i, (a, b) in enumerate(rangos)]
    info = {"fallos": 0, "reintentos": 0}
    parciales = []
    with Pool(processes=nodos) as pool:
        asincronos = [pool.apply_async(procesar_bloque, (t,)) for t in tareas]
        for i, a in enumerate(asincronos):
            try:
                parciales.append(a.get())
            except RuntimeError:
                info["fallos"] += 1
                if not reintentar:
                    raise
                info["reintentos"] += 1
                t = tareas[i][:-1] + (False,)
                parciales.append(pool.apply(procesar_bloque, (t,)))
    res = consolidar(parciales)
    return res, time.perf_counter() - t0, parciales, info


# ------------------------------------------------------------ utilidades
def comparar(res_a, res_b, tol=1e-9):
    """True si dos resultados consolidados son identicos."""
    return (res_a["ciudad"] == res_b["ciudad"]
            and res_a["top5"] == res_b["top5"]
            and res_a["mes"] == res_b["mes"])


def imprimir_reporte(res):
    print("\nIngresos totales por ciudad (COP):")
    for c, v in sorted(res["ciudad"].items(), key=lambda x: -x[1]):
        print(f"  {c:<14}{v:>20,}")
    print("\nTop 5 productos por cantidad vendida:")
    for p, q in res["top5"]:
        print(f"  {p:<14}{q:>10,}")
    print("\nIngresos por mes (COP):")
    for m, v in res["mes"].items():
        print(f"  {m}{v:>22,}")


if __name__ == "__main__":
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else "ventas_10000.csv"
    nodos = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rs, ts = secuencial(ruta)
    rp, tp, parciales, _ = paralelo_bloques(ruta, nodos)
    print(f"Archivo: {ruta} | nodos (procesos simulados): {nodos}")
    print("Parciales por nodo (antes de consolidar):")
    for p in parciales:
        print(f"  nodo {p['nodo']}: {p['registros']:,} registros, "
              f"pid {p['pid']}, {p['t']*1000:.1f} ms, "
              f"ingresos parciales = {sum(p['ciudad'].values()):,}")
    total_parciales = sum(sum(p['ciudad'].values()) for p in parciales)
    total_final = sum(rp['ciudad'].values())
    print(f"Suma de parciales = {total_parciales:,} | consolidado = {total_final:,} "
          f"| coinciden: {total_parciales == total_final}")
    print(f"Resultado paralelo == secuencial: {comparar(rs, rp)}")
    print(f"Ts={ts:.3f}s  Tp={tp:.3f}s  aceleracion={ts/tp:.2f}x")
    imprimir_reporte(rp)
    # Evidencia en JSON: la lee generar_panel.py para construir el panel.
    n = os.path.basename(ruta).replace("ventas_", "").replace(".csv", "")
    salida = f"evidencia_ejecucion_{n}.json"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({
            "archivo": os.path.basename(ruta), "n_nodos": nodos,
            "parciales": [{"nodo": p["nodo"], "registros": p["registros"], "pid": p["pid"],
                           "ms": round(p["t"] * 1000, 1), "ingresos": sum(p["ciudad"].values())}
                          for p in parciales],
            "total": total_final,
            "coinciden": total_parciales == total_final,
            "igual_secuencial": comparar(rs, rp),
            "ts": round(ts, 4), "tp": round(tp, 4),
            "consolidado": {"ciudad": rp["ciudad"], "top5": rp["top5"], "mes": rp["mes"]},
        }, f, ensure_ascii=False, indent=2)
    print(f"\nEvidencia guardada en {salida}")
