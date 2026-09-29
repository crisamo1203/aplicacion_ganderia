import os
from pathlib import Path
import streamlit as st
from modules.auth import (
    init_session_state, render_login_page, render_sidebar,
    handle_oauth_callback, get_current_page, load_user_profile, is_admin,
    restore_session, get_accessible_modules
)

# Test mode is opt-in and must never be enabled in production.
TEST_MODE = os.getenv("TEST_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
from modules.dashboard import render_dashboard
from modules.inventario import render_inventario
from modules.ventas import render_ventas
from modules.produccion import render_produccion
from modules.ceba import render_ceba
from modules.historial import render_historial
from modules.administracion import render_administracion
from modules.salud import render_salud
from modules.usuarios import render_usuarios
from modules.feedback import render_feedback_user, render_feedback_admin
from components.filters import render_global_filters_sidebar, load_user_filter_preference
from utils.alerts import render_alerts_dropdown


def configure_page() -> None:
    st.set_page_config(
        page_title="MyFinca_Pro",
        page_icon="🐄",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "MyFinca_Pro - Sistema de gestión ganadera y agrícola",
        },
    )

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False

    # Mantener una sola fuente de verdad para las variables del tema.
    dark = bool(st.session_state.dark_mode)
    if dark:
        theme_vars = """
        :root {
          color-scheme: dark;
          --primary: #69bd7a; --primary-light: #7bc98a; --primary-lighter: #9bd8a7;
          --primary-bg: #20372a; --secondary: #77b9ef; --accent: #ffc16c;
          --success: #74c989; --warning: #f5bd61; --error: #f28d8d; --info: #77b9ef;
          --bg: #111714; --card-bg: #1e232a; --card-bg-hover: #292f38;
          --border: #363e49; --text: #edf2f7; --text-secondary: #b8c1cc;
          --text-muted: #8da092; --sidebar-start: #102f1d; --sidebar-end: #1d5633;
          --sidebar-text: #f5fbf6; --sidebar-text-hover: #a9dfb7; --sidebar-border: #365442;
          --shadow-sm: 0 1px 3px rgba(0,0,0,.3); --shadow: 0 4px 16px rgba(0,0,0,.28);
          --shadow-lg: 0 8px 28px rgba(0,0,0,.36); --radius-sm: 8px; --radius: 12px;
          --radius-lg: 16px; --transition: all .2s ease;
          --input-bg: #1e232a; --input-border: #414a56; --hover-bg: #292f38;
        }
        """
    else:
        theme_vars = """
        :root {
          color-scheme: light;
          --primary: #1b5e20; --primary-light: #2e7d32; --primary-lighter: #4caf50;
          --primary-bg: #e8f5e9; --secondary: #0d47a1; --accent: #e87813;
          --success: #2e7d32; --warning: #9a6500; --error: #b3261e; --info: #0277bd;
          --bg: #f4f7f4; --card-bg: #ffffff; --card-bg-hover: #f4f8f4;
          --border: #dce5dd; --text: #1a241c; --text-secondary: #506052;
          --text-muted: #68766b; --sidebar-start: #102f1d; --sidebar-end: #1d5633;
          --sidebar-text: #f5fbf6; --sidebar-text-hover: #a9dfb7; --sidebar-border: #365442;
          --shadow-sm: 0 1px 3px rgba(0,0,0,.06); --shadow: 0 4px 16px rgba(25,55,32,.08);
          --shadow-lg: 0 8px 28px rgba(25,55,32,.12); --radius-sm: 8px; --radius: 12px;
          --radius-lg: 16px; --transition: all .2s ease;
          --input-bg: #ffffff; --input-border: #cbd8cd; --hover-bg: #f2f7f2;
        }
        """

    global_css = Path(__file__).parent / "styles" / "global.css"
    css = theme_vars
    if global_css.is_file():
        css += "\n" + global_css.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def main() -> None:
    configure_page()
    init_session_state()

    # TEST MODE: Create mock user for testing
    if TEST_MODE and not st.session_state.user:
        st.session_state.user = type('obj', (object,), {
            'id': 'test-user-id',
            'email': 'test@test.com'
        })
        st.session_state.profile = {
            'id': 'test-user-id',
            'email': 'test@test.com',
            'nombre': 'Usuario Test',
            'rol': 'admin',
            'activo': True,
            'telefono': '',
            'grupo': '',
            'direccion': '',
            'ciudad': '',
            'notas_contacto': ''
        }
        st.session_state.session = type('obj', (object,), {
            'access_token': 'test-token',
            'refresh_token': 'test-refresh'
        })

    # Handle OAuth callback
    if "code" in st.query_params:
        if handle_oauth_callback():
            st.rerun()

    # Restore session from storage (persists login across refreshes)
    restore_session()

    # Load user filter preferences on first load
    if "user" in st.session_state and st.session_state.user and "profile" in st.session_state:
        load_user_filter_preference()

    if not st.session_state.user:
        render_login_page()
        return

    # Render sidebar with navigation and global filters
    render_sidebar()
    accessible_modules = get_accessible_modules()
    if not accessible_modules:
        st.title("Registro de campo")
        st.info("Tu perfil no tiene acceso a los módulos administrativos de Streamlit. Usa la aplicación móvil de campo para registrar nacimientos, pesajes, sanidad, traslados y muertes.")
        st.link_button("Abrir MyFinca Pro · Campo", "/campo/", type="primary")
        return

    render_global_filters_sidebar()
    render_alerts_dropdown()

    # Route to current page
    page = get_current_page()

    page_renderers = {
        "dashboard": render_dashboard,
        "inventario": render_inventario,
        "ventas": render_ventas,
        "produccion": render_produccion,
        "ceba": render_ceba,
        "historial": render_historial,
        "administracion": render_administracion,
        "salud": render_salud,
        "usuarios": render_usuarios,
        "feedback": render_feedback_admin if is_admin() else render_feedback_user,
    }

    if page not in accessible_modules:
        page = accessible_modules[0]
    renderer = page_renderers.get(page)
    if renderer is None:
        st.error("No hay un módulo autorizado para este perfil.")
        return
    renderer()


if __name__ == "__main__":
    main()
