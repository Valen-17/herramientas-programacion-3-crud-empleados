// Autora: Valentina Alejandra Pérez Cardona
"use strict";

// Lógica de la interfaz web: pide los datos a la API, dibuja la tabla,
// valida el formulario y envía los cambios (crear, editar, eliminar).

// Atajo para document.querySelector
const $ = (selector, raiz = document) => raiz.querySelector(selector);

// Estado de la pantalla: todo lo que cambia vive aquí y render() lo dibuja
const state = {
    formato: "json",
    empleados: [],
    busqueda: "",
    orden: { campo: "IdEmpleado", dir: 1 },
    editandoId: null,   // Id que se está editando (null = empleado nuevo)
    eliminarId: null,   // Id pendiente de confirmar para eliminar
};

// Expresiones regulares para validar email y teléfono
const REGLAS = {
    email: /^[^@\s]+@[^@\s]+\.[^@\s]+$/,
    telefono: /^[0-9+ -]{7,20}$/,
};

// ---------- utilidades ----------
// Escapa caracteres especiales de HTML para evitar inyección de código (XSS)
function esc(valor) {
    return String(valor ?? "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Fecha de hoy en formato AAAA-MM-DD
function hoyISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Convierte 2021-01-28 en 28/01/2021 solo para mostrarla
function fechaLegible(iso) {
    const [a, m, d] = String(iso).split("-");
    return a && m && d ? `${d}/${m}/${a}` : iso;
}

// Primeras letras de las dos primeras palabras del nombre (para el avatar)
function iniciales(nombre) {
    return nombre.trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
}

// Años transcurridos desde una fecha (para los indicadores de antigüedad)
function aniosDesde(iso) {
    const ms = Date.now() - new Date(iso + "T00:00:00").getTime();
    return ms / (365.25 * 24 * 3600 * 1000);
}

// Muestra una notificación temporal (toast) que desaparece a los 3,5 segundos
function aviso(mensaje, tipo = "ok") {
    const el = document.createElement("div");
    el.className = "toast" + (tipo === "error" ? " toast--error" : "");
    el.textContent = mensaje;
    $("#toasts").append(el);
    setTimeout(() => el.remove(), 3500);
}

// Llama a la API con fetch; si el servidor responde con error, lanza una excepción
// que lleva el mensaje y los errores por campo
async function api(ruta, opciones = {}) {
    const respuesta = await fetch(ruta, {
        headers: { "Content-Type": "application/json" },
        ...opciones,
    });
    const cuerpo = respuesta.status === 204 ? null : await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
        const error = new Error(cuerpo?.mensaje || "Ocurrió un error inesperado.");
        error.errores = cuerpo?.errores || {};
        throw error;
    }
    return cuerpo;
}

// Arma la URL de la API según el formato activo (json o xml)
const urlApi = (ruta = "") => `/api/empleados${ruta}?formato=${state.formato}`;

// ---------- carga y render ----------
async function cargar() {
    try {
        state.empleados = await api(urlApi());
        render();
    } catch (e) {
        aviso(e.message, "error");
    }
}

// Aplica el filtro de búsqueda y el orden elegido a la lista de empleados
function empleadosVisibles() {
    const q = state.busqueda.trim().toLowerCase();
    const { campo, dir } = state.orden;
    return state.empleados
        .filter((e) => !q || [e.strNombre, e.NumDocumento, e.StrEmail, e.StrTelefono, e.StrDireccion]
            .some((v) => String(v).toLowerCase().includes(q)))
        .sort((a, b) => {
            const x = a[campo], y = b[campo];
            return (typeof x === "number" ? x - y : String(x).localeCompare(String(y), "es")) * dir;
        });
}

function render() {
    renderKpis();
    renderTabla();
    $("#kpiArchivo").textContent = `empleados.${state.formato}`;
    $("#btnExportar").href = `/api/exportar?formato=${state.formato}`;
    document.querySelectorAll(".segmented__btn").forEach((b) => {
        const activo = b.dataset.formato === state.formato;
        b.classList.toggle("is-active", activo);
        b.setAttribute("aria-checked", String(activo));
    });
}

// Calcula los indicadores: total, ingresos del último año y antigüedad promedio
function renderKpis() {
    const lista = state.empleados;
    const nuevos = lista.filter((e) => aniosDesde(e.DtmIngreso) <= 1).length;
    const promedio = lista.length
        ? lista.reduce((suma, e) => suma + Math.max(aniosDesde(e.DtmIngreso), 0), 0) / lista.length
        : 0;
    $("#kpiTotal").textContent = lista.length;
    $("#kpiNuevos").textContent = nuevos;
    $("#kpiAntiguedad").textContent = promedio.toFixed(1);
}

// Dibuja las filas de la tabla; todo texto del usuario pasa por esc()
function renderTabla() {
    const visibles = empleadosVisibles();
    const cuerpo = $("#tblBody");

    if (visibles.length === 0) {
        cuerpo.innerHTML = `<tr><td colspan="7" class="table__vacio">${
            state.empleados.length ? "Ningún empleado coincide con la búsqueda." : "Aún no hay empleados. Agrega el primero con “Nuevo empleado”."}</td></tr>`;
    } else {
        cuerpo.innerHTML = visibles.map((e) => `
            <tr data-id="${e.IdEmpleado}">
                <td class="mono">#${e.IdEmpleado}</td>
                <td>
                    <div class="persona">
                        <span class="avatar avatar--${e.IdEmpleado % 5}" aria-hidden="true">${esc(iniciales(e.strNombre))}</span>
                        <div>
                            <div class="persona__nombre">${esc(e.strNombre)}</div>
                            <div class="persona__email">${esc(e.StrEmail)}</div>
                        </div>
                    </div>
                </td>
                <td class="mono">${esc(e.NumDocumento)}</td>
                <td class="mono">${esc(e.StrTelefono)}</td>
                <td>${esc(e.StrDireccion)}</td>
                <td class="mono">${esc(fechaLegible(e.DtmIngreso))}</td>
                <td class="table__acciones">
                    <button type="button" class="icon-btn" data-accion="editar" aria-label="Editar a ${esc(e.strNombre)}" title="Editar">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                    </button>
                    <button type="button" class="icon-btn icon-btn--danger" data-accion="eliminar" aria-label="Eliminar a ${esc(e.strNombre)}" title="Eliminar">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m19 6-1 14H6L5 6"/></svg>
                    </button>
                </td>
            </tr>`).join("");
    }

    $("#lblConteo").textContent = `Mostrando ${visibles.length} de ${state.empleados.length} empleados`;
    document.querySelectorAll("th[data-campo]").forEach((th) => {
        th.classList.remove("orden-asc", "orden-desc");
        if (th.dataset.campo === state.orden.campo) {
            th.classList.add(state.orden.dir === 1 ? "orden-asc" : "orden-desc");
        }
    });
}

// ---------- formulario ----------
const formulario = $("#frmEmpleado");
const dlgEmpleado = $("#dlgEmpleado");
const dlgConfirmar = $("#dlgConfirmar");

// Quita el mensaje de error de un campo
function limpiarError(campo) {
    const mensaje = formulario.querySelector(`[data-error="${campo}"]`);
    if (!mensaje) return;
    mensaje.textContent = "";
    const field = mensaje.closest(".field");
    field.classList.remove("is-invalid");
    field.querySelector("input").removeAttribute("aria-invalid");
}

function limpiarErrores() {
    formulario.querySelectorAll("[data-error]").forEach((s) => limpiarError(s.dataset.error));
}

// Muestra el error debajo de cada campo y pone el foco en el primero con error
function mostrarErrores(errores, enfocar = true) {
    for (const [campo, texto] of Object.entries(errores)) {
        const mensaje = formulario.querySelector(`[data-error="${campo}"]`);
        if (mensaje) {
            mensaje.textContent = texto;
            const field = mensaje.closest(".field");
            field.classList.add("is-invalid");
            field.querySelector("input").setAttribute("aria-invalid", "true");
        }
    }
    if (enfocar) {
        const primero = formulario.querySelector(".is-invalid input");
        if (primero) primero.focus();
    }
}

function valoresFormulario() {
    return Object.fromEntries(
        [...new FormData(formulario)].map(([k, v]) => [k, String(v).trim()]));
}

// Validación al salir de un campo y limpieza al corregirlo
formulario.querySelectorAll("input").forEach((input) => {
    input.addEventListener("blur", () => {
        if (!dlgEmpleado.open || !input.value.trim()) return;  // los vacíos se validan al guardar
        const errores = validarCliente(valoresFormulario());
        limpiarError(input.name);
        if (errores[input.name]) mostrarErrores({ [input.name]: errores[input.name] }, false);
    });
    input.addEventListener("input", () => limpiarError(input.name));
});

// Validación en el navegador (da respuesta inmediata). El servidor repite las
// mismas reglas, porque la validación del cliente se puede saltar.
function validarCliente(v) {
    const e = {};
    if (!v.strNombre) e.strNombre = "El nombre es obligatorio.";
    else if (v.strNombre.length < 3 || v.strNombre.length > 50) e.strNombre = "El nombre debe tener entre 3 y 50 caracteres.";
    if (!v.NumDocumento) e.NumDocumento = "El documento es obligatorio.";
    else if (!/^\d{5,15}$/.test(v.NumDocumento)) e.NumDocumento = "Solo números, entre 5 y 15 dígitos.";
    if (v.StrTelefono && !REGLAS.telefono.test(v.StrTelefono)) e.StrTelefono = "Teléfono inválido (7 a 20 dígitos, puede incluir + y espacios).";
    if (!v.StrEmail) e.StrEmail = "El email es obligatorio.";
    else if (!REGLAS.email.test(v.StrEmail)) e.StrEmail = "Email inválido.";
    if (v.DtmIngreso && v.DtmIngreso > hoyISO()) e.DtmIngreso = "La fecha de ingreso no puede ser futura.";
    return e;
}

// Abre el formulario vacío (nuevo) o con los datos del empleado (editar)
function abrirFormulario(empleado = null) {
    state.editandoId = empleado ? empleado.IdEmpleado : null;
    limpiarErrores();
    formulario.reset();
    $("#dlgTitulo").textContent = empleado ? `Editar empleado #${empleado.IdEmpleado}` : "Nuevo empleado";
    $("#txtIngreso").max = hoyISO();
    $("#txtIngreso").value = empleado ? empleado.DtmIngreso : hoyISO();
    if (empleado) {
        $("#txtNombre").value = empleado.strNombre;
        $("#txtDocumento").value = empleado.NumDocumento;
        $("#txtTelefono").value = empleado.StrTelefono;
        $("#txtEmail").value = empleado.StrEmail;
        $("#txtDireccion").value = empleado.StrDireccion;
    }
    dlgEmpleado.showModal();
    $("#txtNombre").focus();
}

// Guardar: valida, y según editandoId envía PUT (editar) o POST (crear)
formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limpiarErrores();
    const datos = valoresFormulario();
    const errores = validarCliente(datos);
    if (Object.keys(errores).length) {
        mostrarErrores(errores);
        return;
    }

    const boton = $("#btnGuardar");
    boton.disabled = true;
    boton.textContent = "Guardando…";
    try {
        const editando = state.editandoId !== null;
        await api(urlApi(editando ? `/${state.editandoId}` : ""), {
            method: editando ? "PUT" : "POST",
            body: JSON.stringify(datos),
        });
        dlgEmpleado.close();
        aviso(editando ? "Empleado actualizado." : "Empleado agregado.");
        await cargar();
    } catch (e) {
        if (Object.keys(e.errores).length) mostrarErrores(e.errores);
        else aviso(e.message, "error");
    } finally {
        boton.disabled = false;
        boton.textContent = "Guardar";
    }
});

// ---------- eventos ----------
// Clic en el fondo oscuro cierra el modal (Esc ya lo cierra de forma nativa)
[dlgEmpleado, dlgConfirmar].forEach((dlg) =>
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); }));

$("#btnNuevo").addEventListener("click", () => abrirFormulario());

// Un solo listener para los botones Editar/Eliminar de todas las filas (delegación de eventos)
$("#tblBody").addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-accion]");
    if (!boton) return;
    const id = Number(boton.closest("tr").dataset.id);
    const empleado = state.empleados.find((e) => e.IdEmpleado === id);
    if (!empleado) return;
    if (boton.dataset.accion === "editar") {
        abrirFormulario(empleado);
    } else {
        state.eliminarId = id;
        $("#lblConfirmar").textContent = `¿Seguro que deseas eliminar a ${empleado.strNombre}? Esta acción quita el registro del archivo ${state.formato.toUpperCase()}.`;
        dlgConfirmar.showModal();
    }
});

$("#btnConfNo").addEventListener("click", () => dlgConfirmar.close());
$("#btnConfSi").addEventListener("click", async () => {
    try {
        await api(urlApi(`/${state.eliminarId}`), { method: "DELETE" });
        aviso("Empleado eliminado.");
        await cargar();
    } catch (e) {
        aviso(e.message, "error");
    } finally {
        dlgConfirmar.close();
    }
});

document.querySelectorAll("[data-cerrar]").forEach((b) =>
    b.addEventListener("click", () => dlgEmpleado.close()));

$("#txtBuscar").addEventListener("input", (e) => {
    state.busqueda = e.target.value;
    renderTabla();
});

// Clic en un encabezado: ordena por esa columna; otro clic invierte el orden
document.querySelector("thead").addEventListener("click", (evento) => {
    const th = evento.target.closest("th[data-campo]");
    if (!th) return;
    const campo = th.dataset.campo;
    state.orden = { campo, dir: state.orden.campo === campo ? -state.orden.dir : 1 };
    renderTabla();
});

document.querySelectorAll(".segmented__btn").forEach((b) =>
    b.addEventListener("click", () => {
        state.formato = b.dataset.formato;
        cargar();
    }));

// Copia los datos del formato activo al otro archivo (JSON -> XML o al revés)
$("#btnSincronizar").addEventListener("click", async () => {
    const destino = state.formato === "json" ? "XML" : "JSON";
    try {
        const r = await api(`/api/sincronizar?formato=${state.formato}`, { method: "POST" });
        aviso(`${r.total} empleados copiados a empleados.${destino.toLowerCase()}.`);
    } catch (e) {
        aviso(e.message, "error");
    }
});

// Al abrir la página se cargan los empleados
cargar();
