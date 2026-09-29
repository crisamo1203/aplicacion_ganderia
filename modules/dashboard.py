import streamlit as st
import pandas as pd
from datetime import date
from utils.data import (
    get_dashboard_kpis,
    get_animales_por_propietario,
    get_animales_por_predio,
    get_produccion_huevos_30dias,
    get_actividad_reciente,
    check_alertas,
    get_reproductive_events,
    get_withdrawal_alerts
)
from components.ui import (
    render_page_header, render_section_header, render_metric_card,
    render_alert_banner, render_divider
)
from components.charts import (
    create_dashboard_animales_por_propietario,
    create_dashboard_animales_por_predio,
    create_dashboard_clase_distribucion,
    create_dashboard_produccion_huevos
)
from modules.auth import has_permission


def render_dashboard() -> None:
    if not st.session_state.get("user"):
        return

    render_page_header(
        "Gerencia Dashboard",
        "Resumen general de la operación ganadera y agrícola",
        "📊"
    )

    render_alerts_section()

    render_kpis_section()
    render_quick_actions()

    render_charts_section()
    render_zootecnicos_section()

    render_actividad_reciente()


def render_zootecnicos_section() -> None:
    """Muestra alertas zootécnicas basadas solo en eventos y fechas capturados."""
    render_divider()
    render_section_header("Calendario reproductivo y retiros sanitarios", "🧬", 20)

    reproductive = get_reproductive_events()
    withdrawals = get_withdrawal_alerts()
    if reproductive.attrs.get("load_error") or withdrawals.attrs.get("load_error"):
        st.info("Las alertas zootécnicas estarán disponibles después de aplicar la migración 006 y conceder acceso a los predios correspondientes.")
        return

    today = pd.Timestamp(date.today())
    horizon = today + pd.DateOffset(months=6)
    future = reproductive.copy()
    if not future.empty:
        future["expected_date"] = pd.to_datetime(future["expected_date"], errors="coerce")
        future["event_date"] = pd.to_datetime(future["event_date"], errors="coerce")
        future = future[
            (future["expected_date"].notna()) &
            (future["expected_date"] >= today) &
            (future["expected_date"] <= horizon)
        ].copy()

    due_calvings = future[future["event_type"] == "calving"] if not future.empty else future
    months = pd.date_range(today.to_period("M").to_timestamp(), periods=7, freq="MS")
    monthly = pd.Series(0, index=months, dtype="int64")
    if not due_calvings.empty:
        counts = due_calvings.groupby(due_calvings["expected_date"].dt.to_period("M")).size()
        for period, count in counts.items():
            month_start = period.to_timestamp()
            if month_start in monthly.index:
                monthly.loc[month_start] = int(count)
    chart = pd.DataFrame({"Partos probables registrados": monthly.values}, index=monthly.index)
    chart.index = chart.index.strftime("%b %Y")

    col_chart, col_alerts = st.columns([1.2, 1])
    with col_chart:
        st.caption("Proyección de partos según eventos reproductivos con fecha probable registrada. No sustituye el criterio veterinario.")
        st.bar_chart(chart, use_container_width=True, color="#2e7d32")
    with col_alerts:
        st.metric("Partos probables · próximos 6 meses", int(len(due_calvings)))
        near_due = due_calvings[
            due_calvings["expected_date"] <= today + pd.Timedelta(days=30)
        ] if not due_calvings.empty else due_calvings
        if not near_due.empty:
            st.warning(f"{len(near_due)} parto(s) probable(s) dentro de los próximos 30 días.")
        elif due_calvings.empty:
            st.caption("Sin fechas probables de parto registradas para este horizonte.")

    animal_names = {}
    try:
        from utils.data import get_animales
        animals = get_animales()
        if not animals.empty:
            animal_names = {
                str(row.get("id")): f"{row.get('arete', 'Sin arete')} · {row.get('nombre', '') or ''}".strip(" ·")
                for _, row in animals.iterrows()
            }
    except Exception:
        pass

    if not due_calvings.empty:
        display = due_calvings[["animal_id", "expected_date", "event_type"]].copy()
        display["Animal"] = display["animal_id"].astype(str).map(animal_names).fillna("Animal")
        display["Fecha probable"] = display["expected_date"].dt.strftime("%d/%m/%Y")
        display = display.sort_values("expected_date")
        st.dataframe(display[["Animal", "Fecha probable"]], hide_index=True, use_container_width=True)

    if withdrawals.empty:
        st.caption("No hay tratamientos con tiempos de retiro cargados.")
        return
    meat_dates = pd.to_datetime(withdrawals.get("meat_withdrawal_until"), errors="coerce")
    milk_dates = pd.to_datetime(withdrawals.get("milk_withdrawal_until"), errors="coerce")
    active_mask = (meat_dates.notna() & (meat_dates >= today)) | (milk_dates.notna() & (milk_dates >= today))
    active = withdrawals.loc[active_mask].copy()
    if active.empty:
        st.success("No hay tiempos de retiro de carne/leche vigentes en los datos visibles.")
        return
    active["animal_id"] = active["animal_id"].astype(str)
    active["Animal"] = active["animal_id"].map(animal_names).fillna("Animal")
    active["Retiro carne hasta"] = pd.to_datetime(active["meat_withdrawal_until"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")
    active["Retiro leche hasta"] = pd.to_datetime(active["milk_withdrawal_until"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("—")
    active["Medicamento"] = active["medicamento"].fillna("Sin especificar")
    st.warning(f"Hay {len(active)} tratamiento(s) con retiro sanitario vigente. Verifica antes de comercializar carne o leche.")
    st.dataframe(active[["Animal", "Medicamento", "Retiro carne hasta", "Retiro leche hasta"]], hide_index=True, use_container_width=True)


def render_quick_actions() -> None:
    """Accesos directos a formularios modales, visibles solo con permiso de creación."""
    actions = []
    if has_permission("inventario", "create"):
        actions.append(("➕ Registrar animal", "animal"))
    if has_permission("ventas", "create"):
        actions.append(("💰 Registrar venta", "venta"))
    if has_permission("administracion", "create"):
        actions.append(("💸 Registrar gasto", "gasto"))
    if not actions:
        return

    with st.container(key="dashboard-quick-actions"):
        columns = st.columns(len(actions))
        for column, (label, kind) in zip(columns, actions):
            with column:
                if st.button(label, key=f"dashboard_quick_{kind}", use_container_width=True,
                             type="primary" if kind == "animal" else "secondary"):
                    if kind == "animal":
                        from components.dialogs import animal_dialog
                        animal_dialog("create")
                    elif kind == "venta":
                        from components.dialogs import venta_dialog
                        venta_dialog("create")
                    else:
                        from components.dialogs import gasto_dialog
                        gasto_dialog("create")


def render_alerts_section() -> None:
    alertas = check_alertas()
    if alertas:
        with st.container():
            render_alert_banner(alertas)
            render_divider()


def render_kpis_section() -> None:
    kpis = get_dashboard_kpis()

    with st.container(key="dashboard-kpis"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Total Animales", f"{kpis['total_animales']:,}", icon="🐄", color="primary")
        with c2:
            render_metric_card("Bovinos", f"{kpis['bovinos']:,}", icon="🐂", color="success")
        with c3:
            render_metric_card("Avícolas", f"{kpis['avicolas']:,}", icon="🐔", color="warning")
        with c4:
            render_metric_card("Huevos Hoy", f"{kpis['huevos_hoy']:,}", icon="🥚", color="info")

    st.write("")


def render_charts_section() -> None:
    with st.container(key="dashboard-charts"):
        col_left, col_right = st.columns(2)

        with col_left:
            render_section_header("Animales por Propietario", "👤")
            df_prop = get_animales_por_propietario()
            fig = create_dashboard_animales_por_propietario(df_prop)
            st.plotly_chart(fig, use_container_width=True, key="chart_propietario")

        with col_right:
            render_section_header("Animales por Predio", "🏞️")
            df_predio = get_animales_por_predio()
            fig = create_dashboard_animales_por_predio(df_predio)
            st.plotly_chart(fig, use_container_width=True, key="chart_predio")

        col_left, col_right = st.columns(2)
        with col_left:
            kpis = get_dashboard_kpis()
            render_section_header("Distribución por Clase", "🐄")
            fig = create_dashboard_clase_distribucion(kpis["bovinos"], kpis["avicolas"])
            st.plotly_chart(fig, use_container_width=True, key="chart_clase")

        with col_right:
            render_section_header("Producción de Huevos (30 días)", "🥚")
            df_huevos = get_produccion_huevos_30dias()
            fig = create_dashboard_produccion_huevos(df_huevos)
            st.plotly_chart(fig, use_container_width=True, key="chart_huevos")


def render_actividad_reciente() -> None:
    render_divider()
    render_section_header("Actividad Reciente", "🕐", 20)

    actividad = get_actividad_reciente(20)

    if actividad.empty:
        st.info("No hay actividad reciente registrada.")
        return

    display_cols = []
    for col in ["fecha", "animal", "tipo", "subtipo", "detalle"]:
        if col in actividad.columns:
            display_cols.append(col)

    if not display_cols:
        st.info("No hay datos de actividad para mostrar.")
        return

    df_display = actividad[display_cols].copy()

    if "fecha" in df_display.columns:
        df_display["fecha"] = pd.to_datetime(df_display["fecha"], errors="coerce")
        df_display["fecha"] = df_display["fecha"].dt.strftime("%d/%m/%Y %H:%M")

    column_config = {
        "fecha": st.column_config.TextColumn("Fecha", width="medium"),
        "animal": st.column_config.TextColumn("Animal", width="medium"),
        "tipo": st.column_config.TextColumn("Tipo", width="small"),
        "subtipo": st.column_config.TextColumn("Subtipo", width="medium"),
        "detalle": st.column_config.TextColumn("Detalle", width="large"),
    }

    st.dataframe(
        df_display,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=300
    )
