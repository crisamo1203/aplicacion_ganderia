import streamlit as st
import pandas as pd
from utils.data import get_animales, insert_record, update_record, delete_record, TABLE_NAMES
from components.dialogs import animal_dialog
from components.ui import (
    render_page_header, render_section_header, render_empty_state,
    render_badge, render_estado_animal, render_toast_success, render_toast_error,
    render_divider
)
from config.constants import (
    PropietariosConocidos, PrediosFijos, EstadoAnimal, ClaseAnimal,
    PropositoAnimal, EspecieAnimal, OrigenAnimal, SexoAnimal,
    MENSAJES
)
from components.forms import get_animal_form_fields
from utils.validators import AnimalCreate, AnimalUpdate, validate_form


PROPIETARIO_ORDEN = [
    "Cristian Arciniegas",
    "Daniel Arciniegas",
    "Elsa Tique",
    "Rosario Tique",
    "Hugo Arciniegas",
    "Elizabeth Mora",
    "Finca Monterredondo",
]

# Mapeo de iconos por especie
ESPECIE_ICONOS = {
    "Vaca": "🐄",
    "Toro": "🐂",
    "Buey": "🐃",
    "Caballo": "🐴",
    "Yegua": "🐴",
    "Potro": "🐎",
    "Cerdo": "🐷",
    "Cerda": "🐷",
    "Lechón": "🐖",
    "Cabra": "🐐",
    "Chivo": "🐐",
    "Oveja": "🐑",
    "Carnero": "🐏",
    "Cordero": "🐑",
    "Gallina": "🐔",
    "Gallo": "🐓",
    "Pollo": "🐤",
    "Pavo": "🦃",
    "Pato": "🦆",
    "Conejo": "🐰",
    "Bufalo": "🐃",
    "Búfalo": "🐃",
    "Búfala": "🐃",
    "Equino": "🐴",
    "Porcino": "🐷",
    "Ovino": "🐑",
    "Caprino": "🐐",
    "Avícola": "🐔",
    "Bovino": "🐄",
}


def get_especie_icon(especie: str, clase: str = "") -> str:
    """Obtiene el icono apropiado para la especie/clase"""
    if not especie or especie == "NaN":
        if clase == "Bovino":
            return "🐄"
        elif clase == "Avícola":
            return "🐔"
        elif clase == "Porcino":
            return "🐷"
        elif clase == "Ovino":
            return "🐑"
        elif clase == "Caprino":
            return "🐐"
        elif clase == "Equino":
            return "🐴"
        return "🐄"
    return ESPECIE_ICONOS.get(especie, "🐄")


def get_clase_color(clase: str) -> str:
    """Color según la clase"""
    colores = {
        "Bovino": "#2E7D32",
        "Avícola": "#F9A825",
        "Porcino": "#E91E63",
        "Ovino": "#3F51B5",
        "Caprino": "#FF9800",
        "Equino": "#795548",
        "Bufalino": "#607D8B",
    }
    return colores.get(clase, "#666")


def get_especie_fields(especie: str) -> dict:
    """Retorna campos específicos según la especie"""
    especie_lower = especie.lower() if especie else ""
    
    campos_especificos = {
        "Vaca": {"propositos": ["Leche", "Ceba", "Cria"], "requiere_ordeño": True},
        "Toro": {"propositos": ["Cria", "Ceba"], "requiere_ordeño": False},
        "Buey": {"propositos": ["Trabajo", "Ceba"], "requiere_ordeño": False},
        "Caballo": {"propositos": ["Deporte", "Trabajo", "Cria"], "requiere_herrado": True},
        "Yegua": {"propositos": ["Cria", "Deporte"], "requiere_herrado": True},
        "Cerdo": {"propositos": ["Ceba", "Cria"], "requiere_ordeño": False},
        "Cerda": {"propositos": ["Cria", "Ceba"], "requiere_ordeño": False},
        "Cabra": {"propositos": ["Leche", "Ceba", "Cria"], "requiere_ordeño": True},
        "Chivo": {"propositos": ["Cria", "Ceba"], "requiere_ordeño": False},
        "Oveja": {"propositos": ["Lana", "Ceba", "Cria", "Leche"], "requiere_esquila": True},
        "Gallina": {"propositos": ["Huevos", "Ceba"], "requiere_nido": True},
        "Gallo": {"propositos": ["Cria"], "requiere_ordeño": False},
        "Pato": {"propositos": ["Huevos", "Ceba"], "requiere_agua": True},
        "Búfalo": {"propositos": ["Leche", "Ceba", "Trabajo"], "requiere_ordeño": True},
        "Búfala": {"propositos": ["Leche", "Ceba", "Cria"], "requiere_ordeño": True},
    }
    
    return campos_especificos.get(especie, {"propositos": ["Ceba", "Cria", "Leche", "Huevos", "Otro"]})


def render_inventario() -> None:
    if not st.session_state.get("user"):
        return

    render_page_header(
        "Inventario",
        "Animales registrados agrupados por propietario y finca",
        "🐄"
    )

    render_toolbar()

    animales = get_animales()

    if animales.empty:
        render_empty_state(
            "🐄", "Sin animales registrados",
            "No hay animales en el inventario. Agrega el primero para comenzar.",
            "➕ Agregar Animal", lambda: animal_dialog("create")
        )
        return

    render_grouped_inventory(animales)


def render_toolbar() -> None:
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

    with c1:
        search = st.text_input(
            "🔍 Buscar",
            placeholder="Buscar por arete, nombre, raza, especie...",
            key="inventario_search",
            label_visibility="collapsed"
        )

    with c2:
        if st.button("➕ Nuevo Animal", type="primary", use_container_width=True):
            animal_dialog("create")

    with c3:
        if st.button("📥 Exportar", use_container_width=True):
            from components.dialogs import export_dialog
            export_dialog(get_animales(), "inventario_animales")

    with c4:
        # Filtro rápido por clase
        st.selectbox(
            "Clase",
            ["Todas", "Bovino", "Avícola", "Porcino", "Ovino", "Caprino", "Equino", "Bufalino"],
            key="inventario_clase_filter",
            label_visibility="collapsed"
        )


def render_grouped_inventory(df: pd.DataFrame) -> None:
    search = st.session_state.get("inventario_search", "").lower().strip()
    clase_filter = st.session_state.get("inventario_clase_filter", "Todas")

    # Ensure required columns exist
    required_cols = [
        "nombre", "arete", "raza", "propietario", "predio", "clase", "estado",
        "especie", "proposito", "sexo", "fecha_nacimiento", "peso_kg", "color",
        "marca", "origen", "proveedor", "valor_compra", "valor_venta", "comentarios",
        "tipo", "ubicacion_actual", "edad", "foto"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # Filtro búsqueda
    if search:
        mask = (
            df["nombre"].astype(str).str.lower().str.contains(search) |
            df["arete"].astype(str).str.lower().str.contains(search) |
            df["raza"].astype(str).str.lower().str.contains(search) |
            df["especie"].astype(str).str.lower().str.contains(search) |
            df["propietario"].astype(str).str.lower().str.contains(search) |
            df["predio"].astype(str).str.lower().str.contains(search) |
            df["marca"].astype(str).str.lower().str.contains(search)
        )
        df = df[mask]

    # Filtro clase
    if clase_filter != "Todas":
        df = df[df["clase"] == clase_filter]

    if df.empty:
        render_empty_state("🔍", "Sin resultados", "No se encontraron animales con ese criterio.")
        return

    df = df.copy()
    df["propietario"] = df["propietario"].fillna("Sin propietario")
    df["predio"] = df["predio"].fillna("Sin predio")
    df["especie"] = df["especie"].fillna("")
    df["proposito"] = df["proposito"].fillna("")
    df["raza"] = df["raza"].fillna("")

    propietarios = sorted(
        df["propietario"].unique(),
        key=lambda x: PROPIETARIO_ORDEN.index(x) if x in PROPIETARIO_ORDEN else 999
    )

    for propietario in propietarios:
        prop_df = df[df["propietario"] == propietario]
        count = len(prop_df)

        with st.expander(f"👤 **{propietario}** ({count} animales)", expanded=True):
            predios = sorted(
                prop_df["predio"].unique(),
                key=lambda x: PrediosFijos.opciones().index(x) if x in PrediosFijos.opciones() else 999
            )

            for predio in predios:
                predio_df = prop_df[prop_df["predio"] == predio]
                pcount = len(predio_df)

                predio_color = PrediosFijos.colores().get(predio, "#666")

                st.markdown(f"""
                <div style="margin: 0.5rem 0; padding: 0.5rem; background: {predio_color}15; border-left: 4px solid {predio_color}; border-radius: 4px;">
                    <strong style="color: {predio_color};">🏞️ {predio}</strong> — {pcount} animal{'es' if pcount != 1 else ''}
                </div>
                """, unsafe_allow_html=True)

                render_animal_rows(predio_df)


def render_animal_rows(df: pd.DataFrame) -> None:
    df = df.sort_values(["clase", "especie", "arete"])

    for _, animal in df.iterrows():
        render_animal_row(animal)


def render_animal_row(animal: pd.Series) -> None:
    arete = animal.get("arete", "S/A")
    nombre = animal.get("nombre", "Sin nombre")
    clase = animal.get("clase", "")
    especie = animal.get("especie", "")
    raza = animal.get("raza", "")
    proposito = animal.get("proposito", "")
    sexo = animal.get("sexo", "")
    edad = animal.get("edad_display", animal.get("edad", ""))
    estado = animal.get("estado", EstadoAnimal.ACTIVO.value)
    color = animal.get("color", "")
    peso = animal.get("peso_kg", animal.get("peso", ""))
    marca = animal.get("marca", "")
    ubicacion = animal.get("ubicacion_actual", animal.get("ubicacion", ""))
    animal_id = animal.get("id")

    # Icono según especie
    icono = get_especie_icon(especie, clase)
    clase_color = get_clase_color(clase)

    # Columnas: Foto/Icono, Nombre/Arete, Especie/Raza, Propósito/Sexo, Edad/Peso, Estado, Acciones
    c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 1.5, 1.5, 1, 1])

    with c1:
        # Foto o icono grande
        foto = animal.get("foto", "")
        if foto and isinstance(foto, str) and foto.strip():
            st.image(foto, width=50)
        else:
            st.markdown(f"<div style='font-size: 2.5rem; text-align: center;'>{get_especie_icon(especie, clase)}</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div>
            <strong style='color: var(--text);'>{nombre}</strong><br>
            <code style='font-size: 0.75rem;'>{arete}</code>
        </div>
        """, unsafe_allow_html=True)
        if marca:
            st.caption(f"Marca: {marca}")

    with c3:
        # Especie con icono + Raza
        st.markdown(f"""
        <div>
            <span style='color: {clase_color}; font-weight: 600;'>{get_especie_icon(especie, clase)} {especie or clase}</span><br>
            <small>{raza or '—'}</small>
        </div>
        """, unsafe_allow_html=True)
        if proposito:
            st.caption(f"🎯 {proposito}")
        if sexo:
            sexo_icon = "♂" if sexo == "Macho" else "♀" if sexo == "Hembra" else "⚥"
            st.caption(f"{sexo_icon} {sexo}")

    with c4:
        # Edad y Peso
        if edad:
            st.caption(f"📅 {edad}")
        if peso:
            st.caption(f"⚖️ {peso} kg")
        if color:
            st.markdown(f"""
            <span style='
                display: inline-block; width: 12px; height: 12px; 
                border-radius: 50%; background: {color}; 
                border: 1px solid #ccc; margin-right: 4px;'>
            </span> {color}
            """, unsafe_allow_html=True)

    with c5:
        # Ubicación y propietario
        if ubicacion:
            st.caption(f"📍 {ubicacion}")
        st.caption(f"👤 {animal.get('propietario', '—')}")

    with c6:
        render_estado_animal(estado)

    with c7:
        # Botones de acción compactos
        btn_cols = st.columns(3)
        with btn_cols[0]:
            if st.button("📋", key=f"hist_{animal_id}", help="Ver historial completo", use_container_width=True):
                show_animal_history(animal_id, nombre, arete)
        with btn_cols[1]:
            if st.button("⚖️", key=f"pesar_{animal_id}", help="Registrar pesaje", use_container_width=True):
                from components.dialogs import pesaje_dialog
                pesaje_dialog("create", {"animal_id": animal_id, "nota": f"Pesaje de {nombre} ({arete})"})
        with btn_cols[2]:
            if st.button("⋮", key=f"menu_{animal_id}", help="Más opciones", use_container_width=True):
                show_animal_menu(animal_id, animal.to_dict())

    # Línea separadora
    st.markdown("<hr style='margin: 0.25rem 0; border-color: var(--border); opacity: 0.5;'>", unsafe_allow_html=True)


def show_animal_menu(animal_id: str, animal_data: dict) -> None:
    """Menú contextual para el animal"""
    @st.dialog("Opciones del Animal")
    def _dialog():
        nombre = animal_data.get("nombre", "Sin nombre")
        arete = animal_data.get("arete", "S/A")
        st.write(f"**{nombre}** (`{arete}`)")
        st.divider()
        
        if st.button("✏️ Editar", use_container_width=True):
            animal_dialog("update", animal_data)
            st.rerun()
        
        if st.button("⚖️ Registrar Pesaje", use_container_width=True):
            from components.dialogs import pesaje_dialog
            pesaje_dialog("create", {"animal_id": animal_id, "nota": f"Pesaje de {nombre} ({arete})"})
            st.rerun()
        
        if st.button("🏥 Registrar Salud", use_container_width=True):
            from components.dialogs import salud_dialog
            salud_dialog("create", {"animal_id": animal_id})
            st.rerun()
        
        if st.button("📋 Registrar Movimiento", use_container_width=True):
            from components.dialogs import movimiento_dialog
            movimiento_dialog("create", {"animal_id": animal_id})
            st.rerun()
        
        if st.button("📋 Ver Historial Completo", use_container_width=True):
            show_animal_history(animal_id, nombre, arete)
        
        st.divider()
        
        if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
            if confirm_delete_animal(animal_id, nombre, arete):
                delete_record(TABLE_NAMES["animales"], animal_id)
                render_toast_success(MENSAJES["eliminado_exitoso"])
                st.rerun()

    _dialog()


def can_edit_inventario() -> bool:
    from modules.auth import can_edit
    return can_edit()


def show_animal_history(animal_id: str, nombre: str, arete: str) -> None:
    """Muestra el historial completo del animal en un diálogo con pestañas."""
    tab1, tab2, tab3 = st.tabs(["⚖️ Pesajes", "🏥 Salud", "📋 Movimientos"])

    with tab1:
        _render_pesajes_history(animal_id, f"{nombre} ({arete})")

    with tab2:
        _render_salud_history(animal_id, f"{nombre} ({arete})")

    with tab3:
        _render_movimientos_history(animal_id, f"{nombre} ({arete})")


def _render_pesajes_history(animal_id: str, animal_nombre: str) -> None:
    """Renderiza el historial de pesajes dentro de una pestaña (sin diálogo anidado)."""
    pesajes = get_animal_pesajes(animal_id)
    if pesajes.empty:
        st.info("No hay pesajes registrados para este animal.")
        return

    pesajes = pesajes.copy()
    pesajes["fecha"] = pd.to_datetime(pesajes["fecha"], errors="coerce")
    pesajes = pesajes.sort_values("fecha", ascending=False)

    st.dataframe(
        pesajes[["fecha", "peso_kg", "nota"]],
        column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "peso_kg": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
            "nota": "Nota",
        },
        use_container_width=True,
        hide_index=True
    )

    if len(pesajes) > 1:
        st.markdown("**Evolución:**")
        from components.charts import create_pesaje_evolucion
        fig = create_pesaje_evolucion(pesajes, animal_id)
        st.plotly_chart(fig, use_container_width=True, key=f"pesaje_evolucion_{animal_id}")


def _render_salud_history(animal_id: str, animal_nombre: str) -> None:
    """Renderiza el historial sanitario dentro de una pestaña (sin diálogo anidado)."""
    salud = get_animal_salud(animal_id)
    if salud.empty:
        st.info("No hay procedimientos registrados para este animal.")
        return

    salud = salud.copy()
    salud["fecha"] = pd.to_datetime(salud["fecha"], errors="coerce")
    salud["proxima_cita"] = pd.to_datetime(salud["proxima_cita"], errors="coerce")
    salud = salud.sort_values("fecha", ascending=False)

    st.dataframe(
        salud[["fecha", "tipo_procedimiento", "medicamento", "veterinario", "proxima_cita", "observaciones"]],
        column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "tipo_procedimiento": "Procedimiento",
            "medicamento": "Medicamento",
            "veterinario": "Veterinario",
            "proxima_cita": st.column_config.DateColumn("Próx. Cita", format="DD/MM/YYYY"),
            "observaciones": "Observaciones",
        },
        use_container_width=True,
        hide_index=True
    )


def _render_movimientos_history(animal_id: str, animal_nombre: str) -> None:
    """Renderiza el historial de movimientos dentro de una pestaña (sin diálogo anidado)."""
    movs = get_animal_movimientos(animal_id)
    if movs.empty:
        st.info("No hay movimientos registrados para este animal.")
        return

    movs = movs.copy()
    movs["fecha"] = pd.to_datetime(movs["fecha"], errors="coerce")
    movs = movs.sort_values("fecha", ascending=False)

    st.dataframe(
        movs[["fecha", "tipo_movimiento", "predio_origen", "predio_destino", "comentarios"]],
        column_config={
            "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
            "tipo_movimiento": "Tipo",
            "predio_origen": "Origen",
            "predio_destino": "Destino",
            "comentarios": "Comentarios",
        },
        use_container_width=True,
        hide_index=True
    )


def confirm_delete_animal(animal_id: str, nombre: str, arete: str) -> bool:
    from components.dialogs import render_confirm_dialog
    return render_confirm_dialog(
        "Eliminar Animal",
        f"¿Eliminar a **{nombre}** (Arete: {arete})?\n\nEsta acción no se puede deshacer.",
        confirm_label="Eliminar",
        cancel_label="Cancelar",
        key=f"del_animal_{animal_id}"
    )