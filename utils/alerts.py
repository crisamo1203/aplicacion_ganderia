from utils.data import check_alertas


def get_sidebar_alert_count() -> dict:
    alertas = check_alertas()
    return {
        "criticas": len([a for a in alertas if a.get("severidad") == "critica"]),
        "advertencias": len([a for a in alertas if a.get("severidad") == "advertencia"]),
        "info": len([a for a in alertas if a.get("severidad") == "info"]),
        "total": len(alertas)
    }


def render_alerts_dropdown() -> None:
    alertas = check_alertas()
    if not alertas:
        return

    with st.sidebar:
        st.markdown("---")
        st.subheader("🔔 Alertas")

        counts = get_sidebar_alert_count()
        if counts["criticas"] > 0:
            st.error(f"🔴 {counts['criticas']} crítica{'s' if counts['criticas'] > 1 else ''}")
        if counts["advertencias"] > 0:
            st.warning(f"🟡 {counts['advertencias']} advertencia{'s' if counts['advertencias'] > 1 else ''}")
        if counts["info"] > 0:
            st.info(f"🔵 {counts['info']} aviso{'s' if counts['info'] > 1 else ''}")

        with st.expander("Ver detalles"):
            for a in alertas[:10]:
                severity_icon = {"critica": "🔴", "advertencia": "🟡", "info": "🔵"}.get(a.get("severidad"), "⚪")
                st.write(f"{severity_icon} {a['mensaje']}")
                if st.button("Ir", key=f"alert_goto_{a.get('animal_id', '')}_{a['tipo']}", use_container_width=True):
                    import streamlit as st
                    st.session_state.pagina = a["accion"]
                    st.rerun()
