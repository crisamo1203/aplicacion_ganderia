import streamlit as st
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from utils.data import get_predios, get_animales
from config.constants import PrediosFijos, PropietariosConocidos, ClaseAnimal


FILTER_KEY = "global_filters"


def init_global_filters() -> None:
    if FILTER_KEY not in st.session_state:
        st.session_state[FILTER_KEY] = {
            "predio": [],
            "fecha_inicio": None,
            "fecha_fin": None,
            "clase": [],
            "propietario": [],
        }


def get_global_filters() -> Dict[str, Any]:
    init_global_filters()
    return st.session_state[FILTER_KEY]


def set_global_filters(filters: Dict[str, Any]) -> None:
    init_global_filters()
    st.session_state[FILTER_KEY].update(filters)


def clear_global_filters() -> None:
    init_global_filters()
    st.session_state[FILTER_KEY] = {
        "predio": [],
        "fecha_inicio": None,
        "fecha_fin": None,
        "clase": [],
        "propietario": [],
    }


def has_active_filters() -> bool:
    filters = get_global_filters()
    return any(
        v for k, v in filters.items()
        if v not in ([], None, "")
    )


def render_global_filters_sidebar() -> None:
    init_global_filters()
    filters = get_global_filters()

    with st.sidebar:
        st.markdown("---")
        st.subheader("🔍 Filtros Globales")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpiar", use_container_width=True, help="Limpiar todos los filtros"):
                clear_global_filters()
                st.rerun()
        with col2:
            if st.button("💾 Guardar", use_container_width=True, help="Guardar como preferencia"):
                _save_filter_preference(filters)
                st.toast("Preferencias guardadas", icon="💾")

        st.markdown("#### 📅 Rango de Fechas")
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio = st.date_input(
                "Desde",
                value=filters.get("fecha_inicio"),
                max_value=date.today(),
                key="filter_fecha_inicio",
                format="DD/MM/YYYY"
            )
        with c2:
            fecha_fin = st.date_input(
                "Hasta",
                value=filters.get("fecha_fin") or date.today(),
                max_value=date.today(),
                key="filter_fecha_fin",
                format="DD/MM/YYYY"
            )

        if fecha_inicio != filters.get("fecha_inicio"):
            filters["fecha_inicio"] = fecha_inicio
        if fecha_fin != filters.get("fecha_fin"):
            filters["fecha_fin"] = fecha_fin

        st.markdown("#### 🏞️ Predios")
        predios_df = get_predios()
        predio_opciones = PrediosFijos.opciones()
        if not predios_df.empty and "nombre" in predios_df.columns:
            predio_opciones = sorted(set(predio_opciones + predios_df["nombre"].tolist()))

        predios_seleccionados = st.multiselect(
            "Seleccionar predios",
            options=predio_opciones,
            default=filters.get("predio", []),
            key="filter_predio",
            placeholder="Todos los predios"
        )
        filters["predio"] = predios_seleccionados

        st.markdown("#### 🐄 Clase Animal")
        clases_seleccionadas = st.multiselect(
            "Clase",
            options=ClaseAnimal.opciones(),
            default=filters.get("clase", []),
            key="filter_clase",
            placeholder="Todas las clases"
        )
        filters["clase"] = clases_seleccionadas

        st.markdown("#### 👤 Propietario")
        animales_df = get_animales()
        propietario_opciones = PropietariosConocidos.opciones()
        if not animales_df.empty and "propietario" in animales_df.columns:
            props_db = [p for p in animales_df["propietario"].dropna().unique() if p]
            propietario_opciones = sorted(set(propietario_opciones + props_db))

        propietarios_seleccionados = st.multiselect(
            "Seleccionar propietarios",
            options=propietario_opciones,
            default=filters.get("propietario", []),
            key="filter_propietario",
            placeholder="Todos los propietarios"
        )
        filters["propietario"] = propietarios_seleccionados

        active_count = sum(1 for v in filters.values() if v not in ([], None, ""))
        if active_count > 0:
            st.caption(f"🔍 {active_count} filtro{'s' if active_count > 1 else ''} activo{'s' if active_count > 1 else ''}")


def _save_filter_preference(filters: Dict[str, Any]) -> None:
    if "user" in st.session_state and st.session_state.user:
        try:
            from config.supabase_client import get_client
            client = get_client()
            user_id = str(st.session_state.user.id)
            client.table("profiles").update({
                "preferencias_filtros": filters
            }).eq("id", user_id).execute()
        except Exception:
            pass


def load_user_filter_preference() -> None:
    if "user" in st.session_state and st.session_state.user and "profile" in st.session_state:
        prefs = st.session_state.profile.get("preferencias_filtros")
        if prefs:
            set_global_filters(prefs)


def apply_filters_to_dataframe(df, table_name: str = "") -> Any:
    if df is None or (hasattr(df, "empty") and df.empty):
        return df

    filters = get_global_filters()
    filtered = df.copy()

    if filters.get("fecha_inicio"):
        date_cols = [c for c in filtered.columns if "fecha" in c.lower() or "date" in c.lower()]
        for col in date_cols:
            if col in filtered.columns:
                filtered[col] = pd.to_datetime(filtered[col], errors="coerce")
                filtered = filtered[filtered[col] >= pd.Timestamp(filters["fecha_inicio"])]

    if filters.get("fecha_fin"):
        date_cols = [c for c in filtered.columns if "fecha" in c.lower() or "date" in c.lower()]
        for col in date_cols:
            if col in filtered.columns:
                filtered[col] = pd.to_datetime(filtered[col], errors="coerce")
                filtered = filtered[filtered[col] <= pd.Timestamp(filters["fecha_fin"])]

    if filters.get("predio"):
        predio_col = None
        for col in ["predio", "predio_id", "predio_nombre", "predio_origen", "predio_destino"]:
            if col in filtered.columns:
                predio_col = col
                break
        if predio_col:
            filtered = filtered[filtered[predio_col].isin(filters["predio"])]

    if filters.get("clase") and "clase" in filtered.columns:
        filtered = filtered[filtered["clase"].isin(filters["clase"])]

    if filters.get("propietario") and "propietario" in filtered.columns:
        filtered = filtered[filtered["propietario"].isin(filters["propietario"])]

    return filtered


def get_filter_summary() -> str:
    filters = get_global_filters()
    parts = []
    if filters.get("fecha_inicio") or filters.get("fecha_fin"):
        ini = filters.get("fecha_inicio", "inicio")
        fin = filters.get("fecha_fin", "hoy")
        parts.append(f"📅 {ini} → {fin}")
    if filters.get("predio"):
        parts.append(f"🏞️ {', '.join(filters['predio'])}")
    if filters.get("clase"):
        parts.append(f"🐄 {', '.join(filters['clase'])}")
    if filters.get("propietario"):
        parts.append(f"👤 {', '.join(filters['propietario'])}")
    return " | ".join(parts) if parts else "Sin filtros"


import pandas as pd
