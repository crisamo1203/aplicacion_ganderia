import streamlit as st
import pandas as pd
from utils.data import get_ventas, insert_record, update_record, delete_record, TABLE_NAMES
from components.filters import apply_filters_to_dataframe
from components.dialogs import venta_dialog
from components.ui import (
    render_page_header, render_empty_state, render_toast_success,
    render_section_header, render_divider
)
from components.filters import apply_filters_to_dataframe as apply_filters
from modules.auth import has_permission
from config.constants import MENSAJES


def render_ventas() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("ventas", "create")
    can_update = has_permission("ventas", "update")
    can_delete = has_permission("ventas", "delete")

    render_page_header("Ventas", "Registro de transacciones comerciales", "💰")

    render_toolbar(can_create)

    df = get_ventas()
    df = apply_filters(df, "ventas")

    if df.empty:
        render_empty_state(
            "💰", "Sin ventas registradas",
            "No hay transacciones de venta en el sistema.",
            "➕ Registrar Venta", lambda: venta_dialog("create") if can_create else None
        )
        return

    render_ventas_table(df, can_update, can_delete)


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por tipo, detalle, método...", key="ventas_search")

    with c2:
        if can_create and st.button("➕ Nueva Venta", type="primary", use_container_width=True):
            venta_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_ventas(), "ventas")


def render_ventas_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("ventas_search", "").lower().strip()
    if search:
        mask = (
            df["tipo"].astype(str).str.lower().str.contains(search) |
            df["detalle"].astype(str).str.lower().str.contains(search) |
            df.get("metodo_pago", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
    if "valor_total" in df.columns:
        df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce").apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")

    display_cols = ["fecha", "tipo", "detalle", "cantidad", "valor_unitario", "valor_total", "metodo_pago", "observaciones"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "tipo": st.column_config.TextColumn("Tipo", width="small"),
        "detalle": st.column_config.TextColumn("Detalle", width="medium"),
        "cantidad": st.column_config.NumberColumn("Cant.", format="%.1f", width="small"),
        "valor_unitario": st.column_config.NumberColumn("V. Unit.", format="$%.0f", width="medium"),
        "valor_total": st.column_config.TextColumn("Total", width="medium"),
        "metodo_pago": st.column_config.TextColumn("Método", width="small"),
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
        show_venta_actions(row, can_update, can_delete)


def show_venta_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    venta_id = row.get("id")
    if not venta_id:
        return

    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            if can_update and st.button("✏️ Editar", key=f"edit_venta_{venta_id}", use_container_width=True):
                venta_dialog("update", row.to_dict())
        with c2:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_venta_{venta_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Venta", f"¿Eliminar la venta de {row.get('detalle', 'N/A')}?", key=f"del_venta_{venta_id}"):
                    delete_record(TABLE_NAMES["ventas"], venta_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()
        with c3:
            st.write("")
