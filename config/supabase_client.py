"""Cliente Supabase por sesión para la aplicación Streamlit MyFinca Pro.

Usa la API pública de supabase-py v2 y una caché resource cuya clave contiene
un identificador aleatorio por sesión de Streamlit. Así el SDK no comparte la
sesión Auth/JWT de una persona con otra dentro del mismo proceso.
"""
from __future__ import annotations

import logging
import secrets as python_secrets
from functools import wraps
from typing import Any, Callable, List, Optional, TypeVar
from urllib.parse import urlparse

import streamlit as st
from supabase import create_client, Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])
_SESSION_SCOPE_KEY = "_myfinca_supabase_session_scope"


class SupabaseClient:
    """Small compatibility wrapper used by existing application modules."""

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def execute_query(self, query_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return query_func(*args, **kwargs).execute()

    def get_user_predios(self, user_id: str) -> List[str]:
        try:
            response = self.client.rpc("get_user_predios", {"p_user_id": user_id}).execute()
            return [str(row["id"]) for row in (response.data or []) if row.get("id")]
        except Exception:
            logger.exception("Supabase RPC get_user_predios failed")
            return []

    def can_access_predio(self, user_id: str, predio_id: str) -> bool:
        try:
            response = self.client.rpc(
                "can_access_predio", {"p_user_id": user_id, "p_predio_id": predio_id}
            ).execute()
            return bool(response.data)
        except Exception:
            logger.exception("Supabase RPC can_access_predio failed")
            return False

    def can_access_animal(self, user_id: str, animal_id: str) -> bool:
        try:
            response = self.client.rpc(
                "can_access_animal", {"p_user_id": user_id, "p_animal_id": animal_id}
            ).execute()
            return bool(response.data)
        except Exception:
            logger.exception("Supabase RPC can_access_animal failed")
            return False

    def is_admin(self, user_id: str) -> bool:
        try:
            response = self.client.rpc("is_admin", {"p_user_id": user_id}).execute()
            return bool(response.data)
        except Exception:
            logger.exception("Supabase RPC is_admin failed")
            return False


def _read_supabase_settings() -> tuple[str, str]:
    """Read and validate URL/public key from Streamlit secrets without logging values."""
    try:
        settings = st.secrets.get("supabase", {})
    except Exception as exc:
        raise RuntimeError(
            "No se encontraron secretos de Supabase. Configura [supabase] en "
            ".streamlit/secrets.toml o en el panel de secretos del hosting."
        ) from exc

    url = str(settings.get("url", "")).strip()
    api_key = str(
        settings.get("publishable_key") or settings.get("anon_key") or settings.get("key") or ""
    ).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("Configura una URL de Supabase válida en [supabase].url.")
    if not api_key:
        raise ValueError(
            "Configura la publishable/anon key en [supabase].publishable_key "
            "(o la clave heredada en [supabase].key). No uses service_role."
        )
    return url, api_key


@st.cache_resource(max_entries=128, show_spinner=False)
def get_supabase_client(session_scope: str) -> SupabaseClient:
    """Read st.secrets and cache one auth-aware SDK client per browser session."""
    # The random scope is a cache discriminator; it is never sent to the API.
    del session_scope
    url, api_key = _read_supabase_settings()
    return SupabaseClient(create_client(url, api_key))


def _get_session_scope() -> str:
    session_scope = st.session_state.get(_SESSION_SCOPE_KEY)
    if not session_scope:
        session_scope = python_secrets.token_urlsafe(24)
        st.session_state[_SESSION_SCOPE_KEY] = session_scope
    return session_scope


def reset_client_session() -> None:
    """Rotate the client cache discriminator when the browser user logs out."""
    st.session_state.pop(_SESSION_SCOPE_KEY, None)


def get_client() -> Client:
    """Return a supabase-py v2 Client for the current Streamlit session."""
    return get_supabase_client(_get_session_scope()).client


def invalidate_cache() -> None:
    """Invalidate user-scoped data caches after a successful write or logout."""
    st.cache_data.clear()


def with_invalidation(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        invalidate_cache()
        return result

    return wrapper  # type: ignore[return-value]
