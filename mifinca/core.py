"""Configuración, conexión y utilidades de datos."""
from __future__ import annotations

import os
import secrets
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import streamlit as st
from supabase import ClientOptions, create_client
from supabase_auth import SyncSupportedStorage


def setting(name: str) -> str:
    """Admite [supabase] en secrets.toml y el formato plano anterior."""
    if os.getenv(name):
        return os.environ[name]
    try:
        section = st.secrets["supabase"]
        aliases = {
            "SUPABASE_URL": ("url", "SUPABASE_URL"),
            "SUPABASE_PUBLISHABLE_KEY": ("key", "publishable_key", "SUPABASE_PUBLISHABLE_KEY"),
            "APP_URL": ("app_url", "APP_URL"),
        }
        for alias in aliases.get(name, (name,)):
            if section.get(alias):
                return str(section[alias])
    except (KeyError, FileNotFoundError):
        pass
    try:
        return str(st.secrets[name])
    except (KeyError, FileNotFoundError):
        return ""


class StreamlitSessionStorage(SyncSupportedStorage):
    """Sesión aislada por navegador, incluido el verificador OAuth PKCE."""

    def get_item(self, key: str) -> str | None:
        return st.session_state.get(f"supabase_{key}")

    def set_item(self, key: str, value: str) -> None:
        st.session_state[f"supabase_{key}"] = value

    def remove_item(self, key: str) -> None:
        st.session_state.pop(f"supabase_{key}", None)


# Streamlit reinicia su Session State tras regresar de Google. PKCE necesita
# conservar el code verifier durante esos pocos minutos, por lo que cada flujo
# se guarda temporalmente en memoria del proceso y se identifica en la URL.
_OAUTH_FLOW_STORAGE: dict[str, dict[str, str]] = {}


class OAuthFlowStorage(SyncSupportedStorage):
    def __init__(self, flow_id: str) -> None:
        self.flow_id = flow_id
        _OAUTH_FLOW_STORAGE.setdefault(flow_id, {})

    def get_item(self, key: str) -> str | None:
        return _OAUTH_FLOW_STORAGE[self.flow_id].get(key)

    def set_item(self, key: str, value: str) -> None:
        _OAUTH_FLOW_STORAGE[self.flow_id][key] = value

    def remove_item(self, key: str) -> None:
        _OAUTH_FLOW_STORAGE.get(self.flow_id, {}).pop(key, None)


def oauth_redirect_url(flow_id: str) -> str:
    parts = urlsplit(setting("APP_URL"))
    query = dict(parse_qsl(parts.query))
    query["mf_flow"] = flow_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def create_oauth_flow() -> tuple[str, str]:
    flow_id = secrets.token_urlsafe(24)
    return flow_id, oauth_redirect_url(flow_id)


def configured() -> bool:
    return bool(setting("SUPABASE_URL") and setting("SUPABASE_PUBLISHABLE_KEY") and setting("APP_URL"))


def db(flow_id: str | None = None):
    return create_client(
        setting("SUPABASE_URL"),
        setting("SUPABASE_PUBLISHABLE_KEY"),
        options=ClientOptions(
            storage=OAuthFlowStorage(flow_id) if flow_id else StreamlitSessionStorage(),
            flow_type="pkce",
        ),
    )


def rows(response: Any) -> list[dict[str, Any]]:
    return response.data or []


def get_rows(client: Any, table: str, order: str = "created_at", ascending: bool = False) -> list[dict[str, Any]]:
    return rows(client.table(table).select("*").order(order, desc=not ascending).execute())


def lookup(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["id"]): row for row in records}
