import streamlit as st
import pandas as pd
from utils.data import get_gastos, insert_record, update_record, delete_record, TABLE_NAMES, get_profiles, get_client
from components.filters import apply_filters_to_dataframe
from components.dialogs import gasto_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success, render_metric_card
from modules.auth import has_permission, is_admin
from config.constants import MENSAJES
from datetime import datetime, timedelta


@st.cache_data(ttl=300, show_spinner=False)
def get_admin_stats() -> dict:
    """Obtener estadísticas para el dashboard admin"""
    try:
        client = get_client()
        stats = {}

        # Total usuarios
        profiles = get_profiles()
        stats["total_usuarios"] = len(profiles)
        stats["usuarios_activos"] = len(profiles[profiles.get("activo", True) == True]) if not profiles.empty else 0
        stats["usuarios_admin"] = len(profiles[profiles.get("rol", "").isin(["admin", "gerencia"])]) if not profiles.empty else 0

        # Gastos del mes actual
        gastos = get_gastos()
        if not gastos.empty:
            gastos["fecha"] = pd.to_datetime(gastos["fecha"], errors="coerce")
            mes_actual = datetime.now().replace(day=1)
            gastos_mes = gastos[gastos["fecha"] >= mes_actual]
            stats["gastos_mes_actual"] = pd.to_numeric(gastos_mes["valor"], errors="coerce").sum()
            stats["gastos_total"] = pd.to_numeric(gastos["valor"], errors="coerce").sum()
        else:
            stats["gastos_mes_actual"] = 0
            stats["gastos_total"] = 0

        # Animales por predio
        from utils.data import get_animales
        animales = get_animales()
        if not animales.empty:
            stats["total_animales"] = len(animales)
            stats["animales_por_predio"] = animales.groupby("predio").size().to_dict()
        else:
            stats["total_animales"] = 0
            stats["animales_por_predio"] = {}

        # Ventas del mes
        from utils.data import get_ventas
        ventas = get_ventas()
        if not ventas.empty:
            ventas["fecha"] = pd.to_datetime(ventas["fecha"], errors="coerce")
            ventas_mes = ventas[ventas["fecha"] >= mes_actual]
            ventas_total = pd.to_numeric(ventas.get("valor_total", pd.Series(0, index=ventas.index)), errors="coerce").fillna(0)
            stats["ventas_mes"] = ventas_total.loc[ventas_mes.index].sum()
            stats["ventas_total"] = ventas_total.sum()
        else:
            stats["ventas_mes"] = 0
            stats["ventas_total"] = 0

        # Producción de huevos mes actual
        from utils.data import get_produccion
        prod = get_produccion()
        if not prod.empty:
            prod["fecha"] = pd.to_datetime(prod["fecha"], errors="coerce")
            prod_mes = prod[prod["fecha"] >= mes_actual]
            stats["huevos_mes"] = pd.to_numeric(prod_mes.get("cantidad_huevos", 0), errors="coerce").sum()
        else:
            stats["huevos_mes"] = 0

        return stats
    except Exception as e:
        st.error(f"Error cargando stats admin: {e}")
        return {}


def render_administracion() -> None:
    if not st.session_state.get("user"):
        return

    can_create = has_permission("administracion", "create")
    can_update = has_permission("administracion", "update")
    can_delete = has_permission("administracion", "delete")
    admin_access = is_admin()

    # Si es admin, mostrar dashboard administrativo completo
    if admin_access:
        render_admin_dashboard()
        st.divider()

    # Sección de gastos (para todos con permisos)
    render_page_header("Administración", "Control financiero y gastos operativos", "💸")

    render_toolbar(can_create)

    df = get_gastos()

    if df.empty:
        render_empty_state(
            "💸", "Sin gastos registrados",
            "No hay movimientos financieros en el sistema.",
            "➕ Registrar Gasto", lambda: gasto_dialog("create") if can_create else None
        )
        return

    render_gastos_table(df, can_update, can_delete)


def render_admin_dashboard() -> None:
    """Dashboard administrativo completo"""
    stats = get_admin_stats()

    render_page_header("Dashboard Administrativo", "Visión general del sistema y métricas clave", "🛠️")

    # KPIs principales
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        render_metric_card("Usuarios Totales", stats.get("total_usuarios", 0), icon="👥", color="primary")
    with c2:
        render_metric_card("Usuarios Activos", stats.get("usuarios_activos", 0), icon="✅", color="success")
    with c3:
        render_metric_card("Admins/Gerencia", stats.get("usuarios_admin", 0), icon="🛡️", color="warning")
    with c4:
        render_metric_card("Animales Totales", stats.get("total_animales", 0), icon="🐄", color="info")
    with c5:
        render_metric_card("Gastos Este Mes", f"${stats.get('gastos_mes_actual', 0):,.0f}", icon="💸", color="error")
    with c6:
        render_metric_card("Ventas Este Mes", f"${stats.get('ventas_mes', 0):,.0f}", icon="💰", color="success")

    st.write("")

    # Gráficos de resumen
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 📊 Animales por Predio")
        predio_data = stats.get("animales_por_predio", {})
        if predio_data:
            df_predio = pd.DataFrame(list(predio_data.items()), columns=["Predio", "Total"])
            st.bar_chart(df_predio.set_index("Predio"), use_container_width=True)
        else:
            st.info("Sin datos de animales")

    with c2:
        st.markdown("### 👥 Usuarios por Rol")
        profiles = get_profiles()
        if not profiles.empty and "rol" in profiles.columns:
            df_rol = profiles.groupby("rol").size().reset_index(name="Total")
            st.bar_chart(df_rol.set_index("rol"), use_container_width=True)
        else:
            st.info("Sin datos de usuarios")

    # Resumen financiero
    st.markdown("### 💰 Resumen Financiero")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Gastos Totales", f"${stats.get('gastos_total', 0):,.0f}", icon="📉", color="error")
    with c2:
        render_metric_card("Ventas Totales", f"${stats.get('ventas_total', 0):,.0f}", icon="📈", color="success")
    with c3:
        balance = stats.get('ventas_total', 0) - stats.get('gastos_total', 0)
        color = "success" if balance >= 0 else "error"
        render_metric_card("Balance", f"${balance:,.0f}", icon="⚖️", color=color)
    with c4:
        render_metric_card("Huevos Mes", f"{stats.get('huevos_mes', 0):,.0f}", icon="🥚", color="warning")


def render_toolbar(can_create: bool) -> None:
    c1, c2, c3 = st.columns([3, 1, 1])

    with c1:
        st.text_input("🔍 Buscar", placeholder="Filtrar por detalle, predio, inversor...", key="gastos_search")

    with c2:
        if can_create and st.button("➕ Nuevo Gasto", type="primary", use_container_width=True):
            gasto_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_gastos(), "gastos")


def render_gastos_table(df: pd.DataFrame, can_update: bool, can_delete: bool) -> None:
    df = df.copy()

    search = st.session_state.get("gastos_search", "").lower().strip()
    if search:
        mask = (
            df["detalle"].astype(str).str.lower().str.contains(search) |
            df.get("predio", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(search) |
            df.get("inversor", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(search) |
            df.get("metodo_pago", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
    if "valor" in df.columns:
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")

    display_cols = ["fecha", "detalle", "valor", "metodo_pago", "predio", "inversor", "observaciones"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "detalle": st.column_config.TextColumn("Detalle", width="medium"),
        "valor": st.column_config.TextColumn("Valor", width="medium"),
        "metodo_pago": st.column_config.TextColumn("Método", width="small"),
        "predio": st.column_config.TextColumn("Predio", width="small"),
        "inversor": st.column_config.TextColumn("Inversor", width="medium"),
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
        show_gasto_actions(row, can_update, can_delete)


def show_gasto_actions(row: pd.Series, can_update: bool, can_delete: bool) -> None:
    gasto_id = row.get("id")
    if not gasto_id:
        return

    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            if can_update and st.button("✏️ Editar", key=f"edit_gasto_{gasto_id}", use_container_width=True):
                gasto_dialog("update", row.to_dict())
        with c2:
            if can_delete and st.button("🗑️ Eliminar", key=f"del_gasto_{gasto_id}", use_container_width=True):
                from components.dialogs import render_confirm_dialog
                if render_confirm_dialog("Eliminar Gasto", f"¿Eliminar el gasto '{row.get('detalle', '')}'?", key=f"del_gasto_{gasto_id}"):
                    delete_record(TABLE_NAMES["gastos"], gasto_id)
                    render_toast_success(MENSAJES["eliminado_exitoso"])
                    st.rerun()
