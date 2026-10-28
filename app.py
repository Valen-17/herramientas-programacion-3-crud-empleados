# Autora: Valentina Alejandra Pérez Cardona
"""Servidor web del CRUD de empleados.

Sirve la interfaz (templates/ y static/) y una API REST sencilla que persiste
en empleados.xml o empleados.json usando la capa de datos (datos.py).
Solo usa la biblioteca estándar de Python: no requiere instalar nada.
"""
import csv
import datetime
import io
import json
import mimetypes
import os
import re
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import datos
from modelo import Empleado

# En local escucha solo en este equipo (puerto 5000). En un hosting como Render
# la variable PORT indica el puerto y hay que escuchar en todas las interfaces.
EN_HOSTING = "PORT" in os.environ
HOST = "0.0.0.0" if EN_HOSTING else "127.0.0.1"
PUERTO = int(os.environ.get("PORT", 5000))
CARPETA = datos.CARPETA
RAIZ_STATIC = os.path.join(CARPETA, "static")
PLANTILLA = os.path.join(CARPETA, "templates", "index.html")

# formato -> (ruta, cargar, guardar)
FORMATOS = {
    "json": (datos.RUTA_JSON, datos.cargar_json, datos.guardar_json),
    "xml": (datos.RUTA_XML, datos.cargar_xml, datos.guardar_xml),
}
CAMPOS = ["IdEmpleado", "strNombre", "NumDocumento", "StrDireccion",
          "StrTelefono", "StrEmail", "DtmIngreso"]
CANDADO = threading.Lock()  # evita escrituras simultáneas al archivo

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RE_TELEFONO = re.compile(r"^[0-9+ -]{7,20}$")
RE_RUTA = re.compile(r"^/api/empleados(?:/(\d+))?$")


def cargar(formato):
    ruta, cargar_fn, _ = FORMATOS[formato]
    if not os.path.exists(ruta):
        return []
    return cargar_fn(ruta)


def guardar(formato, empleados):
    ruta, _, guardar_fn = FORMATOS[formato]
    guardar_fn(ruta, empleados)


def validar(entrada, empleados, id_actual=None):
    """Devuelve (empleado_sin_id | None, errores). Reglas de la guía + sentido común."""
    errores = {}
    nombre = str(entrada.get("strNombre", "")).strip()
    documento = str(entrada.get("NumDocumento", "")).strip()
    direccion = str(entrada.get("StrDireccion", "")).strip()
    telefono = str(entrada.get("StrTelefono", "")).strip()
    email = str(entrada.get("StrEmail", "")).strip()
    ingreso = str(entrada.get("DtmIngreso", "")).strip() or datetime.date.today().isoformat()

    if not nombre:
        errores["strNombre"] = "El nombre es obligatorio."
    elif len(nombre) < 3 or len(nombre) > 50:
        errores["strNombre"] = "El nombre debe tener entre 3 y 50 caracteres."

    if not documento:
        errores["NumDocumento"] = "El documento es obligatorio."
    elif not documento.isdigit() or not 5 <= len(documento) <= 15:
        errores["NumDocumento"] = "Solo números, entre 5 y 15 dígitos."
    elif any(e.NumDocumento == int(documento) and e.IdEmpleado != id_actual
             for e in empleados):
        errores["NumDocumento"] = "Ya existe un empleado con este documento."

    if len(direccion) > 50:
        errores["StrDireccion"] = "Máximo 50 caracteres."
    if telefono and not RE_TELEFONO.match(telefono):
        errores["StrTelefono"] = "Teléfono inválido (7 a 20 dígitos, puede incluir + y espacios)."

    if not email:
        errores["StrEmail"] = "El email es obligatorio."
    elif len(email) > 50 or not RE_EMAIL.match(email):
        errores["StrEmail"] = "Email inválido (máximo 50 caracteres)."

    try:
        fecha = datetime.date.fromisoformat(ingreso)
        if fecha > datetime.date.today():
            errores["DtmIngreso"] = "La fecha de ingreso no puede ser futura."
    except ValueError:
        errores["DtmIngreso"] = "Fecha inválida (formato AAAA-MM-DD)."

    if errores:
        return None, errores
    return {"strNombre": nombre, "NumDocumento": int(documento),
            "StrDireccion": direccion, "StrTelefono": telefono,
            "StrEmail": email, "DtmIngreso": ingreso}, {}


def celda_csv(valor):
    """Neutraliza fórmulas (=, @, +x, -x) al abrir el CSV en Excel."""
    texto = str(valor)
    if re.match(r"^(=|@|\t|\r|[+-][^0-9 ])", texto):
        return "'" + texto
    return texto


class Manejador(BaseHTTPRequestHandler):
    server_version = "CrudEmpleados/1.0"

    # ---------- utilidades de respuesta ----------
    def _enviar(self, estado, cuerpo=b"", tipo="application/json; charset=utf-8", extra=None):
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self'; "
                         "img-src 'self' data:; frame-ancestors 'none'")
        for clave, valor in (extra or {}).items():
            self.send_header(clave, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _json(self, estado, objeto):
        self._enviar(estado, json.dumps(objeto, ensure_ascii=False).encode("utf-8"))

    def _error(self, estado, mensaje, errores=None):
        self._json(estado, {"mensaje": mensaje, "errores": errores or {}})

    def _leer_json(self):
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > 65536:
            raise ValueError("Cuerpo demasiado grande.")
        try:
            datos_in = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            raise ValueError("JSON inválido.")
        if not isinstance(datos_in, dict):
            raise ValueError("Se esperaba un objeto JSON.")
        return datos_in

    # ---------- estáticos ----------
    def _servir_archivo(self, ruta):
        try:
            with open(ruta, "rb") as f:
                cuerpo = f.read()
        except OSError:
            return self._error(404, "No encontrado.")
        tipo = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "image/svg+xml"):
            tipo += "; charset=utf-8"
        self._enviar(200, cuerpo, tipo)

    def _servir_static(self, ruta_url):
        relativa = ruta_url[len("/static/"):]
        absoluta = os.path.abspath(os.path.join(RAIZ_STATIC, relativa))
        if os.path.commonpath([absoluta, RAIZ_STATIC]) != RAIZ_STATIC or not os.path.isfile(absoluta):
            return self._error(404, "No encontrado.")
        self._servir_archivo(absoluta)

    # ---------- enrutado ----------
    def _despachar(self, metodo):
        url = urlparse(self.path)
        consulta = parse_qs(url.query)
        formato = (consulta.get("formato") or ["json"])[0].lower()

        if metodo in ("GET", "HEAD"):
            if url.path == "/":
                return self._servir_archivo(PLANTILLA)
            if url.path.startswith("/static/"):
                return self._servir_static(url.path)

        if not url.path.startswith("/api/"):
            return self._error(404, "No encontrado.")
        if formato not in FORMATOS:
            return self._error(400, "Formato no soportado (use json o xml).")

        try:
            if url.path == "/api/exportar" and metodo == "GET":
                return self._exportar(formato)
            if url.path == "/api/sincronizar" and metodo == "POST":
                return self._sincronizar(formato)
            coincide = RE_RUTA.match(url.path)
            if not coincide:
                return self._error(404, "No encontrado.")
            id_ruta = int(coincide.group(1)) if coincide.group(1) else None
            return self._empleados(metodo, formato, id_ruta)
        except ValueError as e:
            return self._error(400, str(e))
        except (OSError, Exception) as e:  # archivo ilegible, XML dañado, etc.
            return self._error(500, f"Error al procesar el archivo {formato}: {e}")

    def _empleados(self, metodo, formato, id_ruta):
        with CANDADO:
            empleados = cargar(formato)

            if metodo == "GET" and id_ruta is None:
                return self._json(200, [asdict(e) for e in empleados])

            if metodo == "POST" and id_ruta is None:
                valores, errores = validar(self._leer_json(), empleados)
                if errores:
                    return self._error(422, "Revisa los campos marcados.", errores)
                nuevo_id = max((e.IdEmpleado for e in empleados), default=0) + 1
                nuevo = Empleado(IdEmpleado=nuevo_id, **valores)
                empleados.append(nuevo)
                guardar(formato, empleados)
                return self._json(201, asdict(nuevo))

            if id_ruta is not None:
                actual = next((e for e in empleados if e.IdEmpleado == id_ruta), None)
                if actual is None:
                    return self._error(404, "El empleado no existe.")
                if metodo == "PUT":
                    valores, errores = validar(self._leer_json(), empleados, id_ruta)
                    if errores:
                        return self._error(422, "Revisa los campos marcados.", errores)
                    for campo, valor in valores.items():
                        setattr(actual, campo, valor)
                    guardar(formato, empleados)
                    return self._json(200, asdict(actual))
                if metodo == "DELETE":
                    empleados.remove(actual)
                    guardar(formato, empleados)
                    return self._enviar(204)

        return self._error(405, "Método no permitido.")

    def _exportar(self, formato):
        with CANDADO:
            empleados = cargar(formato)
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(CAMPOS)
        for e in empleados:
            escritor.writerow([celda_csv(getattr(e, campo)) for campo in CAMPOS])
        # utf-8-sig: Excel muestra bien las tildes
        self._enviar(200, salida.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8",
                     {"Content-Disposition": 'attachment; filename="empleados.csv"'})

    def _sincronizar(self, origen):
        destino = "xml" if origen == "json" else "json"
        with CANDADO:
            empleados = cargar(origen)
            guardar(destino, empleados)
        self._json(200, {"origen": origen, "destino": destino, "total": len(empleados)})

    do_GET = lambda self: self._despachar("GET")
    do_HEAD = lambda self: self._despachar("HEAD")
    do_POST = lambda self: self._despachar("POST")
    do_PUT = lambda self: self._despachar("PUT")
    do_DELETE = lambda self: self._despachar("DELETE")

    def log_message(self, formato, *args):
        pass


if __name__ == "__main__":
    servidor = ThreadingHTTPServer((HOST, PUERTO), Manejador)
    url = f"http://{HOST}:{PUERTO}"
    print(f"Panel de Talento Humano en {url}  (Ctrl+C para detener)")
    if not EN_HOSTING:
        webbrowser.open(url)   # el navegador solo se abre al ejecutarlo en local
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
