# Autora: Valentina Alejandra Pérez Cardona
"""Modelo de datos: define cómo es un empleado."""
from dataclasses import dataclass

# @dataclass genera automáticamente __init__, __repr__ y __eq__,
# así no hay que escribirlos a mano.
@dataclass
class Empleado:
    IdEmpleado: int      # identificador único (se asigna al agregar)
    strNombre: str       # nombre completo
    NumDocumento: int    # documento de identidad, solo números
    StrDireccion: str    # dirección de residencia (opcional)
    StrTelefono: str     # teléfono (texto, porque puede incluir +57 y espacios)
    StrEmail: str        # correo electrónico
    DtmIngreso: str      # fecha de ingreso en formato ISO AAAA-MM-DD
