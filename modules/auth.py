import logging
import html
import secrets
import threading
import time
import streamlit as st
from typing import Optional, Tuple, List
from config.supabase_client import get_client, get_supabase_client, reset_client_session
from config.constants import MENSAJES, RolUsuario, PERMISSION_MATRIX, NAVIGATION_ORDER, MODULE_LABELS, MODULE_ICONS
from utils.data import get_profiles, invalidate_cache
from components.ui import render_toast_success, render_toast_error, render_toast_info
import json

logger = logging.getLogger(__name__)

# Google may return to a new Streamlit websocket session after the browser
# redirects to the provider. Keep only one-time PKCE verifiers in process memory.
_OAUTH_PENDING_TTL_SECONDS = 600
_oauth_pending_lock = threading.Lock()
_oauth_pending_verifiers: dict[str, tuple[str, float]] = {}


def render_google_oauth_link(url: str) -> None:
    """Render Google OAuth navigation in the current tab (no JavaScript)."""
    safe_url = html.escape(url, quote=True)
    st.markdown(
        f'<a class="mf-google-oauth-link" href="{safe_url}" target="_self" '
        'rel="noopener noreferrer"><span aria-hidden="true">🔐</span> '
        'Continuar con Google</a>',
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    defaults = {
        "session": None,
        "user": None,
        "profile": None,
        "pagina": "dashboard",
        "sidebar_collapsed": False,
        "auth_initialized": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def restore_session() -> bool:
    """Check if we already have a valid session in session_state"""
    if st.session_state.get("auth_initialized"):
        return st.session_state.user is not None
    
    # Session is already in session_state from OAuth callback or password login
    if st.session_state.get("user") and st.session_state.get("session"):
        st.session_state.auth_initialized = True
        return True
    
    st.session_state.auth_initialized = True
    return False


def get_current_profile() -> dict:
    return st.session_state.profile or {}


def get_current_user_id() -> Optional[str]:
    if st.session_state.user:
        return str(st.session_state.user.id)
    return None


def get_current_role() -> str:
    profile = get_current_profile()
    return str(profile.get("rol", "colaborador")).lower()


def is_admin() -> bool:
    return RolUsuario.es_admin(get_current_role())


def can_edit() -> bool:
    return RolUsuario.puede_editar(get_current_role())


def has_permission(module: str, action: str) -> bool:
    role = get_current_role()
    permissions = PERMISSION_MATRIX.get(module, {}).get(role, [])
    return action in permissions


def require_permission(module: str, action: str = "read") -> bool:
    if not has_permission(module, action):
        st.error(MENSAJES["sin_permisos"])
        return False
    return True


def login_with_password(email: str, password: str) -> Tuple[bool, str]:
    try:
        client = get_client()
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.session is None:
            return False, MENSAJES["login_fallido"]

        st.session_state.session = response.session
        st.session_state.user = response.user

        profile = load_user_profile(response.user.id)
        st.session_state.profile = profile

        return True, ""
    except Exception as e:
        return False, str(e)


def login_with_google() -> Optional[str]:
    """Create a Google OAuth URL and retain its one-time PKCE verifier."""
    try:
        client = get_client()
        app_url = str(st.secrets["supabase"].get("app_url", "http://localhost:8501")).rstrip("/")
        if not app_url.startswith(("http://", "https://")):
            raise ValueError("supabase.app_url debe comenzar con http:// o https://")
        attempt = secrets.token_urlsafe(24)
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": f"{app_url}/?oauth_attempt={attempt}",
                "query_params": {"prompt": "select_account"},
            }
        })
        if not response.url:
            raise RuntimeError("Supabase no devolvió la URL de autorización de Google.")

        # The callback may open in a new Streamlit session, so its in-memory SDK
        # storage cannot be assumed to contain the PKCE verifier. The random,
        # short-lived attempt key lets that callback retrieve it safely.
        auth = client.auth
        storage = getattr(auth, "_storage", None)
        storage_key = getattr(auth, "_storage_key", None)
        verifier = storage.get_item(f"{storage_key}-code-verifier") if storage and storage_key else None
        if not verifier:
            raise RuntimeError("No se pudo preparar la verificación segura PKCE de Google.")
        now = time.time()
        with _oauth_pending_lock:
            expired = [key for key, (_, expires_at) in _oauth_pending_verifiers.items() if expires_at <= now]
            for key in expired:
                _oauth_pending_verifiers.pop(key, None)
            if len(_oauth_pending_verifiers) >= 512:
                oldest = min(_oauth_pending_verifiers, key=lambda key: _oauth_pending_verifiers[key][1])
                _oauth_pending_verifiers.pop(oldest, None)
            _oauth_pending_verifiers[attempt] = (verifier, now + _OAUTH_PENDING_TTL_SECONDS)
        return response.url
    except Exception as e:
        render_toast_error(f"Error iniciando OAuth: {e}")
        return None


def handle_oauth_callback() -> bool:
    """Handle OAuth callback from Google/Supabase"""
    # Check for code in query params (from Supabase redirect)
    if "code" in st.query_params:
        code = st.query_params["code"]
        attempt = st.query_params.get("oauth_attempt")
        try:
            client = get_client()
            verifier = None
            if attempt:
                now = time.time()
                with _oauth_pending_lock:
                    expired = [key for key, (_, expires_at) in _oauth_pending_verifiers.items() if expires_at <= now]
                    for key in expired:
                        _oauth_pending_verifiers.pop(key, None)
                    pending = _oauth_pending_verifiers.pop(str(attempt), None)
                verifier = pending[0] if pending else None
            if not verifier:
                auth = client.auth
                storage = getattr(auth, "_storage", None)
                storage_key = getattr(auth, "_storage_key", None)
                verifier = storage.get_item(f"{storage_key}-code-verifier") if storage and storage_key else None
            if not verifier:
                raise RuntimeError("La verificación de Google expiró. Vuelve a pulsar ‘Continuar con Google’.")
            response = client.auth.exchange_code_for_session({
                "auth_code": code,
                "code_verifier": verifier,
            })

            if response.session:
                st.session_state.session = response.session
                st.session_state.user = response.user

                profile = load_user_profile(response.user.id)
                st.session_state.profile = profile

                # Clear the code from URL
                st.query_params.clear()
                return True
        except Exception:
            logger.exception("OAuth callback failed")
            render_toast_error("No se pudo completar el inicio de sesión. Intenta nuevamente.")
            return False
    
    # Also check for access_token in hash (implicit flow)
    # This won't work with server-side code but kept for reference
    return False


def load_user_profile(user_id: str) -> Optional[dict]:
    try:
        client = get_client()
        response = client.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
        if response.data:
            return response.data

        email = st.session_state.user.email if st.session_state.user else f"user-{user_id}"
        new_profile = {
            "id": user_id,
            "email": email,
            "rol": "colaborador",
            "nombre": email.split("@")[0],
            "telefono": "",
            "grupo": "",
            "activo": True,
            "direccion": "",
            "ciudad": "",
            "notas_contacto": "",
        }
        client.table("profiles").insert(new_profile).execute()
        return new_profile
    except Exception:
        logger.exception("Error al cargar el perfil del usuario")
        return None


def admin_create_user(email: str, password: str, nombre: str, rol: str, telefono: str = "", 
                       grupo: str = "", direccion: str = "", ciudad: str = "", 
                       notas_contacto: str = "") -> Tuple[bool, str]:
    """Admin creates a new user with email/password and profile info"""
    try:
        client = get_client()
        
        # Create auth user
        auth_response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"nombre": nombre}
        })
        
        if not auth_response.user:
            return False, "No se pudo crear el usuario en Auth"
        
        user_id = auth_response.user.id
        
        # Create profile with contact info
        profile_data = {
            "id": user_id,
            "email": email,
            "rol": rol,
            "nombre": nombre,
            "telefono": telefono,
            "grupo": grupo,
            "activo": True,
            "direccion": direccion,
            "ciudad": ciudad,
            "notas_contacto": notas_contacto,
        }
        client.table("profiles").insert(profile_data).execute()
        
        return True, f"Usuario {nombre} creado exitosamente"
    except Exception as e:
        return False, str(e)


def admin_update_user_profile(user_id: str, data: dict) -> Tuple[bool, str]:
    """Admin updates user profile including contact info"""
    try:
        client = get_client()
        client.table("profiles").update(data).eq("id", user_id).execute()
        return True, "Perfil actualizado"
    except Exception as e:
        return False, str(e)


def logout() -> None:
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:
        pass
    reset_client_session()

    st.session_state.session = None
    st.session_state.user = None
    st.session_state.profile = None
    st.session_state.pagina = "dashboard"
    invalidate_cache()
    render_toast_info(MENSAJES["logout_exitoso"])


def get_accessible_modules() -> List[str]:
    role = get_current_role()
    accessible = []
    for module in NAVIGATION_ORDER:
        if has_permission(module, "read"):
            accessible.append(module)
    return accessible


def render_login_page() -> None:
    st.markdown("""
    <div class="login-container">
        <div class="login-title">🐄 MyFinca_Pro</div>
        <p class="login-subtitle">Sistema de gestión ganadera y agrícola</p>
    </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])

    with center:
        st.subheader("Iniciar sesión")

        tab1, tab2 = st.tabs(["📧 Email / Contraseña", "🔐 Google"])

        with tab1:
            st.caption("Usa la contraseña creada para esta aplicación. Si tu cuenta se registró con Google, entra desde la pestaña Google; no escribas aquí la contraseña de Gmail.")
            with st.form("login_form"):
                email = st.text_input("Correo electrónico", placeholder="tu@email.com")
                password = st.text_input("Contraseña", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

            if submit:
                if not email or not password:
                    render_toast_error("Debes ingresar correo y contraseña")
                else:
                    success, msg = login_with_password(email, password)
                    if success:
                        render_toast_success(MENSAJES["login_exitoso"])
                        st.rerun()
                    else:
                        render_toast_error(msg)

        with tab2:
            st.write("Inicia sesión con tu cuenta de Google")
            oauth_url = login_with_google()
            if oauth_url:
                render_google_oauth_link(oauth_url)


def render_sidebar() -> None:
    init_session_state()

    with st.sidebar:
        # Dark/Light mode toggle at top of sidebar
        dark_mode = st.session_state.get("dark_mode", False)
        col_sun, col_moon = st.columns([1, 1])
        with col_sun:
            if st.button("☀️", key="theme_light", use_container_width=True, 
                         help="Modo claro", type="secondary" if dark_mode else "primary"):
                if dark_mode:
                    st.session_state.dark_mode = False
                    st.rerun()
        with col_moon:
            if st.button("🌙", key="theme_dark", use_container_width=True,
                         help="Modo oscuro", type="secondary" if not dark_mode else "primary"):
                if not dark_mode:
                    st.session_state.dark_mode = True
                    st.rerun()

        st.markdown("# 🐄 MyFinca_Pro")
        st.markdown('<span style="color: var(--sidebar-text); opacity: 0.9; font-weight: 500;">Gestión ganadera y agrícola</span>', unsafe_allow_html=True)

        profile = get_current_profile()
        nombre = profile.get("nombre", st.session_state.user.email if st.session_state.user else "Usuario")
        rol = profile.get("rol", "colaborador")

        st.write(f"**{nombre}**")
        st.markdown(f'<span style="color: var(--sidebar-text); opacity: 0.9; font-weight: 500;">Rol: {rol}</span>', unsafe_allow_html=True)

        st.divider()

        accessible_modules = get_accessible_modules()

        for module in accessible_modules:
            label = MODULE_LABELS.get(module, module)
            icon = MODULE_ICONS.get(module, "📄")
            is_active = st.session_state.pagina == module

            btn_style = "primary" if is_active else "secondary"
            if st.button(
                f"{icon} {label}",
                key=f"nav_{module}",
                use_container_width=True,
                type=btn_style
            ):
                st.session_state.pagina = module
                st.rerun()

        st.link_button("📲 Operación de campo", "/campo/", use_container_width=True)
        st.divider()

        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()


def get_current_page() -> str:
    return st.session_state.pagina


def set_current_page(page: str) -> None:
    if page in NAVIGATION_ORDER:
        st.session_state.pagina = page
