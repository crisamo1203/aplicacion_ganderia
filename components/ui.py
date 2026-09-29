import streamlit as st
from typing import Optional, List, Dict, Any, Callable
from config.constants import UI_COLORS, EstadoAnimal, MENSAJES


def render_metric_card(
    label: str,
    value: Any,
    delta: Optional[str] = None,
    icon: Optional[str] = None,
    color: str = "primary",
    help_text: Optional[str] = None
) -> None:
    color_map = {
        "primary": UI_COLORS["primary"],
        "success": UI_COLORS["success"],
        "warning": UI_COLORS["warning"],
        "error": UI_COLORS["error"],
        "info": UI_COLORS["info"],
    }
    bg_color = color_map.get(color, UI_COLORS["primary"])

    icon_html = f'<span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>' if icon else ''

    delta_html = ''
    if delta:
        delta_color = UI_COLORS["success"] if not delta.startswith("-") else UI_COLORS["error"]
        delta_html = f'<div style="color: {delta_color}; font-size: 0.85rem; margin-top: 0.25rem;">{delta}</div>'

    st.markdown(f"""
    <div class="mf-metric-card" style="
        background: var(--card-bg, {UI_COLORS['card_bg']});
        border: 1px solid var(--border, {UI_COLORS['card_border']});
        border-radius: 15px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-left: 4px solid {bg_color};
    ">
        <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--text-secondary, {UI_COLORS['text_secondary']}); font-size: 0.9rem; font-weight: 500; margin-bottom: 0.5rem;">
            {icon_html}{label}
        </div>
        <div style="font-size: 2rem; font-weight: 700; color: var(--text, {UI_COLORS['text_primary']}); line-height: 1.2;">
            {value}
        </div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

    if help_text:
        st.caption(help_text)


def render_alert_banner(alertas: List[Dict[str, Any]]) -> None:
    if not alertas:
        return

    criticas = [a for a in alertas if a.get("severidad") == "critica"]
    advertencias = [a for a in alertas if a.get("severidad") == "advertencia"]
    info = [a for a in alertas if a.get("severidad") == "info"]

    if criticas:
        with st.container():
            st.error(f"🔴 **{len(criticas)} alerta{'s' if len(criticas) > 1 else ''} crítica{'s' if len(criticas) > 1 else ''}**")
            for a in criticas[:3]:
                cols = st.columns([4, 1])
                cols[0].write(f"• {a['mensaje']}")
                if cols[1].button("Ir", key=f"alert_{a['tipo']}_{a.get('animal_id', '')}", use_container_width=True):
                    st.session_state.pagina = a["accion"]
                    if a.get("animal_id"):
                        st.session_state[f"filter_animal_{a['accion']}"] = a["animal_id"]
                    st.rerun()
            if len(criticas) > 3:
                st.caption(f"... y {len(criticas) - 3} más")

    if advertencias:
        with st.container():
            st.warning(f"🟡 **{len(advertencias)} advertencia{'s' if len(advertencias) > 1 else ''}**")
            for a in advertencias[:3]:
                cols = st.columns([4, 1])
                cols[0].write(f"• {a['mensaje']}")
                if cols[1].button("Ir", key=f"alert_{a['tipo']}_{a.get('animal_id', '')}_w", use_container_width=True):
                    st.session_state.pagina = a["accion"]
                    if a.get("animal_id"):
                        st.session_state[f"filter_animal_{a['accion']}"] = a["animal_id"]
                    st.rerun()
            if len(advertencias) > 3:
                st.caption(f"... y {len(advertencias) - 3} más")

    if info and not criticas and not advertencias:
        with st.container():
            st.info(f"🔵 **{len(info)} aviso{'s' if len(info) > 1 else ''}**")
            for a in info[:3]:
                st.write(f"• {a['mensaje']}")


def render_sidebar_alert_badge(alertas: List[Dict[str, Any]]) -> None:
    if not alertas:
        return

    criticas = len([a for a in alertas if a.get("severidad") == "critica"])
    advertencias = len([a for a in alertas if a.get("severidad") == "advertencia"])

    badge_parts = []
    if criticas > 0:
        badge_parts.append(f"🔴 {criticas}")
    if advertencias > 0:
        badge_parts.append(f"🟡 {advertencias}")

    if badge_parts:
        st.sidebar.markdown(
            f'<div style="background: {UI_COLORS["error"]}; color: white; padding: 0.25rem 0.5rem; '
            f'border-radius: 12px; font-size: 0.75rem; font-weight: bold; display: inline-block;">'
            f'{" | ".join(badge_parts)} alertas</div>',
            unsafe_allow_html=True
        )


def render_empty_state(
    icon: str,
    title: str,
    message: str,
    cta_label: Optional[str] = None,
    cta_callback: Optional[Callable] = None,
    cta_key: Optional[str] = None
) -> None:
    st.markdown(f"""
    <div class="mf-card" style="text-align: center; padding: 3rem 2rem; background: var(--card-bg, {UI_COLORS['card_bg']}); border-radius: 15px; border: 1px solid var(--border, {UI_COLORS['card_border']});">
        <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
        <h3 style="color: var(--text, {UI_COLORS['text_primary']}); margin-bottom: 0.5rem;">{title}</h3>
        <p style="color: var(--text-secondary, {UI_COLORS['text_secondary']}); margin-bottom: 1.5rem;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

    if cta_label and cta_callback:
        if st.button(cta_label, type="primary", key=cta_key, use_container_width=True):
            cta_callback()


def render_badge(text: str, color: str = "gray", size: str = "normal") -> None:
    size_styles = {
        "small": "font-size: 0.7rem; padding: 0.15rem 0.5rem;",
        "normal": "font-size: 0.8rem; padding: 0.25rem 0.75rem;",
        "large": "font-size: 0.9rem; padding: 0.4rem 1rem;",
    }

    color_map = {
        "green": UI_COLORS["success"],
        "blue": UI_COLORS["info"],
        "orange": UI_COLORS["warning"],
        "red": UI_COLORS["error"],
        "purple": "#9C27B0",
        "gray": UI_COLORS["text_secondary"],
    }
    bg = color_map.get(color, UI_COLORS["text_secondary"])

    st.markdown(f"""
    <span style="
        {size_styles.get(size, size_styles['normal'])}
        background: {bg};
        color: white;
        border-radius: 20px;
        font-weight: 600;
        white-space: nowrap;
    ">{text}</span>
    """, unsafe_allow_html=True)


def render_estado_animal(estado: str) -> None:
    color = EstadoAnimal.color(estado)
    icon_map = {
        "Activo": "✅",
        "Vendido": "💰",
        "Fallecido": "💀",
        "Trasladado": "🚚",
        "En Ceba": "⚖️",
    }
    icon = icon_map.get(estado, "❓")
    render_badge(f"{icon} {estado}", color)


def render_action_buttons(
    row_id: str,
    actions: List[Dict[str, Any]],
    key_prefix: str = "action"
) -> None:
    cols = st.columns(len(actions))
    for i, action in enumerate(actions):
        with cols[i]:
            if st.button(
                action.get("label", "Acción"),
                key=f"{key_prefix}_{action['key']}_{row_id}",
                help=action.get("help"),
                use_container_width=True,
                type=action.get("type", "secondary")
            ):
                if action.get("callback"):
                    action["callback"](row_id)


def render_dataframe_with_actions(
    df,
    column_config: Dict[str, Any],
    action_columns: List[Dict[str, Any]],
    key: str = "dataframe",
    height: Optional[int] = None,
    hide_index: bool = True,
    on_select: Optional[Callable] = None
) -> Any:
    if df is None or df.empty:
        render_empty_state("📭", "Sin datos", "No hay registros para mostrar.")
        return None

    display_df = df.copy()

    for action in action_columns:
        display_df[action["key"]] = ""

    all_columns = list(column_config.keys()) + [a["key"] for a in action_columns]

    selection = st.dataframe(
        display_df[all_columns],
        column_config=column_config,
        use_container_width=True,
        hide_index=hide_index,
        height=height,
        key=key,
        on_select="rerun" if on_select else None,
        selection_mode="single-row"
    )

    if on_select and selection and hasattr(selection, "selection") and selection.selection.rows:
        row_idx = selection.selection.rows[0]
        row_data = df.iloc[row_idx].to_dict()
        on_select(row_data)

    return selection


def render_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    st.markdown(f"""
    <div style="margin-bottom: 1.5rem;">
        <h1 style="
            font-size: 2rem;
            font-weight: 800;
            color: {UI_COLORS['primary']};
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        ">
            {icon} {title}
        </h1>
        {f'<p style="color: var(--text-secondary, {UI_COLORS["text_secondary"]}); margin: 0.5rem 0 0 0;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, icon: str = "", count: Optional[int] = None) -> None:
    count_html = f'<span style="background: {UI_COLORS["primary"]}; color: white; padding: 0.15rem 0.5rem; border-radius: 10px; font-size: 0.75rem; margin-left: 0.5rem;">{count}</span>' if count is not None else ''
    st.markdown(f"""
    <h2 style="
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text, {UI_COLORS['text_primary']});
        margin: 1.5rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    ">
        {icon} {title}{count_html}
    </h2>
    """, unsafe_allow_html=True)


def render_divider() -> None:
    st.markdown(f'<hr style="border: none; border-top: 1px solid {UI_COLORS["card_border"]}; margin: 1.5rem 0;">', unsafe_allow_html=True)


def render_toast_success(message: str) -> None:
    st.toast(f"✅ {message}", icon="✅")


def render_toast_error(message: str) -> None:
    st.toast(f"❌ {message}", icon="❌")


def render_toast_warning(message: str) -> None:
    st.toast(f"⚠️ {message}", icon="⚠️")


def render_toast_info(message: str) -> None:
    st.toast(f"ℹ️ {message}", icon="ℹ️")


def confirm_dialog(
    title: str,
    message: str,
    confirm_label: str = "Confirmar",
    cancel_label: str = "Cancelar",
    key: str = "confirm",
    type: str = "primary"
) -> bool:
    @st.dialog(title)
    def _dialog():
        st.write(message)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(confirm_label, type=type, use_container_width=True):
                st.session_state[f"{key}_result"] = True
                st.rerun()
        with c2:
            if st.button(cancel_label, use_container_width=True):
                st.session_state[f"{key}_result"] = False
                st.rerun()

    _dialog()
    return st.session_state.get(f"{key}_result", False)


def render_info_card(title: str, content: str, icon: str = "ℹ️", color: str = "info") -> None:
    color_map = {
        "info": UI_COLORS["info"],
        "success": UI_COLORS["success"],
        "warning": UI_COLORS["warning"],
        "error": UI_COLORS["error"],
    }
    border_color = color_map.get(color, UI_COLORS["info"])

    st.markdown(f"""
    <div class="mf-card" style="
        background: var(--card-bg, {UI_COLORS['card_bg']});
        border: 1px solid var(--border, {UI_COLORS['card_border']});
        border-left: 4px solid {border_color};
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    ">
        <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
            <span style="font-size: 1.25rem; margin-top: 0.1rem;">{icon}</span>
            <div style="flex: 1;">
                <strong style="color: var(--text, {UI_COLORS['text_primary']});">{title}</strong>
                <p style="color: var(--text-secondary, {UI_COLORS['text_secondary']}); margin: 0.25rem 0 0 0;">{content}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_loading_skeleton(lines: int = 3) -> None:
    st.mark(f"""
    <div style="padding: 1rem;">
        {''.join([
            f'<div style="height: 1rem; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: loading 1.5s infinite; border-radius: 4px; margin-bottom: 0.5rem;"></div>'
            for _ in range(lines)
        ])}
    </div>
    <style>
    @keyframes loading {{
        0% {{ background-position: 200% 0; }}
        100% {{ background-position: -200% 0; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def render_progress_steps(steps: List[str], current: int, completed: List[int] = None) -> None:
    completed = completed or []
    st.markdown("""
    <style>
    .progress-step { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
    .step-circle { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.8rem; flex-shrink: 0; }
    .step-line { flex: 1; height: 2px; margin-left: 14px; }
    </style>
    """, unsafe_allow_html=True)

    for i, step in enumerate(steps):
        is_completed = i in completed
        is_current = i == current
        is_future = i > current and not is_completed

        if is_completed:
            circle_color = UI_COLORS["success"]
            circle_text = "✓"
            line_color = UI_COLORS["success"]
        elif is_current:
            circle_color = UI_COLORS["primary"]
            circle_text = str(i + 1)
            line_color = UI_COLORS["card_border"]
        else:
            circle_color = UI_COLORS["card_border"]
            circle_text = str(i + 1)
            line_color = UI_COLORS["card_border"]

        st.markdown(f"""
        <div class="progress-step">
            <div class="step-circle" style="background: {circle_color}; color: {'white' if (is_completed or is_current) else UI_COLORS['text_secondary']};">
                {circle_text}
            </div>
            <span style="color: {UI_COLORS['primary'] if (is_completed or is_current) else 'var(--text-secondary)'}; font-weight: {'600' if (is_completed or is_current) else '400'};">
                {step}
            </span>
        </div>
        """.format(
            UI_COLORS["text_primary"],
            UI_COLORS["primary"],
            UI_COLORS["text_secondary"]
        ), unsafe_allow_html=True)

        if i < len(steps) - 1:
            st.markdown(f'<div class="step-line" style="background: {line_color};"></div>', unsafe_allow_html=True)
