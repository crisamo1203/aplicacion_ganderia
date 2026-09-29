import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict, Any
from config.constants import CHART_COLORS, UI_COLORS, PrediosFijos


def _apply_theme(fig: go.Figure) -> go.Figure:
    dark = bool(st.session_state.get("dark_mode", False))
    surface = "#1e232a" if dark else "#ffffff"
    ink = "#edf4ee" if dark else "#1a1a1a"
    muted = "#b7c7bb" if dark else UI_COLORS["text_secondary"]
    grid = "#34463a" if dark else "#e8ecef"
    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        plot_bgcolor=surface,
        paper_bgcolor=surface,
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color=ink),
        margin=dict(l=20, r=20, t=40, b=20),
        hoverlabel=dict(bgcolor=surface, bordercolor=grid, font=dict(color=ink, size=12, family="Inter")),
        xaxis=dict(showgrid=True, gridcolor=grid, zeroline=False, showline=True, linecolor=grid),
        yaxis=dict(showgrid=True, gridcolor=grid, zeroline=False, showline=True, linecolor=grid),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color=muted)),
    )
    return fig


def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: Optional[str] = None,
    color_map: Optional[Dict[str, str]] = None,
    text_auto: bool = True,
    orientation: str = "v",
    height: int = 350
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=UI_COLORS["text_secondary"])
        )
        return _apply_theme(fig)

    if orientation == "h":
        fig = px.bar(df, y=x, x=y, orientation="h", title=title, text_auto=text_auto, color=color, color_discrete_map=color_map)
    else:
        fig = px.bar(df, x=x, y=y, title=title, text_auto=text_auto, color=color, color_discrete_map=color_map)

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=11),
        hovertemplate="<b>%{x}</b><br>%{y} animales<extra></extra>" if orientation == "v"
        else "<b>%{y}</b><br>%{x} animales<extra></extra>"
    )

    if orientation == "h":
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))

    return _apply_theme(fig)


def create_pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str,
    hole: float = 0.45,
    height: int = 350
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=UI_COLORS["text_secondary"])
        )
        return _apply_theme(fig)

    fig = px.pie(df, names=names, values=values, title=title, hole=hole,
                 color_discrete_sequence=CHART_COLORS.get("clase", CHART_COLORS["default"]))

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>%{value} animales (%{percent})<extra></extra>",
        pull=[0.02] * len(df)
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
    )

    return _apply_theme(fig)


def create_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    markers: bool = True,
    color: Optional[str] = None,
    height: int = 350,
    show_trend: bool = False,
    trend_window: int = 7
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=UI_COLORS["text_secondary"])
        )
        return _apply_theme(fig)

    fig = px.line(df, x=x, y=y, title=title, markers=markers, color=color,
                  color_discrete_sequence=[UI_COLORS["primary"]])

    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>%{y} huevos<extra></extra>"
    )

    if show_trend and len(df) >= trend_window:
        df_sorted = df.sort_values(x)
        df_sorted["trend"] = df_sorted[y].rolling(window=trend_window, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df_sorted[x],
            y=df_sorted["trend"],
            mode="lines",
            name=f"Tendencia ({trend_window}d)",
            line=dict(color=UI_COLORS["accent"], width=2, dash="dot"),
            hovertemplate="Tendencia: %{y:.0f}<extra></extra>"
        ))

    fig.update_xaxes(tickformat="%d/%m")
    fig.update_yaxes(rangemode="tozero")

    return _apply_theme(fig)


def create_grouped_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: str,
    barmode: str = "group",
    height: int = 350
) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=UI_COLORS["text_secondary"])
        )
        return _apply_theme(fig)

    fig = px.bar(df, x=x, y=y, color=color, title=title, barmode=barmode,
                 color_discrete_sequence=CHART_COLORS["default"])

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="<b>%{x}</b><br>%{legendgroup}: %{y}<extra></extra>"
    )

    return _apply_theme(fig)


def create_dashboard_animales_por_propietario(df: pd.DataFrame) -> go.Figure:
    return create_bar_chart(
        df, x="propietario", y="total",
        title="Animales por Propietario",
        orientation="h",
        color="propietario",
        height=350
    )


def create_dashboard_animales_por_predio(df: pd.DataFrame) -> go.Figure:
    color_map = PrediosFijos.colores()
    return create_bar_chart(
        df, x="predio", y="total",
        title="Animales por Predio",
        color="predio",
        color_map=color_map,
        height=350
    )


def create_dashboard_clase_distribucion(bovinos: int, avicolas: int) -> go.Figure:
    df = pd.DataFrame({
        "Clase": ["Bovino", "Avícola"],
        "Total": [bovinos, avicolas]
    })
    return create_pie_chart(df, names="Clase", values="Total", title="Distribución por Clase", hole=0.5)


def create_dashboard_produccion_huevos(df: pd.DataFrame) -> go.Figure:
    return create_line_chart(
        df, x="fecha", y="cantidad_huevos",
        title="Producción de Huevos (Últimos 30 días)",
        markers=True,
        show_trend=True,
        height=350
    )


def create_ventas_mensuales(df: pd.DataFrame) -> go.Figure:
    if df.empty or "fecha" not in df.columns or "valor_total" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos de ventas", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    mensual = df.groupby("mes")["valor_total"].sum().reset_index()

    return create_bar_chart(
        mensual, x="mes", y="valor_total",
        title="Ventas por Mes",
        text_auto=".2s",
        height=350
    )


def create_produccion_por_predio(df: pd.DataFrame) -> go.Figure:
    if df.empty or "predio" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No hay datos", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    df = df.copy()
    metricas = []
    if "litros_leche" in df.columns:
        metricas.append("litros_leche")
    if "cantidad_huevos" in df.columns:
        metricas.append("cantidad_huevos")

    if not metricas:
        fig = go.Figure()
        fig.add_annotation(text="No hay métricas de producción", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    agg = df.groupby("predio")[metricas].sum().reset_index()
    agg = agg.melt(id_vars="predio", var_name="tipo", value_name="total")

    return create_grouped_bar_chart(
        agg, x="predio", y="total", color="tipo",
        title="Producción por Predio",
        height=350
    )


def create_pesaje_evolucion(df: pd.DataFrame, animal_id: str) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin historial de pesajes", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.sort_values("fecha")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"],
        y=df["peso_kg"],
        mode="lines+markers",
        name="Peso (kg)",
        line=dict(color=UI_COLORS["primary"], width=3),
        marker=dict(size=10),
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Peso: %{y} kg<extra></extra>"
    ))

    if len(df) > 1:
        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=df["peso_kg"].rolling(window=2, min_periods=1).mean(),
            mode="lines",
            name="Tendencia",
            line=dict(color=UI_COLORS["accent"], width=2, dash="dot"),
            hovertemplate="Tendencia: %{y:.1f} kg<extra></extra>"
        ))

    return _apply_theme(fig)


def create_salud_calendario(df: pd.DataFrame) -> go.Figure:
    if df.empty or "proxima_cita" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Sin citas programadas", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    df = df.copy()
    df["proxima_cita"] = pd.to_datetime(df["proxima_cita"], errors="coerce")
    df = df.dropna(subset=["proxima_cita"])
    df = df[df["proxima_cita"] >= pd.Timestamp.now()]
    df = df.sort_values("proxima_cita").head(20)

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin citas próximas", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return _apply_theme(fig)

    fig = px.timeline(
        df,
        x_start="proxima_cita",
        x_end="proxima_cita",
        y="animal_id" if "animal_id" in df.columns else "tipo_procedimiento",
        color="tipo_procedimiento",
        title="Próximas Citas Sanitarias",
        color_discrete_sequence=CHART_COLORS["default"]
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickformat="%d/%m")

    return _apply_theme(fig)
