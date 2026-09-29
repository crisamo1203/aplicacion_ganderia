import streamlit as st
import pandas as pd
from datetime import date
from typing import Optional, Dict, Any, List, Callable
from utils.data import (
    insert_record, update_record, delete_record,
    get_animal_by_id, get_animal_pesajes, get_animal_salud, get_animal_movimientos
)
from components.forms import (
    render_form_dialog, render_confirm_dialog,
    get_animal_form_fields, get_venta_form_fields,
    get_produccion_form_fields, get_pesaje_form_fields,
    get_movimiento_form_fields, get_gasto_form_fields,
    get_salud_form_fields, get_profile_form_fields
)
from utils.validators import (
    AnimalCreate, AnimalUpdate, VentaCreate, VentaUpdate,
    ProduccionCreate, ProduccionUpdate, PesajeCreate, PesajeUpdate,
    MovimientoCreate, MovimientoUpdate, GastoCreate, GastoUpdate,
    SaludCreate, SaludUpdate, ProfileUpdate
)
from utils.data import TABLE_NAMES
from config.constants import MENSAJES
from components.ui import render_toast_success, render_toast_error


def animal_dialog(
    mode: str = "create",
    animal_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    if mode != "create" and not (animal_data and animal_data.get("id")):
        render_toast_error("No se pudo editar el animal: falta su identificador.")
        return None
    animal_data = animal_data or {}
    title = "➕ Nuevo Animal" if mode == "create" else f"✏️ Editar: {animal_data.get('arete', 'Animal')}"
    if animal_data and "observaciones" not in animal_data and "comentarios" in animal_data:
        animal_data = {**animal_data, "observaciones": animal_data.get("comentarios")}
    fields = get_animal_form_fields()
    validator = AnimalCreate if mode == "create" else AnimalUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if "observaciones" in data:
            data["comentarios"] = data.pop("observaciones")
        if mode == "create":
            success = insert_record(TABLE_NAMES["animales"], data)
        else:
            success = update_record(TABLE_NAMES["animales"], animal_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Animal", animal_data, validator, submit, f"animal_{mode}")


def venta_dialog(
    mode: str = "create",
    venta_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nueva Venta" if mode == "create" else f"✏️ Editar Venta"
    fields = get_venta_form_fields()
    validator = VentaCreate if mode == "create" else VentaUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        data["valor_total"] = round(float(data.get("cantidad", 0)) * float(data.get("valor_unitario", 0)), 2)
        if "metodo_pago" in data:
            data["metodo"] = data.pop("metodo_pago")
        if mode == "create":
            success = insert_record(TABLE_NAMES["ventas"], data)
        else:
            success = update_record(TABLE_NAMES["ventas"], venta_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Venta", venta_data, validator, submit, f"venta_{mode}")


def produccion_dialog(
    mode: str = "create",
    prod_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nueva Producción" if mode == "create" else f"✏️ Editar Producción"
    fields = get_produccion_form_fields()
    validator = ProduccionCreate if mode == "create" else ProduccionUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if mode == "create":
            success = insert_record(TABLE_NAMES["produccion"], data)
        else:
            success = update_record(TABLE_NAMES["produccion"], prod_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Producción", prod_data, validator, submit, f"produccion_{mode}")


def pesaje_dialog(
    mode: str = "create",
    pesaje_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nuevo Pesaje" if mode == "create" else f"✏️ Editar Pesaje"
    fields = get_pesaje_form_fields()
    validator = PesajeCreate if mode == "create" else PesajeUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if mode == "create":
            success = insert_record(TABLE_NAMES["pesajes"], data)
        else:
            success = update_record(TABLE_NAMES["pesajes"], pesaje_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Pesaje", pesaje_data, validator, submit, f"pesaje_{mode}")


def movimiento_dialog(
    mode: str = "create",
    mov_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nuevo Movimiento" if mode == "create" else f"✏️ Editar Movimiento"
    fields = get_movimiento_form_fields()
    validator = MovimientoCreate if mode == "create" else MovimientoUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if mode == "create":
            success = insert_record(TABLE_NAMES["movimientos"], data)
        else:
            success = update_record(TABLE_NAMES["movimientos"], mov_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Movimiento", mov_data, validator, submit, f"movimiento_{mode}")


def gasto_dialog(
    mode: str = "create",
    gasto_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nuevo Gasto" if mode == "create" else f"✏️ Editar Gasto"
    fields = get_gasto_form_fields()
    validator = GastoCreate if mode == "create" else GastoUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if "metodo_pago" in data:
            data["metodo"] = data.pop("metodo_pago")
        if mode == "create":
            success = insert_record(TABLE_NAMES["gastos"], data)
        else:
            success = update_record(TABLE_NAMES["gastos"], gasto_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Gasto", gasto_data, validator, submit, f"gasto_{mode}")


def salud_dialog(
    mode: str = "create",
    salud_data: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "➕ Nuevo Procedimiento" if mode == "create" else f"✏️ Editar Procedimiento"
    fields = get_salud_form_fields()
    validator = SaludCreate if mode == "create" else SaludUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        if mode == "create":
            success = insert_record(TABLE_NAMES["salud"], data)
        else:
            success = update_record(TABLE_NAMES["salud"], salud_data["id"], data)
        if success:
            render_toast_success(MENSAJES["guardado_exitoso"])
            if on_success:
                on_success()
        return success

    return render_form_dialog(title, fields, "Guardar Procedimiento", salud_data, validator, submit, f"salud_{mode}")


def perfil_dialog(
    profile_data: Dict[str, Any],
    on_success: Optional[Callable] = None
) -> Optional[Dict[str, Any]]:
    title = "✏️ Editar Perfil"
    fields = get_profile_form_fields()
    validator = ProfileUpdate

    def submit(data):
        data = {k: v for k, v in data.items() if v not in (None, "", [])}
        from config.supabase_client import get_client
        try:
            client = get_client()
            client.table(TABLE_NAMES["profiles"]).update(data).eq("id", profile_data["id"]).execute()
            render_toast_success(MENSAJES["actualizado_exitoso"])
            if on_success:
                on_success()
            return True
        except Exception as e:
            render_toast_error(str(e))
            return False

    return render_form_dialog(title, fields, "Guardar Cambios", profile_data, validator, submit, "perfil_edit")





def delete_confirm_dialog(
    title: str,
    message: str,
    on_confirm: Callable,
    key: str = "delete_confirm"
) -> bool:
    return render_confirm_dialog(
        title=f"🗑️ {title}",
        message=message,
        confirm_label="Eliminar",
        cancel_label="Cancelar",
        key=key,
        type="primary"
    )


def google_oauth_dialog() -> None:
    @st.dialog("🔐 Iniciar sesión con Google")
    def _dialog():
        st.write("Serás redirigido a Google para autorizar el acceso.")
        st.caption("Tu correo se usará para crear o vincular tu perfil en MyFinca_Pro.")
        c1, c2 = st.columns(2)
        with c1:
            from modules.auth import login_with_google
            auth_url = login_with_google()
            if auth_url:
                st.link_button(
                    "Continuar con Google",
                    auth_url,
                    type="primary",
                    use_container_width=True,
                )
        with c2:
            if st.button("Cancelar", use_container_width=True):
                st.rerun()

    _dialog()


def export_dialog(df: pd.DataFrame, filename: str) -> None:
    @st.dialog(f"📥 Exportar {filename}")
    def _dialog():
        st.write(f"Se exportarán {len(df)} registros.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📊 CSV", use_container_width=True):
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar CSV",
                    csv,
                    f"{filename}.csv",
                    "text/csv",
                    use_container_width=True
                )
        with c2:
            if st.button("📈 Excel", use_container_width=True):
                from io import BytesIO
                buffer = BytesIO()
                df.to_excel(buffer, index=False)
                st.download_button(
                    "Descargar Excel",
                    buffer.getvalue(),
                    f"{filename}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    _dialog()
