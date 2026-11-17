"""
Panel interactivo: sirve el panel en http://127.0.0.1:8000 y permite EJECUTAR las
pruebas (procesamiento.py y benchmark.py) desde la propia pagina.

Un HTML abierto con doble clic no puede lanzar Python; por eso este servidor local.
Solo escucha en 127.0.0.1 (tu equipo) y solo ejecuta los dos scripts del proyecto,
con argumentos validados. Usa unicamente la biblioteca estandar.

Uso (desde la carpeta del proyecto):
    python servidor_panel.py            # puerto 8000
    python servidor_panel.py 8123       # otro puerto
Detener: Ctrl+C
"""
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from generar_panel import construir_html

ESTADO = {"corriendo": False, "tarea": None, "inicio": 0.0, "log": [], "codigo": None}
CANDADO = threading.Lock()


def archivos_disponibles():
    return sorted(glob.glob("ventas_*.csv"), key=lambda r: int(re.findall(r"\d+", r)[0]))


def lanzar(tarea, archivo=None, nodos=None):
    """Valida los argumentos y ejecuta el script en un hilo. Devuelve (ok, mensaje)."""
    if tarea == "benchmark":
        cmd = [sys.executable, "-u", "benchmark.py"]
    elif tarea == "procesamiento":
        if archivo not in archivos_disponibles():
            return False, "Archivo no valido"
        if not isinstance(nodos, int) or not 1 <= nodos <= 16:
            return False, "Nodos debe estar entre 1 y 16"
        cmd = [sys.executable, "-u", "procesamiento.py", archivo, str(nodos)]
    else:
        return False, "Tarea desconocida"
    with CANDADO:
        if ESTADO["corriendo"]:
            return False, "Ya hay una prueba en ejecucion"
        ESTADO.update(corriendo=True, tarea=" ".join(cmd[2:]), inicio=time.time(), log=[], codigo=None)
    threading.Thread(target=correr, args=(cmd,), daemon=True).start()
    return True, "Iniciada"


def correr(cmd):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        for linea in p.stdout:
            ESTADO["log"].append(linea.rstrip())
        ESTADO["codigo"] = p.wait()
    except Exception as e:  # noqa: BLE001
        ESTADO["log"].append(f"Error: {e}")
        ESTADO["codigo"] = -1
    finally:
        ESTADO["corriendo"] = False


class Manejador(BaseHTTPRequestHandler):
    def responder(self, codigo, cuerpo, tipo):
        datos = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def json(self, obj, codigo=200):
        self.responder(codigo, json.dumps(obj, ensure_ascii=False), "application/json")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                self.responder(200, construir_html(), "text/html")
            except SystemExit as e:  # faltan los JSON de resultados
                self.responder(500, f"<p>{e}</p>", "text/html")
        elif self.path == "/api/estado":
            self.json({**ESTADO, "log": ESTADO["log"][-200:], "archivos": archivos_disponibles(),
                       "transcurrido": round(time.time() - ESTADO["inicio"], 1) if ESTADO["corriendo"] else 0})
        else:
            self.responder(404, "No encontrado", "text/plain")

    def do_POST(self):
        if self.path != "/api/ejecutar":
            return self.responder(404, "No encontrado", "text/plain")
        # Solo se acepta desde esta misma pagina (evita que otro sitio dispare pruebas).
        if self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
            return self.json({"ok": False, "mensaje": "Host no permitido"}, 403)
        try:
            n = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.json({"ok": False, "mensaje": "JSON invalido"}, 400)
        ok, msg = lanzar(cuerpo.get("tarea"), cuerpo.get("archivo"), cuerpo.get("nodos"))
        self.json({"ok": ok, "mensaje": msg}, 200 if ok else 409)

    def log_message(self, *a):  # silencio en consola
        pass


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    url = f"http://127.0.0.1:{puerto}"
    print(f"Panel en {url}  (Ctrl+C para detener)")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")


if __name__ == "__main__":
    main()
