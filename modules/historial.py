import streamlit as st
import pandas as pd
from utils.data import get_movimientos, insert_record, update_record, delete_record, TABLE_NAMES
from components.filters import apply_filters_to_dataframe
from components.dialogs import movimiento_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success
from modules.auth import has_permission
from config.constants import MENSAJES


def render_historial() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("historial", "create")
    can_update = has_permission("historial", "update")
    can_delete = has_permission("historial", "delete")

    render_page_header("Historial", "Bitácora de eventos y trazabilidad del ganado", "📋")

    render_toolbar(can_create)

    df = get_movimientos()

    if df.empty:
        render_empty_state(
            "📋", "Sin movimientos registrados",
            "No hay eventos de trazabilidad en el sistema.",
            "➕ Registrar Movimiento", lambda: movimiento_dialog("create") if can_create else None
        )
        return

    render_historial_table(df, can_update, can_delete)


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por animal, tipo, predio...", key="historial_search")

    with c2:
        if can_create and st.button("➕ Nuevo Movimiento", type="primary", use_container_width=True):
            movimiento_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_movimientos(), "movimientos")


def render_historial_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("historial_search", "").lower().strip()
    if search:
        mask = (
            df["animal"].astype(str).str.lower().str.contains(search) |
            df["tipo_movimiento"].astype(str).str.lower().str.contains(search) |
            df["comentarios"].astype(str).str.lower().str.contains(search) |
            df["predio_origen"].astype(str).str.lower().str.contains(search) |
            df["predio_destino"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")

    display_cols = ["fecha", "animal", "tipo_movimiento", "predio_origen", "predio_destino", "valor", "comentarios"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="medium"),
        "animal": st.column_config.TextColumn("Animal", width="medium"),
        "tipo_movimiento": st.column_config.TextColumn("Tipo", width="medium"),
        "predio_origen": st.column_config.TextColumn("Origen", width="medium"),
        "predio_destino": st.column_config.TextColumn("Destino", width="medium"),
        "valor": st.column_config.NumberColumn("Valor", format="$%.0f", width="small"),
        "comentarios": st.column_config.TextColumn("Comentarios", width="large"),
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
        show_historial_actions(row, can_update, can_delete)


def show_historial_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    mov_id = row.get("id")
    if not mov_id:
        return

    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            if can_update and st.button("✏️ Editar", key=f"edit_mov_{mov_id}", use_container_width=True):
                movimiento_dialog("update", row.to_dict())
        with c2:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_mov_{mov_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Movimiento", f"¿Eliminar el movimiento {row.get('tipo_movimiento', '')}?", key=f"del_mov_{mov_id}"):
                    delete_record(TABLE_NAMES["movimientos"], mov_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()
