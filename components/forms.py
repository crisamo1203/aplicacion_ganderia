import streamlit as st
from datetime import date
from typing import Any, Dict, List, Optional, Callable, Type
from pydantic import BaseModel
from utils.validators import validate_form
from config.constants import (
    ClaseAnimal, SexoAnimal, EstadoAnimal, TipoAnimal,
    PropositoAnimal, EspecieAnimal, OrigenAnimal,
    TipoVenta, MetodoPago, TipoMovimiento, ProcedimientoSalud,
    PrediosFijos, PropietariosConocidos, GrupoUsuario
)


class FormField:
    def __init__(
        self,
        name: str,
        label: str,
        field_type: str = "text",
        required: bool = False,
        options: Optional[List[str]] = None,
        help: Optional[str] = None,
        default: Any = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: float = 1.0,
        placeholder: str = "",
        disabled: bool = False,
        option_labels: Optional[List[str]] = None
    ):
        self.name = name
        self.label = label
        self.field_type = field_type
        self.required = required
        self.options = options
        self.option_labels = option_labels
        self.help = help
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.placeholder = placeholder
        self.disabled = disabled


def render_form_field(field: FormField, value: Any = None, key_prefix: str = "") -> Any:
    key = f"{key_prefix}_{field.name}" if key_prefix else field.name
    default = value if value is not None else field.default

    if field.field_type == "text":
        return st.text_input(
            field.label + (" *" if field.required else ""),
            value=default or "",
            placeholder=field.placeholder,
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "textarea":
        return st.text_area(
            field.label + (" *" if field.required else ""),
            value=default or "",
            placeholder=field.placeholder,
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "select":
        index = 0
        if default and field.options and default in field.options:
            index = field.options.index(default)
        option_labels = dict(zip(field.options or [], field.option_labels or []))
        return st.selectbox(
            field.label + (" *" if field.required else ""),
            options=field.options or [],
            format_func=lambda option: option_labels.get(option, option),
            index=index,
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "multiselect":
        return st.multiselect(
            field.label + (" *" if field.required else ""),
            options=field.options or [],
            default=default if isinstance(default, list) else [],
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "date":
        return st.date_input(
            field.label + (" *" if field.required else ""),
            value=default if isinstance(default, date) else None,
            help=field.help,
            disabled=field.disabled,
            key=key,
            format="DD/MM/YYYY"
        )
    elif field.field_type == "number":
        initial_number = (
            float(default) if default is not None
            else float(field.min_value) if field.min_value is not None and field.min_value > 0
            else 0.0
        )
        return st.number_input(
            field.label + (" *" if field.required else ""),
            value=initial_number,
            min_value=float(field.min_value) if field.min_value is not None else None,
            max_value=float(field.max_value) if field.max_value is not None else None,
            step=float(field.step),
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "integer":
        return st.number_input(
            field.label + (" *" if field.required else ""),
            value=int(default) if default is not None else 0,
            min_value=int(field.min_value) if field.min_value is not None else 0,
            max_value=int(field.max_value) if field.max_value is not None else None,
            step=int(field.step),
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    elif field.field_type == "checkbox":
        return st.checkbox(
            field.label,
            value=bool(default),
            help=field.help,
            disabled=field.disabled,
            key=key
        )
    else:
        return st.text_input(field.label, value=str(default) if default else "", key=key)


def get_animal_form_fields() -> List[FormField]:
    from utils.data import get_lotes
    lotes = get_lotes()
    lote_ids = lotes["id"].astype(str).tolist() if not lotes.empty and "id" in lotes.columns else []
    lote_labels = [
        " · ".join(str(value) for value in [row.get("nombre", "Lote"), row.get("predio", "")] if value)
        for row in lotes.to_dict("records")
    ] if lote_ids else []
    return [
        FormField("nombre", "Nombre / Identificación", "text", required=True, placeholder="Ej: Novilla 001"),
        FormField("arete", "Arete", "text", required=True, placeholder="Ej: CO-12345678"),
        FormField("clase", "Clase", "select", required=True, options=ClaseAnimal.opciones()),
        FormField("raza", "Raza", "text", placeholder="Ej: Holstein, Brahman, Isa Brown"),
        FormField("propietario", "Propietario", "select", options=PropietariosConocidos.opciones()),
        FormField("lote_id", "Lote / predio", "select", required=True, options=lote_ids,
                  help="Selecciona el lote activo al que pertenece el animal.", option_labels=lote_labels),
        FormField("fecha_nacimiento", "Fecha de Nacimiento", "date"),
        FormField("sexo", "Sexo", "select", options=SexoAnimal.opciones()),
        FormField("estado", "Estado", "select", options=EstadoAnimal.opciones()),
        FormField("tipo", "Tipo", "select", options=TipoAnimal.opciones()),
        FormField("proposito", "Propósito", "select", options=PropositoAnimal.opciones()),
        FormField("especie", "Especie", "select", options=EspecieAnimal.opciones()),
        FormField("origen", "Origen", "select", options=OrigenAnimal.opciones()),
        FormField("proveedor", "Proveedor", "text", placeholder="Nombre del proveedor"),
        FormField("valor_compra", "Valor Compra", "number", min_value=0, step=1000),
        FormField("valor_venta", "Valor Venta", "number", min_value=0, step=1000),
        FormField("marca", "Marca", "text", placeholder="Marca o señal"),
        FormField("color", "Color", "text", placeholder="Color del animal"),
        FormField("peso_kg", "Peso Actual (kg)", "number", min_value=0, step=0.1),
        FormField("observaciones", "Observaciones", "textarea", placeholder="Notas adicionales"),
    ]


def _predio_select_options():
    from utils.data import get_predios
    predios = get_predios()
    if predios.empty or "id" not in predios.columns:
        return [""], ["Sin predio disponible"]
    ids = [""] + predios["id"].astype(str).tolist()
    labels = ["Sin predio"] + predios.get("nombre", predios["id"]).fillna("Predio").astype(str).tolist()
    return ids, labels


def _animal_select_options():
    from utils.data import get_animales
    animales = get_animales()
    if animales.empty or "id" not in animales.columns:
        return [""], ["Sin animales disponibles"]
    labels = []
    for row in animales.to_dict("records"):
        name = row.get("arete") or row.get("nombre") or str(row["id"])
        detail = row.get("nombre") if row.get("arete") and row.get("nombre") else ""
        labels.append(f"{name} · {detail}" if detail else str(name))
    return [""] + animales["id"].astype(str).tolist(), ["Sin animal"] + labels


def get_venta_form_fields() -> List[FormField]:
    predio_ids, predio_labels = _predio_select_options()
    return [
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("predio_id", "Predio", "select", options=predio_ids, option_labels=predio_labels),
        FormField("clase", "Clase", "select", options=ClaseAnimal.opciones()),
        FormField("tipo", "Tipo", "select", required=True, options=TipoVenta.opciones()),
        FormField("detalle", "Detalle", "text", placeholder="Descripción de la venta"),
        FormField("cantidad", "Cantidad", "number", required=True, min_value=0.01, step=1.0),
        FormField("valor_unitario", "Valor Unitario", "number", required=True, min_value=0, step=1000),
        FormField("metodo_pago", "Método de Pago", "select", options=MetodoPago.opciones()),
        FormField("observaciones", "Observaciones", "textarea"),
    ]


def get_produccion_form_fields() -> List[FormField]:
    predio_ids, predio_labels = _predio_select_options()
    animal_ids, animal_labels = _animal_select_options()
    return [
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("predio_id", "Predio", "select", options=predio_ids, option_labels=predio_labels),
        FormField("animal_id", "Animal (opcional)", "select", options=animal_ids, option_labels=animal_labels),
        FormField("clase", "Clase", "select", options=ClaseAnimal.opciones()),
        FormField("nombre_referencia", "Referencia", "text", placeholder="Lote o grupo"),
        FormField("ordeno", "¿Ordeñó?", "checkbox"),
        FormField("kilos_leche", "Kilos Leche", "number", min_value=0, step=0.1),
        FormField("litros_leche", "Litros Leche", "number", min_value=0, step=0.1),
        FormField("cantidad_huevos", "Cantidad Huevos", "integer", min_value=0, step=1),
        FormField("observaciones", "Observaciones", "textarea"),
    ]


def get_pesaje_form_fields() -> List[FormField]:
    animal_ids, animal_labels = _animal_select_options()
    return [
        FormField("animal_id", "Animal", "select", required=True, options=animal_ids[1:], option_labels=animal_labels[1:]),
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("peso_kg", "Peso (kg)", "number", required=True, min_value=0.1, step=0.1),
        FormField("nota", "Nota", "textarea", placeholder="Observaciones del pesaje"),
    ]


def get_movimiento_form_fields() -> List[FormField]:
    predio_ids, predio_labels = _predio_select_options()
    animal_ids, animal_labels = _animal_select_options()
    return [
        FormField("animal_id", "Animal (opcional)", "select", options=animal_ids, option_labels=animal_labels),
        FormField("predio_id", "Predio", "select", options=predio_ids, option_labels=predio_labels),
        FormField("tipo", "Tipo de Movimiento", "select", required=True, options=TipoMovimiento.opciones()),
        FormField("valor", "Valor", "number", min_value=0, step=1000),
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("comentarios", "Comentarios", "textarea"),
    ]


def get_gasto_form_fields() -> List[FormField]:
    predio_ids, predio_labels = _predio_select_options()
    return [
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("predio_id", "Predio", "select", options=predio_ids, option_labels=predio_labels),
        FormField("detalle", "Detalle", "text", required=True, placeholder="Concepto del gasto"),
        FormField("valor", "Valor", "number", required=True, min_value=0, step=1000),
        FormField("metodo_pago", "Método de Pago", "select", options=MetodoPago.opciones()),
        FormField("inversor", "Inversor", "text", placeholder="Quién realizó el gasto"),
        FormField("observaciones", "Observaciones", "textarea"),
    ]


def get_salud_form_fields() -> List[FormField]:
    animal_ids, animal_labels = _animal_select_options()
    return [
        FormField("animal_id", "Animal", "select", required=True, options=animal_ids[1:], option_labels=animal_labels[1:]),
        FormField("fecha", "Fecha", "date", required=True, default=date.today()),
        FormField("tipo_procedimiento", "Procedimiento", "select", required=True, options=ProcedimientoSalud.opciones()),
        FormField("medicamento", "Medicamento", "text", placeholder="Nombre y dosis"),
        FormField("veterinario", "Veterinario", "text", placeholder="Nombre del profesional"),
        FormField("proxima_cita", "Próxima Cita", "date"),
        FormField("observaciones", "Observaciones", "textarea"),
    ]


def get_profile_form_fields() -> List[FormField]:
    return [
        FormField("nombre", "Nombre", "text", required=True),
        FormField("telefono", "Teléfono", "text", placeholder="+57 XXX XXX XXXX"),
        FormField("rol", "Rol", "select", required=True, options=GrupoUsuario.opciones()),
        FormField("grupo", "Grupo", "select", options=GrupoUsuario.opciones()),
        FormField("activo", "Usuario Activo", "checkbox", default=True),
    ]


def render_form_dialog(
    title: str,
    fields: List[FormField],
    submit_label: str = "Guardar",
    initial_data: Optional[Dict[str, Any]] = None,
    validator: Optional[Type[BaseModel]] = None,
    on_submit: Optional[Callable[[Dict[str, Any]], bool]] = None,
    key: str = "form_dialog"
) -> Optional[Dict[str, Any]]:
    @st.dialog(title)
    def _dialog():
        form_data = {}
        cols_per_row = 3
        required_options_missing = [
            field for field in fields
            if field.required and field.field_type == "select" and not field.options
        ]
        if required_options_missing:
            names = ", ".join(field.label for field in required_options_missing)
            st.warning(f"No hay opciones disponibles para: {names}. Revisa los catálogos y permisos en Supabase.")

        for i, field in enumerate(fields):
            if i % cols_per_row == 0:
                cols = st.columns(cols_per_row)
            col = cols[i % cols_per_row]

            with col:
                initial_val = initial_data.get(field.name) if initial_data else None
                form_data[field.name] = render_form_field(field, initial_val, key)

        st.divider()

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Cancelar", use_container_width=True):
                st.session_state[f"{key}_result"] = None
                st.rerun()
        with c2:
            if st.button(submit_label, type="primary", use_container_width=True,
                         disabled=bool(required_options_missing)):
                for nullable_id in ("predio_id", "animal_id"):
                    if form_data.get(nullable_id) == "":
                        form_data[nullable_id] = None
                if validator:
                    is_valid, model, errors = validate_form(validator, form_data)
                    if not is_valid:
                        for err in errors:
                            st.error(err)
                        return
                    form_data = model.model_dump(exclude_unset=True, exclude_none=True)

                if on_submit:
                    success = on_submit(form_data)
                    if success:
                        st.session_state[f"{key}_result"] = form_data
                        st.rerun()
                else:
                    st.session_state[f"{key}_result"] = form_data
                    st.rerun()

    _dialog()
    return st.session_state.get(f"{key}_result")


def render_confirm_dialog(
    title: str,
    message: str,
    confirm_label: str = "Confirmar",
    cancel_label: str = "Cancelar",
    key: str = "confirm",
    type: str = "primary"
) -> bool:
    @st.dialog(title)
    def _dialog():
        st.write(message)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(confirm_label, type=type, use_container_width=True):
                st.session_state[f"{key}_result"] = True
                st.rerun()
        with c2:
            if st.button(cancel_label, use_container_width=True):
                st.session_state[f"{key}_result"] = False
                st.rerun()

    _dialog()
    return st.session_state.get(f"{key}_result", False)
