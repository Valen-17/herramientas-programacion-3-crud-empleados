# Autora: Valentina Alejandra Pérez Cardona
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from modelo import Empleado
from datos import (cargar_xml, guardar_xml, cargar_json, guardar_json,
                   RUTA_XML, RUTA_JSON)

class App(tk.Tk):
    """Ventana de escritorio (respaldo): tabla de empleados y formulario para agregar."""
    def __init__(self):
        super().__init__()
        self.title("Gestión de empleados")
        self.geometry("900x560")

        self.empleados = cargar_json(RUTA_JSON)   # lista en memoria

        self.crear_tabla()
        self.crear_formulario()
        self.refrescar_tabla()

    def crear_tabla(self):
        # Treeview es el control de tabla de tkinter (equivale al DataGridView)
        columnas = ("id", "nombre", "documento", "direccion",
                    "telefono", "email", "ingreso")
        self.dgvEmpleados = ttk.Treeview(self, columns=columnas, show="headings")
        encabezados = ["Id", "Nombre", "Documento", "Dirección",
                       "Teléfono", "Email", "Fecha ingreso"]
        for col, header in zip(columnas, encabezados):
            self.dgvEmpleados.heading(col, text=header)
            self.dgvEmpleados.column(col, width=100, anchor="center")
        self.dgvEmpleados.pack(fill="both", expand=True, padx=10, pady=10)

    def crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Datos del empleado")
        marco.pack(fill="x", padx=10, pady=5)

        # (etiqueta, nombre del atributo, fila, columna de la etiqueta)
        campos = [
            ("Nombre:", "txtNombre", 0, 0),
            ("Documento:", "txtDocumento", 0, 2),
            ("Dirección:", "txtDireccion", 1, 0),
            ("Teléfono:", "txtTelefono", 1, 2),
            ("Email:", "txtEmail", 2, 0),
            ("Fecha ingreso (AAAA-MM-DD):", "txtIngreso", 2, 2),
        ]
        # Se crea cada etiqueta con su caja de texto y se guarda la caja como
        # atributo (self.txtNombre, self.txtEmail...) usando setattr
        for texto, nombre, fila, col in campos:
            ttk.Label(marco, text=texto).grid(row=fila, column=col, padx=5, pady=5, sticky="e")
            entrada = ttk.Entry(marco, width=30)
            entrada.grid(row=fila, column=col + 1, padx=5, pady=5)
            setattr(self, nombre, entrada)

        botones = ttk.Frame(self)
        botones.pack(pady=5)
        self.btnAgregar = ttk.Button(botones, text="Agregar", command=self.agregar)
        self.btnAgregar.pack(side="left", padx=5)
        self.btnLimpiar = ttk.Button(botones, text="Limpiar", command=self.limpiar_campos)
        self.btnLimpiar.pack(side="left", padx=5)

    def refrescar_tabla(self):
        # Borra todas las filas y las vuelve a cargar desde la lista en memoria
        self.dgvEmpleados.delete(*self.dgvEmpleados.get_children())
        for e in self.empleados:
            self.dgvEmpleados.insert("", "end", values=(e.IdEmpleado, e.strNombre, e.NumDocumento,
                                                       e.StrDireccion, e.StrTelefono,
                                                       e.StrEmail, e.DtmIngreso))

    def limpiar_campos(self):
        for entrada in (self.txtNombre, self.txtDocumento, self.txtDireccion,
                        self.txtTelefono, self.txtEmail, self.txtIngreso):
            entrada.delete(0, tk.END)

    def agregar(self):
        # 1) Leer los campos y validar; si algo está mal se avisa y se sale
        nombre = self.txtNombre.get().strip()
        documento = self.txtDocumento.get().strip()
        email = self.txtEmail.get().strip()

        if not nombre or not documento or not email:
            messagebox.showwarning("Datos incompletos",
                                   "Nombre, documento y email son obligatorios.")
            return
        try:
            num_documento = int(documento)
        except ValueError:
            messagebox.showwarning("Documento inválido",
                                   "El documento debe ser numérico.")
            return
        if "@" not in email:
            messagebox.showwarning("Email inválido", "El email debe contener '@'.")
            return

        # Si la fecha queda vacía se usa la de hoy; fromisoformat falla si no es AAAA-MM-DD
        ingreso = self.txtIngreso.get().strip() or datetime.date.today().isoformat()
        try:
            datetime.date.fromisoformat(ingreso)
        except ValueError:
            messagebox.showwarning("Fecha inválida", "Use el formato AAAA-MM-DD.")
            return

        # 2) Crear el empleado con el siguiente Id, guardarlo en el JSON y refrescar la pantalla
        nuevo_id = max((e.IdEmpleado for e in self.empleados), default=0) + 1
        self.empleados.append(Empleado(nuevo_id, nombre, num_documento,
                                       self.txtDireccion.get().strip(),
                                       self.txtTelefono.get().strip(),
                                       email, ingreso))
        guardar_json(RUTA_JSON, self.empleados)
        self.refrescar_tabla()
        self.limpiar_campos()
        messagebox.showinfo("Éxito", "Empleado agregado.")

if __name__ == "__main__":
    App().mainloop()
