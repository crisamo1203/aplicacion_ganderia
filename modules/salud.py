import streamlit as st
import pandas as pd
from utils.data import get_salud, insert_record, update_record, delete_record, TABLE_NAMES, get_animal_salud
from components.filters import apply_filters_to_dataframe
from components.dialogs import salud_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success
from components.charts import create_salud_calendario
from modules.auth import has_permission
from config.constants import MENSAJES, ProcedimientoSalud


def render_salud() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("salud", "create")
    can_update = has_permission("salud", "update")
    can_delete = has_permission("salud", "delete")

    render_page_header("Historial Médico", "Sanidad animal, vacunación, purgas y marcaciones", "🏥")

    render_calendario_proximas()

    render_toolbar(can_create)

    df = get_salud()

    if df.empty:
        render_empty_state(
            "🏥", "Sin procedimientos registrados",
            "No hay historial sanitario en el sistema.",
            "➕ Registrar Procedimiento", lambda: salud_dialog("create") if can_create else None
        )
        return

    render_salud_table(df, can_update, can_delete)


def render_calendario_proximas() -> None:
    salud = get_salud()
    if not salud.empty:
        with st.expander("📅 Próximas Citas Programadas", expanded=False):
            fig = create_salud_calendario(salud)
            st.plotly_chart(fig, use_container_width=True, key="salud_calendario")


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por animal, procedimiento, veterinario...", key="salud_search")

    with c2:
        if can_create and st.button("➕ Nuevo Procedimiento", type="primary", use_container_width=True):
            salud_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_salud(), "salud")


def render_salud_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("salud_search", "").lower().strip()
    if search:
        mask = (
            df["arete"].astype(str).str.lower().str.contains(search) |
            df["nombre"].astype(str).str.lower().str.contains(search) |
            df["tipo_procedimiento"].astype(str).str.lower().str.contains(search) |
            df["veterinario"].astype(str).str.lower().str.contains(search) |
            df["medicamento"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
    if "proxima_cita" in df.columns:
        df["proxima_cita"] = pd.to_datetime(df["proxima_cita"], errors="coerce").dt.strftime("%d/%m/%Y")

    if "cita_vencida" in df.columns:
        df["estado_cita"] = df["cita_vencida"].apply(lambda x: "🔴 Vencida" if x else "🟢 Vigente")

    display_cols = ["fecha", "arete", "nombre", "tipo_procedimiento", "medicamento", "veterinario", "proxima_cita", "estado_cita", "observaciones"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "arete": st.column_config.TextColumn("Arete", width="small"),
        "nombre": st.column_config.TextColumn("Animal", width="medium"),
        "tipo_procedimiento": st.column_config.TextColumn("Procedimiento", width="medium"),
        "medicamento": st.column_config.TextColumn("Medicamento", width="medium"),
        "veterinario": st.column_config.TextColumn("Veterinario", width="medium"),
        "proxima_cita": st.column_config.TextColumn("Próx. Cita", width="small"),
        "estado_cita": st.column_config.TextColumn("Estado", width="small"),
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
        show_salud_actions(row, can_update, can_delete)


def show_salud_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    salud_id = row.get("id")
    animal_id = row.get("animal_id")
    if not salud_id:
        return

    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            if animal_id and st.button("📋 Ver Historial", key=f"hist_salud_{salud_id}", use_container_width=True):
                _render_salud_history(animal_id, f"{row.get('nombre', '')} ({row.get('arete', '')})")
        with c2:
            if can_update and st.button("✏️ Editar", key=f"edit_salud_{salud_id}", use_container_width=True):
                salud_dialog("update", row.to_dict())
        with c3:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_salud_{salud_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Procedimiento", f"¿Eliminar {row.get('tipo_procedimiento', '')}?", key=f"del_salud_{salud_id}"):
                    delete_record(TABLE_NAMES["salud"], salud_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()


def _render_salud_history(animal_id: str, animal_nombre: str) -> None:
    """Renderiza el historial sanitario dentro de un diálogo."""
    @st.dialog(f"🏥 Historial Sanitario: {animal_nombre}")
    def _dialog():
        from utils.data import get_animal_salud
        
        salud = get_animal_salud(animal_id)
        if salud.empty:
            st.info("No hay procedimientos registrados para este animal.")
            return

        salud = salud.copy()
        salud["fecha"] = pd.to_datetime(salud["fecha"], errors="coerce")
        salud["proxima_cita"] = pd.to_datetime(salud["proxima_cita"], errors="coerce")
        salud = salud.sort_values("fecha", ascending=False)

        st.dataframe(
            salud[["fecha", "tipo_procedimiento", "medicamento", "veterinario", "proxima_cita", "observaciones"]],
            column_config={
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "tipo_procedimiento": "Procedimiento",
                "medicamento": "Medicamento",
                "veterinario": "Veterinario",
                "proxima_cita": st.column_config.DateColumn("Próx. Cita", format="DD/MM/YYYY"),
                "observaciones": "Observaciones",
            },
            use_container_width=True,
            hide_index=True
        )

    _dialog()
