import streamlit as st
import pandas as pd
from utils.data import get_produccion, insert_record, update_record, delete_record, TABLE_NAMES
from components.filters import apply_filters_to_dataframe
from components.dialogs import produccion_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success
from modules.auth import has_permission
from config.constants import MENSAJES


def render_produccion() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("produccion", "create")
    can_update = has_permission("produccion", "update")
    can_delete = has_permission("produccion", "delete")

    render_page_header("Producción", "Registro diario de producción agrícola y pecuaria", "🥚")

    render_toolbar(can_create)

    df = get_produccion()

    if df.empty:
        render_empty_state(
            "🥚", "Sin producción registrada",
            "No hay registros de producción en el sistema.",
            "➕ Registrar Producción", lambda: produccion_dialog("create") if can_create else None
        )
        return

    render_produccion_table(df, can_update, can_delete)


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por animal, predio, tipo...", key="produccion_search")

    with c2:
        if can_create and st.button("➕ Nueva Producción", type="primary", use_container_width=True):
            produccion_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_produccion(), "produccion")


def render_produccion_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("produccion_search", "").lower().strip()
    if search:
        mask = (
            df["animal"].astype(str).str.lower().str.contains(search) |
            df["nombre_referencia"].astype(str).str.lower().str.contains(search) |
            df["predio"].astype(str).str.lower().str.contains(search) |
            df["clase"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")

    display_cols = ["fecha", "animal", "clase", "nombre_referencia", "ordeno", "kilos_leche", "litros_leche", "cantidad_huevos", "observaciones"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "animal": st.column_config.TextColumn("Animal", width="medium"),
        "clase": st.column_config.TextColumn("Clase", width="small"),
        "nombre_referencia": st.column_config.TextColumn("Referencia", width="medium"),
        "ordeno": st.column_config.CheckboxColumn("Ordeñó", width="small"),
        "kilos_leche": st.column_config.NumberColumn("Kg Leche", format="%.1f", width="small"),
        "litros_leche": st.column_config.NumberColumn("L Leche", format="%.1f", width="small"),
        "cantidad_huevos": st.column_config.NumberColumn("Huevos", format="%d", width="small"),
        "observaciones": st.column_config.TextColumn("Obs.", width="large"),
    }

    if can_update or can_delete:
        df["acciones"] = ""

    selection = st.dataframe(
        df[display_cols + (["acciones"] if can_update or can_delete else [])],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500,
        on_select="rerun",
        selection_mode="single-row"
    )

    if selection and selection.selection.rows:
        row_idx = selection.selection.rows[0]
        row = df.iloc[row_idx]
        show_produccion_actions(row, can_update, can_delete)


def show_produccion_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    prod_id = row.get("id")
    if not prod_id:
        return

    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            if can_update and st.button("✏️ Editar", key=f"edit_prod_{prod_id}", use_container_width=True):
                produccion_dialog("update", row.to_dict())
        with c2:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_prod_{prod_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Producción", f"¿Eliminar el registro de {row.get('animal', 'N/A')} del {row.get('fecha', '')}?", key=f"del_prod_{prod_id}"):
                    delete_record(TABLE_NAMES["produccion"], prod_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()
