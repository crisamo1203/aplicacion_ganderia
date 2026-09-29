"""Componentes visuales reutilizables para la interfaz móvil."""
import streamlit as st


def apply_theme() -> None:
    """Compatibility no-op: app.configure_page() injects the shared theme once."""
    return None


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<section class="mf-hero"><h1>{title}</h1><p>{subtitle}</p></section>', unsafe_allow_html=True)


def error(exc: Exception) -> None:
    st.error("No fue posible completar la operación. Verifica conexión y permisos.")
    with st.expander("Detalle técnico"):
        st.code(str(exc))
