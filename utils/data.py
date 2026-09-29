import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from config.supabase_client import get_client, invalidate_cache
from config.constants import (
    TABLE_NAMES, CACHE_TTL_SECONDS, DEFAULT_PAGE_SIZE,
    ALERT_THRESHOLDS, ClaseAnimal, EstadoAnimal, ProcedimientoSalud
)
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def _user_scoped_cache(func):
    """Cache private Supabase results per authenticated user, never across RLS identities."""
    @st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
    def cached(user_scope, cache_identity, *args, **kwargs):
        return func(*args, **kwargs)

    @wraps(func)
    def wrapper(*args, **kwargs):
        user_scope = _get_user_id() or "anonymous"
        cache_identity = f"{func.__module__}.{func.__qualname__}"
        return cached(user_scope, cache_identity, *args, **kwargs)

    return wrapper


def _fetch_table_rows(client, table: str, columns: str = "*", limit: int = 5000,
                      order_by: Optional[str] = None, desc: bool = False,
                      filters: Optional[Dict[str, Any]] = None) -> list:
    """Fetch up to limit rows in API-sized pages, preserving RLS and a stable ordering."""
    rows = []
    page_size = 1000
    for start in range(0, limit, page_size):
        query = client.table(table).select(columns)
        for column, value in (filters or {}).items():
            query = query.eq(column, value)
        if order_by:
            query = query.order(order_by, desc=desc)
        end = min(start + page_size, limit) - 1
        response = query.range(start, end).execute()
        page = response.data or []
        rows.extend(page)
        if len(page) < (end - start + 1):
            break
    return rows


def _get_user_id() -> Optional[str]:
    if "user" in st.session_state and st.session_state.user:
        return str(st.session_state.user.id)
    return None


def _get_user_role() -> str:
    if "profile" in st.session_state and st.session_state.profile:
        return str(st.session_state.profile.get("rol", "colaborador")).lower()
    return "colaborador"


def _apply_global_filters(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df

    filters = st.session_state.get("global_filters", {})
    if not filters:
        return df

    filtered = df.copy()

    if "fecha_inicio" in filters and filters["fecha_inicio"]:
        date_cols = [c for c in filtered.columns if "fecha" in c.lower() or "date" in c.lower()]
        for col in date_cols:
            if col in filtered.columns:
                filtered[col] = pd.to_datetime(filtered[col], errors="coerce")
                filtered = filtered[filtered[col] >= pd.Timestamp(filters["fecha_inicio"])]

    if "fecha_fin" in filters and filters["fecha_fin"]:
        date_cols = [c for c in filtered.columns if "fecha" in c.lower() or "date" in c.lower()]
        for col in date_cols:
            if col in filtered.columns:
                filtered[col] = pd.to_datetime(filtered[col], errors="coerce")
                filtered = filtered[filtered[col] <= pd.Timestamp(filters["fecha_fin"])]

    if "predio" in filters and filters["predio"]:
        predio_col = None
        for col in ["predio", "predio_id", "predio_nombre"]:
            if col in filtered.columns:
                predio_col = col
                break
        if predio_col:
            filtered = filtered[filtered[predio_col].isin(filters["predio"])]

    if "clase" in filters and filters["clase"] and "clase" in filtered.columns:
        filtered = filtered[filtered["clase"].isin(filters["clase"])]

    if "propietario" in filters and filters["propietario"] and "propietario" in filtered.columns:
        filtered = filtered[filtered["propietario"].isin(filters["propietario"])]

    return filtered


@_user_scoped_cache
def get_animales(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["animales"], "*, lotes(nombre, predio_id, predios(nombre))",
                                 limit=limit, order_by="created_at")
        df = pd.DataFrame(rows)
        if not df.empty:
            df = _enrich_animales(df)
        return df
    except Exception as e:
        logger.exception("Error fetching animales from Supabase")
        return pd.DataFrame()


@_user_scoped_cache
def get_lotes() -> pd.DataFrame:
    """Lotes activos visibles para el usuario autenticado, con su predio asociado."""
    try:
        rows = _fetch_table_rows(
            get_client(), TABLE_NAMES["lotes"], "id,nombre,predio_id,predios(nombre)",
            limit=5000, order_by="id", filters={"activo": True}
        )
        normalized = []
        for row in rows:
            lot = dict(row)
            predio = lot.pop("predios", None)
            lot["predio"] = predio.get("nombre", "") if isinstance(predio, dict) else ""
            normalized.append(lot)
        return pd.DataFrame(normalized)
    except Exception:
        logger.exception("Error fetching lots from Supabase")
        return pd.DataFrame(columns=["id", "nombre", "predio_id", "predio"])


def _enrich_animales(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if "lotes" in df.columns:
        def lot_value(value, key):
            return value.get(key) if isinstance(value, dict) else None
        lotes = df["lotes"]
        if "lote_id" not in df.columns:
            df["lote_id"] = lotes.apply(lambda value: lot_value(value, "id"))
        if "lote" not in df.columns:
            df["lote"] = lotes.apply(lambda value: lot_value(value, "nombre"))
        def predio_name(value):
            predios = value.get("predios") if isinstance(value, dict) else None
            return predios.get("nombre") if isinstance(predios, dict) else None
        if "predio" not in df.columns:
            df["predio"] = lotes.apply(predio_name)
        else:
            df["predio"] = df["predio"].fillna(lotes.apply(predio_name))
        df = df.drop(columns=["lotes"])

    if "fecha_nacimiento" in df.columns:
        df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce")
        hoy = pd.Timestamp.now()
        edad_dias = (hoy - df["fecha_nacimiento"]).dt.days
        df["edad_meses"] = (edad_dias / 30).fillna(0).clip(lower=0).astype(int)
        df["edad_display"] = df["edad_meses"].apply(_format_edad)

    if "estado" not in df.columns:
        df["estado"] = EstadoAnimal.ACTIVO.value

    if "clase" not in df.columns:
        df["clase"] = ClaseAnimal.BOVINO.value

    # Ensure optional columns exist with defaults
    if "propietario" not in df.columns:
        df["propietario"] = "Sin propietario"
    if "predio" not in df.columns:
        df["predio"] = "Sin predio"
    if "raza" not in df.columns:
        df["raza"] = ""
    if "arete" not in df.columns:
        df["arete"] = ""
    if "nombre" not in df.columns:
        df["nombre"] = ""

    return df


def _format_edad(meses: int) -> str:
    if meses >= 24:
        return f"{meses // 12}a {meses % 12}m"
    return f"{meses}m"


@_user_scoped_cache
def get_ventas(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["ventas"], "*, predios(nombre)", limit=limit,
                                 order_by="fecha", desc=True)
        df = pd.DataFrame(rows)
        if not df.empty:
            if "predios" in df.columns:
                df["predio"] = df["predios"].apply(lambda value: value.get("nombre", "") if isinstance(value, dict) else "")
                df = df.drop(columns=["predios"])
            if "metodo_pago" not in df.columns and "metodo" in df.columns:
                df["metodo_pago"] = df["metodo"]
            if "valor_total" not in df.columns and {"cantidad", "valor_unitario"}.issubset(df.columns):
                cantidad = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
                unitario = pd.to_numeric(df["valor_unitario"], errors="coerce").fillna(0)
                df["valor_total"] = cantidad * unitario
        return df
    except Exception as e:
        logger.error(f"Error fetching ventas: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_produccion(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["produccion"], "*", limit=limit,
                                 order_by="fecha", desc=True)
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Error fetching produccion: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_pesajes(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["pesajes"], "*", limit=limit,
                                 order_by="fecha", desc=True)
        df = pd.DataFrame(rows)
        if not df.empty and "animal_id" in df.columns:
            animales = get_animales()
            if not animales.empty:
                df = df.merge(animales[["id", "arete", "nombre", "propietario", "predio"]],
                              left_on="animal_id", right_on="id", how="left", suffixes=("", "_animal"))
        return df
    except Exception as e:
        logger.error(f"Error fetching pesajes: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_movimientos(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["movimientos"], "*", limit=limit,
                                 order_by="fecha", desc=True)
        df = pd.DataFrame(rows)
        if not df.empty:
            if "animal_id" in df.columns:
                animales = get_animales()
                if not animales.empty:
                    df = df.merge(animales[["id", "arete", "nombre"]],
                                  left_on="animal_id", right_on="id", how="left", suffixes=("", "_animal"))
        return df
    except Exception as e:
        logger.error(f"Error fetching movimientos: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_gastos(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["gastos"], "*, predios(nombre)", limit=limit,
                                 order_by="fecha", desc=True)
        df = pd.DataFrame(rows)
        if not df.empty and "predios" in df.columns:
            df["predio"] = df["predios"].apply(lambda value: value.get("nombre", "") if isinstance(value, dict) else "")
            df = df.drop(columns=["predios"])
        if not df.empty and "metodo_pago" not in df.columns and "metodo" in df.columns:
            df["metodo_pago"] = df["metodo"]
        return df
    except Exception as e:
        logger.error(f"Error fetching gastos: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_salud(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["salud"], "*", limit=limit,
                                 order_by="fecha", desc=True)
        df = pd.DataFrame(rows)
        if not df.empty:
            if "animal_id" in df.columns:
                animales = get_animales()
                if not animales.empty:
                    df = df.merge(animales[["id", "arete", "nombre", "propietario", "predio"]],
                                  left_on="animal_id", right_on="id", how="left", suffixes=("", "_animal"))
            if "proxima_cita" in df.columns:
                df["proxima_cita"] = pd.to_datetime(df["proxima_cita"], errors="coerce")
                df["cita_vencida"] = df["proxima_cita"] < pd.Timestamp.now()
        return df
    except Exception as e:
        logger.error(f"Error fetching salud: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_profiles(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["profiles"], "*", limit=limit,
                                 order_by="created_at", desc=True)
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Error fetching profiles: {e}")
        return pd.DataFrame()


@_user_scoped_cache
def get_predios() -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["predios"], "*", limit=5000,
                                 order_by="created_at", desc=True)
        return pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Error fetching predios: {e}")
        return pd.DataFrame()


def insert_record(table: str, data: Dict[str, Any]) -> bool:
    try:
        client = get_client()
        client.table(table).insert(data).execute()
        invalidate_cache()
        return True
    except Exception as e:
        logger.error(f"Error inserting into {table}: {e}")
        st.error(f"Error al guardar: {e}")
        return False


def update_record(table: str, record_id: str, data: Dict[str, Any]) -> bool:
    try:
        client = get_client()
        client.table(table).update(data).eq("id", record_id).execute()
        invalidate_cache()
        return True
    except Exception as e:
        logger.error(f"Error updating {table}: {e}")
        st.error(f"Error al actualizar: {e}")
        return False


def delete_record(table: str, record_id: str) -> bool:
    try:
        client = get_client()
        client.table(table).delete().eq("id", record_id).execute()
        invalidate_cache()
        return True
    except Exception as e:
        logger.error(f"Error deleting from {table}: {e}")
        st.error(f"Error al eliminar: {e}")
        return False


def get_animal_by_id(animal_id: str) -> Optional[Dict]:
    try:
        client = get_client()
        resp = client.table(TABLE_NAMES["animales"]).select("*").eq("id", animal_id).maybe_single().execute()
        return resp.data
    except Exception:
        return None


def get_animal_pesajes(animal_id: str) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["pesajes"], "*", limit=5000,
                                 order_by="fecha", desc=True, filters={"animal_id": animal_id})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def get_animal_salud(animal_id: str) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["salud"], "*", limit=5000,
                                 order_by="fecha", desc=True, filters={"animal_id": animal_id})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def get_animal_movimientos(animal_id: str) -> pd.DataFrame:
    try:
        client = get_client()
        rows = _fetch_table_rows(client, TABLE_NAMES["movimientos"], "*", limit=5000,
                                 order_by="fecha", desc=True, filters={"animal_id": animal_id})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def get_dashboard_kpis() -> Dict[str, Any]:
    animales = get_animales()
    produccion = get_produccion()

    total_animales = len(animales)
    bovinos = len(animales[animales.get("clase", "") == ClaseAnimal.BOVINO.value]) if not animales.empty else 0
    avicolas = len(animales[animales.get("clase", "") == ClaseAnimal.AVICOLA.value]) if not animales.empty else 0

    huevos_hoy = 0
    if not produccion.empty and "fecha" in produccion.columns and "cantidad_huevos" in produccion.columns:
        produccion["fecha"] = pd.to_datetime(produccion["fecha"], errors="coerce")
        hoy = pd.Timestamp.now().date()
        huevos_hoy = pd.to_numeric(
            produccion[produccion["fecha"].dt.date == hoy]["cantidad_huevos"],
            errors="coerce"
        ).fillna(0).sum()

    return {
        "total_animales": total_animales,
        "bovinos": bovinos,
        "avicolas": avicolas,
        "huevos_hoy": int(huevos_hoy),
    }


def get_animales_por_propietario() -> pd.DataFrame:
    animales = get_animales()
    if animales.empty or "propietario" not in animales.columns:
        return pd.DataFrame(columns=["propietario", "total"])

    df = animales.groupby("propietario").size().reset_index(name="total")
    df = df.sort_values("total", ascending=False)
    return df


def get_animales_por_predio() -> pd.DataFrame:
    animales = get_animales()
    if animales.empty or "predio" not in animales.columns:
        return pd.DataFrame(columns=["predio", "total"])

    df = animales.groupby("predio").size().reset_index(name="total")
    predios_orden = [p.value for p in __import__("config.constants", fromlist=["PrediosFijos"]).PrediosFijos]
    df["orden"] = df["predio"].apply(lambda x: predios_orden.index(x) if x in predios_orden else 999)
    df = df.sort_values("orden").drop("orden", axis=1)
    return df


def get_produccion_huevos_30dias() -> pd.DataFrame:
    produccion = get_produccion()
    if produccion.empty or "fecha" not in produccion.columns or "cantidad_huevos" not in produccion.columns:
        return pd.DataFrame(columns=["fecha", "cantidad_huevos"])

    df = produccion.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["cantidad_huevos"] = pd.to_numeric(df["cantidad_huevos"], errors="coerce").fillna(0)

    hace_30 = pd.Timestamp.now() - timedelta(days=30)
    df = df[df["fecha"] >= hace_30]

    df = df.groupby("fecha")["cantidad_huevos"].sum().reset_index()
    df = df.sort_values("fecha")
    return df


def get_actividad_reciente(limit: int = 20) -> pd.DataFrame:
    movimientos = get_movimientos(limit)
    salud = get_salud(limit)

    cols_mov = ["fecha", "animal", "tipo_movimiento", "comentarios"]
    cols_salud = ["fecha", "animal", "tipo_procedimiento", "observaciones"]
    if "tipo_movimiento" not in movimientos.columns and "tipo" in movimientos.columns:
        movimientos["tipo_movimiento"] = movimientos["tipo"]
    if "tipo_procedimiento" not in salud.columns and "tipo" in salud.columns:
        salud["tipo_procedimiento"] = salud["tipo"]
    for df in (movimientos, salud):
        if "animal" not in df.columns and "nombre" in df.columns:
            aretes = df.get("arete", pd.Series("", index=df.index)).fillna("").astype(str)
            nombres = df["nombre"].fillna("").astype(str)
            df["animal"] = (nombres + " " + aretes).str.strip().replace("", "—")

    for c in cols_mov:
        if c not in movimientos.columns:
            movimientos[c] = None
    for c in cols_salud:
        if c not in salud.columns:
            salud[c] = None

    if not movimientos.empty:
        movimientos = movimientos[cols_mov].copy()
        movimientos["tipo"] = "Movimiento"
        movimientos = movimientos.rename(columns={"tipo_movimiento": "subtipo", "comentarios": "detalle"})

    if not salud.empty:
        salud = salud[cols_salud].copy()
        salud["tipo"] = "Salud"
        salud = salud.rename(columns={"tipo_procedimiento": "subtipo", "observaciones": "detalle"})

    combinado = pd.concat([movimientos, salud], ignore_index=True)
    if not combinado.empty:
        combinado["fecha"] = pd.to_datetime(combinado["fecha"], errors="coerce")
        combinado = combinado.sort_values("fecha", ascending=False).head(limit)

    return combinado


def check_alertas() -> List[Dict[str, Any]]:
    alertas = []
    animales = get_animales()
    salud = get_salud()
    pesajes = get_pesajes()
    produccion = get_produccion()
    gastos = get_gastos()

    if not animales.empty:
        for _, animal in animales.iterrows():
            animal_id = animal.get("id")
            arete = animal.get("arete", "N/A")
            nombre = animal.get("nombre", "N/A")
            clase = animal.get("clase", "")
            propietario = animal.get("propietario", "")

            animal_pesajes = pesajes[pesajes.get("animal_id") == animal_id] if not pesajes.empty else pd.DataFrame()
            if not animal_pesajes.empty:
                ultima_fecha = pd.to_datetime(animal_pesajes["fecha"]).max()
                dias_sin_pesar = (pd.Timestamp.now() - ultima_fecha).days
                if dias_sin_pesar > ALERT_THRESHOLDS["pesaje_vencido_dias"]:
                    alertas.append({
                        "tipo": "pesaje_vencido",
                        "severidad": "critica" if dias_sin_pesar > ALERT_THRESHOLDS["pesaje_vencido_dias"] * 2 else "advertencia",
                        "animal_id": animal_id,
                        "arete": arete,
                        "nombre": nombre,
                        "propietario": propietario,
                        "mensaje": f"{nombre} ({arete}) sin pesaje hace {dias_sin_pesar} días",
                        "accion": "ceba",
                        "dias": dias_sin_pesar,
                    })

            if clase == ClaseAnimal.AVICOLA.value:
                animal_prod = produccion[produccion.get("animal_id") == animal_id] if not produccion.empty else pd.DataFrame()
                if not animal_prod.empty:
                    animal_prod["fecha"] = pd.to_datetime(animal_prod["fecha"], errors="coerce")
                    ultima = animal_prod["fecha"].max()
                    if pd.notna(ultima):
                        dias = (pd.Timestamp.now() - ultima).days
                        if dias > ALERT_THRESHOLDS["produccion_avicola_dias"]:
                            alertas.append({
                                "tipo": "produccion_pendiente",
                                "severidad": "advertencia",
                                "animal_id": animal_id,
                                "arete": arete,
                                "nombre": nombre,
                                "propietario": propietario,
                                "mensaje": f"{nombre} ({arete}) sin producción de huevos hace {dias} días",
                                "accion": "produccion",
                                "dias": dias,
                            })

    if not salud.empty:
        hoy = pd.Timestamp.now()
        vencidas = salud[salud.get("cita_vencida", False) == True]
        for _, cita in vencidas.iterrows():
            animal_id = cita.get("animal_id")
            animal_info = animales[animales["id"] == animal_id] if not animales.empty else pd.DataFrame()
            arete = animal_info.iloc[0].get("arete", "N/A") if not animal_info.empty else "N/A"
            nombre = animal_info.iloc[0].get("nombre", "N/A") if not animal_info.empty else "N/A"
            propietario = animal_info.iloc[0].get("propietario", "") if not animal_info.empty else ""
            dias_vencida = (hoy - pd.to_datetime(cita["proxima_cita"])).days

            alertas.append({
                "tipo": "vacuna_vencida",
                "severidad": "critica" if dias_vencida > ALERT_THRESHOLDS["alerta_critica_dias"] else "advertencia",
                "animal_id": animal_id,
                "arete": arete,
                "nombre": nombre,
                "propietario": propietario,
                "mensaje": f"{nombre} ({arete}): {cita.get('tipo_procedimiento', 'Procedimiento')} vencida hace {dias_vencida} días",
                "accion": "salud",
                "dias": dias_vencida,
            })

    if not gastos.empty:
        sin_comprobante = gastos[
            (pd.to_numeric(gastos.get("valor", 0), errors="coerce") > ALERT_THRESHOLDS["gasto_sin_comprobante_valor"]) &
            (gastos.get("observaciones", "").isna() | (gastos.get("observaciones", "") == ""))
        ]
        for _, gasto in sin_comprobante.iterrows():
            alertas.append({
                "tipo": "gasto_sin_comprobante",
                "severidad": "info",
                "animal_id": None,
                "arete": None,
                "nombre": gasto.get("detalle", "Gasto"),
                "propietario": gasto.get("predio", ""),
                "mensaje": f"Gasto '{gasto.get('detalle', '')}' de ${gasto.get('valor', 0):,.0f} sin observaciones",
                "accion": "administracion",
                "dias": 0,
            })

    return alertas

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_reproductive_events(limit: int = 5000) -> pd.DataFrame:
    try:
        client = get_client()
        resp = client.table("reproductive_events").select("*").order("event_date", desc=True).limit(limit).execute()
        df = pd.DataFrame(resp.data or [])
        if not df.empty:
            # Add attr to track load errors
            df.attrs["load_error"] = False
        return df
    except Exception as e:
        logger.error(f"Error fetching reproductive_events: {e}")
        df = pd.DataFrame()
        df.attrs["load_error"] = True
        return df


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_withdrawal_alerts(limit: int = 5000) -> pd.DataFrame:
    """Get upcoming withdrawal alerts from salud table"""
    try:
        client = get_client()
        resp = client.table("salud").select("*").neq("withdrawal_days_meat", 0).neq("withdrawal_days_milk", 0).execute()
        df = pd.DataFrame(resp.data or [])
        if not df.empty:
            df["meat_withdrawal_until"] = pd.to_datetime(df["meat_withdrawal_until"], errors="coerce")
            df["milk_withdrawal_until"] = pd.to_datetime(df["milk_withdrawal_until"], errors="coerce")
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            # Only show future withdrawals
            today = pd.Timestamp.now()
            df = df[
                (df["meat_withdrawal_until"].notna() & (df["meat_withdrawal_until"] >= pd.Timestamp.now())) |
                (df["milk_withdrawal_until"].notna() & (df["milk_withdrawal_until"] >= pd.Timestamp.now()))
            ]
        return df
    except Exception as e:
        logger.error(f"Error fetching withdrawal alerts: {e}")
        df = pd.DataFrame()
        df.attrs["load_error"] = True
        return df
