# Autora: Valentina Alejandra Pérez Cardona
"""Capa de datos: lee y escribe los empleados en archivos XML y JSON."""
import json
import os
import xml.etree.ElementTree as ET

from modelo import Empleado

# Rutas absolutas a partir de la ubicación de este archivo, para que funcione
# sin importar desde qué carpeta se ejecute el programa.
CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_XML = os.path.join(CARPETA, "empleados.xml")
RUTA_JSON = os.path.join(CARPETA, "empleados.json")

def cargar_xml(ruta: str):
    """Lee el archivo XML y devuelve una lista de objetos Empleado."""
    raiz = ET.parse(ruta).getroot()          # elemento raíz <Empleados>
    empleados = []
    for empleado in raiz.findall('Empleado'):    # cada <Empleado> hijo de la raíz
        # .text devuelve siempre texto, por eso Id y documento se convierten a int
        IdEmpleado = int(empleado.find('IdEmpleado').text)
        strNombre = empleado.find('strNombre').text
        NumDocumento = int(empleado.find('NumDocumento').text)
        StrDireccion = empleado.find('StrDireccion').text
        StrTelefono = empleado.find('StrTelefono').text
        StrEmail = empleado.find('StrEmail').text
        DtmIngreso = empleado.find('DtmIngreso').text

        empleados.append(Empleado(IdEmpleado, strNombre,
        NumDocumento, StrDireccion, StrTelefono, StrEmail, DtmIngreso))

    return empleados

def guardar_xml(ruta: str, empleados: list):
    """Escribe la lista de empleados en un archivo XML."""
    root = ET.Element('Empleados')
    for empleado in empleados:
        el = ET.SubElement(root, 'Empleado')
        # En XML todo es texto, por eso los números se convierten con str()
        ET.SubElement(el, 'IdEmpleado').text = str(empleado.IdEmpleado)
        ET.SubElement(el, 'strNombre').text = empleado.strNombre
        ET.SubElement(el, 'NumDocumento').text = str(empleado.NumDocumento)
        ET.SubElement(el, 'StrDireccion').text = empleado.StrDireccion
        ET.SubElement(el, 'StrTelefono').text = empleado.StrTelefono
        ET.SubElement(el, 'StrEmail').text = empleado.StrEmail
        ET.SubElement(el, 'DtmIngreso').text = empleado.DtmIngreso

    ET.indent(root)    # deja el XML con sangría para que sea legible
    # utf-8 conserva las tildes; xml_declaration agrega <?xml ...?> al inicio
    ET.ElementTree(root).write(ruta, encoding='utf-8', xml_declaration=True)

def cargar_json(ruta: str):
    """Lee el archivo JSON y devuelve una lista de objetos Empleado."""
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)       # lista de diccionarios
    empleados = []
    for empleado in datos:
        IdEmpleado = int(empleado['IdEmpleado'])
        strNombre = empleado['strNombre']
        NumDocumento = int(empleado['NumDocumento'])
        StrDireccion = empleado['StrDireccion']
        StrTelefono = empleado['StrTelefono']
        StrEmail = empleado['StrEmail']
        DtmIngreso = empleado['DtmIngreso']

        empleados.append(Empleado(IdEmpleado, strNombre,
        NumDocumento, StrDireccion, StrTelefono, StrEmail, DtmIngreso))

    return empleados

def guardar_json(ruta: str, empleados: list):
    """Escribe la lista de empleados en un archivo JSON."""
    # Cada objeto Empleado se convierte en un diccionario
    empleados_data = []
    for empleado in empleados:
        empleados_data.append({
            'IdEmpleado': empleado.IdEmpleado,
            'strNombre': empleado.strNombre,
            'NumDocumento': empleado.NumDocumento,
            'StrDireccion': empleado.StrDireccion,
            'StrTelefono': empleado.StrTelefono,
            'StrEmail': empleado.StrEmail,
            'DtmIngreso': empleado.DtmIngreso
        })

    with open(ruta, 'w', encoding='utf-8') as f:
        # ensure_ascii=False conserva tildes y ñ; indent=4 lo deja legible
        json.dump(empleados_data, f, indent=4, ensure_ascii=False)

# Prueba rápida: ejecutar este archivo solo imprime los empleados de ambos formatos
if __name__ == "__main__":
    for e in cargar_xml("empleados.xml"):
        print(e)
    for e in cargar_json("empleados.json"):
        print(e)
