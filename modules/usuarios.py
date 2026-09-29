import streamlit as st
import pandas as pd
from utils.data import get_profiles, update_record, TABLE_NAMES
from components.dialogs import perfil_dialog
from components.ui import render_page_header, render_empty_state, render_toast_success, render_toast_error, render_badge
from modules.auth import has_permission, is_admin, admin_create_user, admin_update_user_profile
from config.constants import MENSAJES, RolUsuario


def render_usuarios() -> None:
    if not st.session_state.get("user"):
        return

    if not is_admin():
        st.error(MENSAJES["sin_permisos"])
        return

    render_page_header("Usuarios", "Directorio y gestión de colaboradores e inversores", "👥")

    tab1, tab2 = st.tabs(["📋 Directorio", "➕ Crear Usuario"])

    with tab1:
        render_usuarios_table()

    with tab2:
        render_crear_usuario()


def render_usuarios_table() -> None:
    df = get_profiles()

    if df.empty:
        render_empty_state("👥", "Sin usuarios", "No hay perfiles registrados en el sistema.")
        return

    search = st.text_input("🔍 Buscar", placeholder="Filtrar por nombre, email, rol...", key="usuarios_search")

    if search:
        search = search.lower().strip()
        mask = (
            df["nombre"].astype(str).str.lower().str.contains(search) |
            df["email"].astype(str).str.lower().str.contains(search) |
            df["rol"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    # Ensure contact columns exist
    for col in ["telefono", "grupo", "direccion", "ciudad", "notas_contacto"]:
        if col not in df.columns:
            df[col] = ""

    display_cols = ["nombre", "email", "telefono", "rol", "grupo", "activo", "ciudad"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_config = {
        "nombre": st.column_config.TextColumn("Nombre", width="medium"),
        "email": st.column_config.TextColumn("Email", width="large"),
        "telefono": st.column_config.TextColumn("Teléfono", width="medium"),
        "rol": st.column_config.TextColumn("Rol", width="small"),
        "grupo": st.column_config.TextColumn("Grupo", width="medium"),
        "activo": st.column_config.CheckboxColumn("Activo", width="small"),
        "ciudad": st.column_config.TextColumn("Ciudad", width="medium"),
    }

    st.dataframe(
        df[display_cols],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    st.divider()

    render_editar_usuario(df)


def render_crear_usuario() -> None:
    """Formulario para que el admin cree nuevos usuarios con email/password y info de contacto"""
    st.markdown("### ➕ Crear Nuevo Usuario")
    st.caption("El usuario recibirá credenciales de acceso por email. Complete la información de contacto.")

    with st.form("crear_usuario_admin", clear_on_submit=True):
        st.markdown("#### 📧 Credenciales de Acceso")
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email *", placeholder="usuario@ejemplo.com")
            password = st.text_input("Contraseña *", type="password", placeholder="Mínimo 6 caracteres")
        with c2:
            nombre = st.text_input("Nombre completo *", placeholder="Juan Pérez")
            roles = RolUsuario.opciones()
            rol = st.selectbox("Rol *", roles, index=roles.index("colaborador"))

        st.markdown("#### 📞 Información de Contacto")
        c1, c2 = st.columns(2)
        with c1:
            telefono = st.text_input("Teléfono", placeholder="+57 300 123 4567")
            direccion = st.text_input("Dirección", placeholder="Calle 123 #45-67")
        with c2:
            grupo = st.selectbox("Grupo", ["", "Administración", "Operaciones", "Veterinaria", "Inversionistas", "Familia"])
            ciudad = st.text_input("Ciudad", placeholder="Bogotá, Medellín, Cali...")

        notas_contacto = st.text_area("Notas adicionales de contacto", placeholder="Horarios de disponibilidad, preferencias de comunicación, etc.")

        activo = st.checkbox("Usuario activo", value=True)

        crear = st.form_submit_button("👤 Crear Usuario", type="primary", use_container_width=True)

        if crear:
            if not email or not password or not nombre:
                render_toast_error("Email, contraseña y nombre son obligatorios")
            elif len(password) < 6:
                render_toast_error("La contraseña debe tener al menos 6 caracteres")
            else:
                data = {
                    "email": email.strip(),
                    "password": password,
                    "nombre": nombre.strip(),
                    "rol": rol,
                    "telefono": telefono.strip(),
                    "grupo": grupo,
                    "direccion": direccion.strip(),
                    "ciudad": ciudad.strip(),
                    "notas_contacto": notas_contacto.strip(),
                }
                success, msg = admin_create_user(**data)
                if success:
                    render_toast_success(msg)
                    st.rerun()
                else:
                    render_toast_error(f"Error: {msg}")


def render_editar_usuario(df: pd.DataFrame) -> None:
    st.subheader("✏️ Editar Usuario / Info de Contacto")

    if "user_id" not in df.columns:
        st.warning("No se pueden editar usuarios sin ID.")
        return

    # Ensure contact columns exist
    for col in ["telefono", "grupo", "direccion", "ciudad", "notas_contacto"]:
        if col not in df.columns:
            df[col] = ""

    user_ids = df["user_id"].astype(str).tolist()
    if not user_ids:
        return

    selected_id = st.selectbox(
        "Seleccionar usuario",
        user_ids,
        format_func=lambda x: f"{df[df['user_id'].astype(str) == x]['nombre'].values[0] if not df[df['user_id'].astype(str) == x].empty else x} ({df[df['user_id'].astype(str) == x]['email'].values[0] if not df[df['user_id'].astype(str) == x].empty else ''})"
    )

    usuario = df[df["user_id"].astype(str) == selected_id].iloc[0]

    with st.form("editar_usuario_form"):
        st.markdown("#### 👤 Información Básica")
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre", value=str(usuario.get("nombre", "")))
            telefono = st.text_input("Teléfono", value=str(usuario.get("telefono", "")))
            direccion = st.text_input("Dirección", value=str(usuario.get("direccion", "")))
        with c2:
            roles = RolUsuario.opciones()
            rol = st.selectbox(
                "Rol",
                roles,
                index=roles.index(usuario.get("rol", "colaborador")) if usuario.get("rol") in roles else 3
            )
            grupo = st.selectbox("Grupo", ["", "Administración", "Operaciones", "Veterinaria", "Inversionistas", "Familia"], 
                               index=["", "Administración", "Operaciones", "Veterinaria", "Inversionistas", "Familia"].index(usuario.get("grupo", "")) if usuario.get("grupo", "") in ["", "Administración", "Operaciones", "Veterinaria", "Inversionistas", "Familia"] else 0)
            ciudad = st.text_input("Ciudad", value=str(usuario.get("ciudad", "")))

        notas_contacto = st.text_area("Notas de contacto", value=str(usuario.get("notas_contacto", "")))
        activo = st.checkbox("Usuario activo", value=bool(usuario.get("activo", True)))

        guardar = st.form_submit_button("Guardar Cambios", type="primary")

        if guardar:
            data = {
                "nombre": nombre,
                "telefono": telefono,
                "rol": rol,
                "grupo": grupo,
                "direccion": direccion,
                "ciudad": ciudad,
                "notas_contacto": notas_contacto,
                "activo": activo
            }
            try:
                success, msg = admin_update_user_profile(selected_id, data)
                if success:
                    render_toast_success(msg)
                    st.rerun()
                else:
                    render_toast_error(msg)
            except Exception as e:
                render_toast_error(f"Error: {e}")
