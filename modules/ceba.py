import streamlit as st
import pandas as pd
from utils.data import get_pesajes, insert_record, update_record, delete_record, TABLE_NAMES, get_animal_pesajes
from components.filters import apply_filters_to_dataframe
from components.dialogs import pesaje_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success
from modules.auth import has_permission
from config.constants import MENSAJES
from components.charts import create_pesaje_evolucion


def render_ceba() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("ceba", "create")
    can_update = has_permission("ceba", "update")
    can_delete = has_permission("ceba", "delete")

    render_page_header("Ceba", "Seguimiento de engorde y control de peso", "⚖️")

    render_toolbar(can_create)

    df = get_pesajes()

    if df.empty:
        render_empty_state(
            "⚖️", "Sin registros de pesaje",
            "No hay controles de peso registrados.",
            "➕ Registrar Pesaje", lambda: pesaje_dialog("create") if can_create else None
        )
        return

    render_ceba_table(df, can_update, can_delete)


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por animal, arete...", key="ceba_search")

    with c2:
        if can_create and st.button("➕ Nuevo Pesaje", type="primary", use_container_width=True):
            pesaje_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_pesajes(), "pesajes")


def render_ceba_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("ceba_search", "").lower().strip()
    if search:
        mask = (
            df["arete"].astype(str).str.lower().str.contains(search) |
            df["nombre"].astype(str).str.lower().str.contains(search) |
            df["propietario"].astype(str).str.lower().str.contains(search) |
            df["predio"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")

    if "diferencia_peso" not in df.columns and "peso_kg" in df.columns:
        df = df.sort_values(["animal_id", "fecha"])
        df["diferencia_peso"] = df.groupby("animal_id")["peso_kg"].diff()

    display_cols = ["fecha", "arete", "nombre", "propietario", "predio", "peso_kg", "diferencia_peso", "nota"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "arete": st.column_config.TextColumn("Arete", width="small"),
        "nombre": st.column_config.TextColumn("Animal", width="medium"),
        "propietario": st.column_config.TextColumn("Propietario", width="medium"),
        "predio": st.column_config.TextColumn("Predio", width="small"),
        "peso_kg": st.column_config.NumberColumn("Peso (kg)", format="%.1f", width="small"),
        "diferencia_peso": st.column_config.NumberColumn("Dif. (kg)", format="%.1f", width="small"),
        "nota": st.column_config.TextColumn("Nota", width="large"),
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
        show_ceba_actions(row, can_update, can_delete)


def show_ceba_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    pesaje_id = row.get("id")
    animal_id = row.get("animal_id")
    if not pesaje_id:
        return

    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📈 Ver Historial", key=f"hist_pes_{pesaje_id}", use_container_width=True):
                if animal_id:
                    _render_pesajes_history(animal_id, f"{row.get('nombre', '')} ({row.get('arete', '')})")
        with c2:
            if can_update and st.button("✏️ Editar", key=f"edit_pes_{pesaje_id}", use_container_width=True):
                pesaje_dialog("update", row.to_dict())
        with c3:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_pes_{pesaje_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Pesaje", f"¿Eliminar el pesaje de {row.get('peso_kg', 0)} kg?", key=f"del_pes_{pesaje_id}"):
                    delete_record(TABLE_NAMES["pesajes"], pesaje_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()


def _render_pesajes_history(animal_id: str, animal_nombre: str) -> None:
    """Renderiza el historial de pesajes dentro de un diálogo."""
    @st.dialog(f"⚖️ Historial de Pesajes: {animal_nombre}")
    def _dialog():
        from utils.data import get_animal_pesajes
        from components.charts import create_pesaje_evolucion
        
        pesajes = get_animal_pesajes(animal_id)
        if pesajes.empty:
            st.info("No hay pesajes registrados para este animal.")
            return

        pesajes = pesajes.copy()
        pesajes["fecha"] = pd.to_datetime(pesajes["fecha"], errors="coerce")
        pesajes = pesajes.sort_values("fecha", ascending=False)

        st.dataframe(
            pesajes[["fecha", "peso_kg", "nota"]],
            column_config={
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "peso_kg": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
                "nota": "Nota",
            },
            use_container_width=True,
            hide_index=True
        )

        if len(pesajes) > 1:
            st.markdown("**Evolución:**")
            fig = create_pesaje_evolucion(pesajes, animal_id)
            st.plotly_chart(fig, use_container_width=True, key=f"pesaje_evolucion_{animal_id}")

    _dialog()
