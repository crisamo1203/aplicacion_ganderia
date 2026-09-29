import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data import insert_record, update_record, TABLE_NAMES, get_client
from components.ui import (
    render_page_header, render_empty_state, render_toast_success,
    render_toast_error, render_toast_info
)
from modules.auth import is_admin, get_current_user_id
from config.constants import MENSAJES


FEEDBACK_TIPOS = {
    "problema": ("🐛", "Problema / Bug", "mf-badge-error"),
    "sugerencia": ("💡", "Sugerencia", "mf-badge-warning"),
    "mejora": ("✨", "Mejora", "mf-badge-info"),
    "otro": ("📝", "Otro", "mf-badge-gray"),
}

FEEDBACK_ESTADOS = {
    "nuevo": ("🆕", "Nuevo", "mf-feedback-status-new"),
    "en_revision": ("👀", "En Revisión", "mf-feedback-status-review"),
    "resuelto": ("✅", "Resuelto", "mf-feedback-status-resolved"),
    "cerrado": ("🔒", "Cerrado", "mf-feedback-status-closed"),
}

FEEDBACK_PRIORIDADES = {
    "baja": ("🔵", "Baja"),
    "media": ("🟡", "Media"),
    "alta": ("🟠", "Alta"),
    "critica": ("🔴", "Crítica"),
}


@st.cache_data(ttl=300, show_spinner=False)
def get_feedback(limit: int = 500) -> pd.DataFrame:
    try:
        client = get_client()
        resp = client.table(TABLE_NAMES.get("feedback", "feedback")).select("*").order("created_at", desc=True).limit(limit).execute()
        return pd.DataFrame(resp.data or [])
    except Exception as e:
        st.error(f"Error cargando feedback: {e}")
        return pd.DataFrame()


def render_feedback_user() -> None:
    """Vista para usuarios: enviar feedback"""
    if not st.session_state.get("user"):
        return

    render_page_header("Feedback", "Reporta problemas, sugerencias o mejoras", "📬")

    # Formulario de nuevo feedback
    st.markdown('<div class="mf-feedback-form">', unsafe_allow_html=True)
    st.markdown("### ✍️ Nuevo Reporte")

    with st.form("nuevo_feedback", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            tipo = st.selectbox(
                "Tipo *",
                options=list(FEEDBACK_TIPOS.keys()),
                format_func=lambda x: f"{FEEDBACK_TIPOS[x][0]} {FEEDBACK_TIPOS[x][1]}"
            )
            modulo = st.selectbox(
                "Módulo (opcional)",
                options=["", "dashboard", "inventario", "ventas", "produccion", "ceba", "historial", "administracion", "salud", "usuarios"],
                format_func=lambda x: "— Seleccionar —" if x == "" else x.title()
            )
        with c2:
            prioridad = st.selectbox(
                "Prioridad *",
                options=list(FEEDBACK_PRIORIDADES.keys()),
                index=1,
                format_func=lambda x: f"{FEEDBACK_PRIORIDADES[x][0]} {FEEDBACK_PRIORIDADES[x][1]}"
            )

        titulo = st.text_input("Título *", placeholder="Resumen breve del problema o sugerencia", max_chars=200)
        descripcion = st.text_area(
            "Descripción *",
            placeholder="Describe con detalle el problema, pasos para reproducirlo, o tu idea de mejora...",
            height=150
        )

        enviado = st.form_submit_button("📤 Enviar Feedback", type="primary", use_container_width=True)

        if enviado:
            if not titulo.strip() or not descripcion.strip():
                render_toast_error("Título y descripción son obligatorios")
            else:
                data = {
                    "user_id": get_current_user_id(),
                    "tipo": tipo,
                    "titulo": titulo.strip(),
                    "descripcion": descripcion.strip(),
                    "modulo": modulo if modulo else None,
                    "prioridad": prioridad,
                    "estado": "nuevo"
                }
                if insert_record(TABLE_NAMES.get("feedback", "feedback"), data):
                    render_toast_success("¡Feedback enviado! El equipo lo revisará pronto.")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Historial del usuario
    st.divider()
    st.markdown("### 📋 Mis Reportes")

    df = get_feedback()
    if df.empty:
        render_empty_state("📭", "Sin reportes", "No has enviado ningún feedback aún.")
        return

    user_feedback = df[df["user_id"] == get_current_user_id()].copy()

    if user_feedback.empty:
        render_empty_state("📭", "Sin reportes", "No has enviado ningún feedback aún.")
        return

    for _, row in user_feedback.iterrows():
        render_feedback_card(row, is_admin_view=False)


def render_feedback_admin() -> None:
    """Vista para admins: gestionar todo el feedback"""
    if not st.session_state.get("user") or not is_admin():
        st.error(MENSAJES["sin_permisos"])
        return

    render_page_header("Gestión de Feedback", "Revisa y gestiona reportes de usuarios", "🛠️")

    df = get_feedback(1000)

    if df.empty:
        render_empty_state("📭", "Sin feedback", "No hay reportes en el sistema.")
        return

    # Filtros
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        filtro_tipo = st.multiselect("Tipo", options=list(FEEDBACK_TIPOS.keys()), format_func=lambda x: FEEDBACK_TIPOS[x][1])
    with c2:
        filtro_estado = st.multiselect("Estado", options=list(FEEDBACK_ESTADOS.keys()), format_func=lambda x: FEEDBACK_ESTADOS[x][1])
    with c3:
        filtro_prioridad = st.multiselect("Prioridad", options=list(FEEDBACK_PRIORIDADES.keys()), format_func=lambda x: FEEDBACK_PRIORIDADES[x][1])
    with c4:
        search = st.text_input("🔍 Buscar", placeholder="Título, descripción, usuario...")

    # Aplicar filtros
    filtered = df.copy()
    if filtro_tipo:
        filtered = filtered[filtered["tipo"].isin(filtro_tipo)]
    if filtro_estado:
        filtered = filtered[filtered["estado"].isin(filtro_estado)]
    if filtro_prioridad:
        filtered = filtered[filtered["prioridad"].isin(filtro_prioridad)]
    if search:
        search = search.lower().strip()
        mask = (
            filtered["titulo"].astype(str).str.lower().str.contains(search) |
            filtered["descripcion"].astype(str).str.lower().str.contains(search)
        )
        filtered = filtered[mask]

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total", len(filtered))
    with c2:
        st.metric("Nuevos", len(filtered[filtered["estado"] == "nuevo"]))
    with c3:
        st.metric("En Revisión", len(filtered[filtered["estado"] == "en_revision"]))
    with c4:
        st.metric("Resueltos", len(filtered[filtered["estado"] == "resuelto"]))

    st.divider()

    # Lista de feedback
    for _, row in filtered.iterrows():
        render_feedback_admin_card(row)


def render_feedback_card(row: pd.Series, is_admin_view: bool = False) -> None:
    """Renderiza una tarjeta de feedback para el usuario"""
    tipo_icon, tipo_label, tipo_badge = FEEDBACK_TIPOS.get(row["tipo"], ("📝", row["tipo"], "mf-badge-gray"))
    estado_icon, estado_label, estado_badge = FEEDBACK_ESTADOS.get(row["estado"], ("❓", row["estado"], "mf-feedback-status-new"))
    prioridad_icon, prioridad_label = FEEDBACK_PRIORIDADES.get(row["prioridad"], ("⚪", row["prioridad"]))

    created = pd.to_datetime(row["created_at"]).strftime("%d/%m/%Y %H:%M")

    st.markdown(f"""
    <div class="mf-feedback-item">
        <div class="mf-feedback-header">
            <span class="mf-feedback-type {tipo_badge}">{tipo_icon} {tipo_label}</span>
            <div class="mf-feedback-meta">
                <span>{prioridad_icon} {prioridad_label}</span>
                <span>{estado_icon} <span class="{estado_badge}">{estado_label}</span></span>
                <span>📅 {created}</span>
                {f'<span>📍 {row["modulo"]}</span>' if row.get("modulo") else ''}
            </div>
        </div>
        <div class="mf-feedback-content"><strong>{row["titulo"]}</strong></div>
        <div class="mf-feedback-content" style="font-weight: 400; color: var(--text-secondary);">{row["descripcion"]}</div>
    </div>
    """, unsafe_allow_html=True)

    if row.get("respuesta_admin") and row["estado"] in ["resuelto", "cerrado"]:
        responded = pd.to_datetime(row["responded_at"]).strftime("%d/%m/%Y %H:%M") if row.get("responded_at") else ""
        st.markdown(f"""
        <div style="background: var(--primary-bg); border-left: 3px solid var(--primary); padding: 1rem; border-radius: var(--radius); margin-top: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">💬 Respuesta del admin ({responded})</div>
            <div>{row["respuesta_admin"]}</div>
        </div>
        """, unsafe_allow_html=True)


def render_feedback_admin_card(row: pd.Series) -> None:
    """Renderiza una tarjeta de feedback para admin con acciones"""
    tipo_icon, tipo_label, tipo_badge = FEEDBACK_TIPOS.get(row["tipo"], ("📝", row["tipo"], "mf-badge-gray"))
    estado_icon, estado_label, estado_badge = FEEDBACK_ESTADOS.get(row["estado"], ("❓", row["estado"], "mf-feedback-status-new"))
    prioridad_icon, prioridad_label = FEEDBACK_PRIORIDADES.get(row["prioridad"], ("⚪", row["prioridad"]))

    created = pd.to_datetime(row["created_at"]).strftime("%d/%m/%Y %H:%M")

    # Obtener info del usuario
    from utils.data import get_profiles
    profiles = get_profiles()
    user_info = profiles[profiles["id"] == row["user_id"]] if not profiles.empty else pd.DataFrame()
    user_name = user_info.iloc[0]["nombre"] if not user_info.empty else "Usuario"
    user_email = user_info.iloc[0]["email"] if not user_info.empty else ""

    st.markdown(f"""
    <div class="mf-feedback-item">
        <div class="mf-feedback-header">
            <span class="mf-feedback-type {tipo_badge}">{tipo_icon} {tipo_label}</span>
            <div class="mf-feedback-meta">
                <span>{prioridad_icon} {prioridad_label}</span>
                <span>{estado_icon} <span class="{estado_badge}">{estado_label}</span></span>
                <span>👤 {user_name} ({user_email})</span>
                <span>📅 {created}</span>
                {f'<span>📍 {row["modulo"]}</span>' if row.get("modulo") else ''}
            </div>
        </div>
        <div class="mf-feedback-content"><strong>{row["titulo"]}</strong></div>
        <div class="mf-feedback-content" style="font-weight: 400; color: var(--text-secondary);">{row["descripcion"]}</div>
    </div>
    """, unsafe_allow_html=True)

    # Acciones admin
    if row["estado"] in ["nuevo", "en_revision"]:
        c1, c2, c3 = st.columns([1, 1, 4])
        with c1:
            if st.button("👀 Revisar", key=f"review_{row['id']}", use_container_width=True):
                update_feedback_status(row["id"], "en_revision")
        with c2:
            if st.button("✅ Resolver", key=f"resolve_{row['id']}", use_container_width=True):
                show_resolve_dialog(row["id"])
        with c3:
            pass
    elif row["estado"] == "resuelto":
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("🔒 Cerrar", key=f"close_{row['id']}", use_container_width=True):
                update_feedback_status(row["id"], "cerrado")
    else:
        st.caption("✅ Resuelto y cerrado")

    # Mostrar respuesta si existe
    if row.get("respuesta_admin"):
        responded = pd.to_datetime(row["responded_at"]).strftime("%d/%m/%Y %H:%M") if row.get("responded_at") else ""
        st.markdown(f"""
        <div style="background: var(--primary-bg); border-left: 3px solid var(--primary); padding: 1rem; border-radius: var(--radius); margin-top: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">💬 Tu respuesta ({responded})</div>
            <div>{row["respuesta_admin"]}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()


def update_feedback_status(feedback_id: str, nuevo_estado: str) -> None:
    try:
        from config.supabase_client import get_client
        client = get_client()
        client.table(TABLE_NAMES.get("feedback", "feedback")).update({
            "estado": nuevo_estado
        }).eq("id", feedback_id).execute()
        render_toast_success(f"Estado actualizado a {nuevo_estado}")
        st.rerun()
    except Exception as e:
        render_toast_error(f"Error: {e}")


def show_resolve_dialog(feedback_id: str) -> None:
    @st.dialog("✅ Resolver Feedback")
    def _dialog():
        respuesta = st.text_area("Respuesta al usuario *", placeholder="Explica la solución o próximos pasos...", height=120)
        if st.button("Confirmar Resolución", type="primary", use_container_width=True):
            if not respuesta.strip():
                render_toast_error("La respuesta es obligatoria")
            else:
                try:
                    from config.supabase_client import get_client
                    client = get_client()
                    client.table(TABLE_NAMES.get("feedback", "feedback")).update({
                        "estado": "resuelto",
                        "respuesta_admin": respuesta.strip(),
                        "responded_by": get_current_user_id(),
                        "responded_at": datetime.now().isoformat()
                    }).eq("id", feedback_id).execute()
                    render_toast_success("Feedback resuelto")
                    st.rerun()
                except Exception as e:
                    render_toast_error(f"Error: {e}")

    _dialog()
