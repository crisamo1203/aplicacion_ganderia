from enum import Enum
from typing import Final, List, Dict, Any


class ClaseAnimal(str, Enum):
    BOVINO = "Bovino"
    AVICOLA = "Avícola"

    @classmethod
    def opciones(cls) -> List[str]:
        return [c.value for c in cls]


class SexoAnimal(str, Enum):
    HEMBRA = "Hembra"
    MACHO = "Macho"
    NO_APLICA = "No aplica"

    @classmethod
    def opciones(cls) -> List[str]:
        return [s.value for s in cls]


class EstadoAnimal(str, Enum):
    ACTIVO = "Activo"
    VENDIDO = "Vendido"
    FALLECIDO = "Fallecido"
    TRASLADADO = "Trasladado"
    EN_CEBA = "En Ceba"

    @classmethod
    def opciones(cls) -> List[str]:
        return [e.value for e in cls]

    @classmethod
    def color(cls, estado: str) -> str:
        colores = {
            "Activo": "green",
            "Vendido": "blue",
            "Fallecido": "red",
            "Trasladado": "orange",
            "En Ceba": "purple",
        }
        return colores.get(estado, "gray")


class TipoAnimal(str, Enum):
    INDIVIDUAL = "Individual"
    LOTE = "Lote"

    @classmethod
    def opciones(cls) -> List[str]:
        return [t.value for t in cls]


class PropositoAnimal(str, Enum):
    CARNE = "Carne"
    LECHE = "Leche"
    DOBLE_PROPOSITO = "Doble Propósito"
    REPRODUCCION = "Reproducción"
    HUEVOS = "Huevos"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [p.value for p in cls]


class EspecieAnimal(str, Enum):
    BOVINO = "Bovino"
    PORCINO = "Porcino"
    OVINO = "Ovino"
    CAPRINO = "Caprino"
    AVICOLA = "Avícola"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [e.value for e in cls]


class OrigenAnimal(str, Enum):
    NACIMIENTO_FINCA = "Nacimiento en Finca"
    COMPRA = "Compra"
    DONACION = "Donación"
    TRASLADO = "Traslado"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [o.value for o in cls]


class TipoVenta(str, Enum):
    CARNE_LIBRA = "Carne Libra"
    CUBETA = "Cubeta"
    LECHE = "Leche"
    ANIMAL = "Animal"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [t.value for t in cls]


class MetodoPago(str, Enum):
    EFECTIVO = "Efectivo"
    DEBE = "Debe"
    TRANSFERENCIA = "Transferencia"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [m.value for m in cls]


class TipoMovimiento(str, Enum):
    NACIMIENTO_FINCA = "Nacimiento en Finca"
    MARCACION = "Marcación"
    MOVIMIENTO = "Movimiento"
    VENTA = "Venta"
    INGRESO = "Ingreso"
    SALIDA = "Salida"
    FALLECIMIENTO = "Fallecimiento"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [t.value for t in cls]


class ProcedimientoSalud(str, Enum):
    VACUNACION = "Vacunación"
    PURGAS = "Purgas"
    MARCACION = "Marcación"
    DESPARASITACION = "Desparasitación"
    TRATAMIENTO = "Tratamiento"
    REVISION = "Revisión"
    OTRO = "Otro"

    @classmethod
    def opciones(cls) -> List[str]:
        return [p.value for p in cls]

    @classmethod
    def requiere_proxima_cita(cls, tipo: str) -> bool:
        return tipo in [
            cls.VACUNACION.value,
            cls.DESPARASITACION.value,
            cls.TRATAMIENTO.value,
        ]


class RolUsuario(str, Enum):
    ADMIN = "admin"
    GERENCIA = "gerencia"
    ENCARGADO = "encargado"
    COLABORADOR = "colaborador"
    OPERARIO = "operario"

    @classmethod
    def opciones(cls) -> List[str]:
        return [r.value for r in cls]

    @classmethod
    def jerarquia(cls) -> Dict[str, int]:
        return {
            cls.ADMIN.value: 4,
            cls.GERENCIA.value: 3,
            cls.ENCARGADO.value: 2,
            cls.COLABORADOR.value: 1,
            cls.OPERARIO.value: 1,
        }

    @classmethod
    def puede_editar(cls, rol: str) -> bool:
        return rol in [cls.ADMIN.value, cls.GERENCIA.value, cls.ENCARGADO.value]

    @classmethod
    def es_admin(cls, rol: str) -> bool:
        return rol in [cls.ADMIN.value, cls.GERENCIA.value]

    @classmethod
    def puede_gestionar_usuarios(cls, rol: str) -> bool:
        return rol in [cls.ADMIN.value]


class PrediosFijos(str, Enum):
    GUAKPA = "Guakpa"
    MONTERREDONDO = "Monterredondo"
    SAN_JOSE = "San Jose"
    SAN_MIGUEL = "San Miguel"

    @classmethod
    def opciones(cls) -> List[str]:
        return [p.value for p in cls]

    @classmethod
    def colores(cls) -> Dict[str, str]:
        return {
            cls.GUAKPA.value: "#2E7D32",
            cls.MONTERREDONDO.value: "#1565C0",
            cls.SAN_JOSE.value: "#F9A825",
            cls.SAN_MIGUEL.value: "#C62828",
        }


class PropietariosConocidos(str, Enum):
    CRISTIAN_ARCINIEGAS = "Cristian Arciniegas"
    DANIEL_ARCINIEGAS = "Daniel Arciniegas"
    ELSA_TIQUE = "Elsa Tique"
    FINCA_MONTERREDONDO = "Finca Monterredondo"

    @classmethod
    def opciones(cls) -> List[str]:
        return [p.value for p in cls]


class GrupoUsuario(str, Enum):
    ADMINISTRACION = "Administración"
    OPERACIONES = "Operaciones"
    VETERINARIA = "Veterinaria"
    INVERSIONISTAS = "Inversionistas"
    FAMILIA = "Familia"

    @classmethod
    def opciones(cls) -> List[str]:
        return [g.value for g in cls]


PERMISSION_MATRIX: Final[Dict[str, Dict[str, List[str]]]] = {
    "dashboard": {
        "admin": ["read"],
        "gerencia": ["read"],
        "encargado": ["read"],
        "colaborador": ["read"],
    },
    "inventario": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "ventas": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "produccion": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "ceba": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "historial": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "administracion": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["read"],
        "colaborador": [],
    },
    "salud": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read", "update", "delete"],
        "encargado": ["create", "read", "update"],
        "colaborador": ["read"],
    },
    "usuarios": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["read"],
        "encargado": [],
        "colaborador": [],
    },
    "feedback": {
        "admin": ["create", "read", "update", "delete"],
        "gerencia": ["create", "read"],
        "encargado": ["create", "read"],
        "colaborador": ["create", "read"],
    },
}

MODULE_LABELS: Final[Dict[str, str]] = {
    "dashboard": "Gerencia Dashboard",
    "inventario": "Inventario",
    "ventas": "Ventas",
    "produccion": "Producción",
    "ceba": "Ceba",
    "historial": "Historial",
    "administracion": "Administración",
    "salud": "Historial Médico",
    "usuarios": "Usuarios",
    "feedback": "Feedback / Soporte",
}

MODULE_ICONS: Final[Dict[str, str]] = {
    "dashboard": "📊",
    "inventario": "🐄",
    "ventas": "💰",
    "produccion": "🥚",
    "ceba": "⚖️",
    "historial": "📋",
    "administracion": "💸",
    "salud": "🏥",
    "usuarios": "👥",
    "feedback": "📬",
}

NAVIGATION_ORDER: Final[List[str]] = [
    "dashboard",
    "inventario",
    "ventas",
    "produccion",
    "ceba",
    "historial",
    "administracion",
    "salud",
    "usuarios",
    "feedback",
]

TABLE_NAMES: Final[Dict[str, str]] = {
    "animales": "animales",
    "ventas": "ventas",
    "produccion": "produccion",
    "pesajes": "pesajes",
    "movimientos": "movimientos",
    "gastos": "gastos",
    "salud": "salud",
    "profiles": "profiles",
    "predios": "predios",
    "lotes": "lotes",
    "feedback": "feedback",
}

CACHE_TTL_SECONDS: Final[int] = 300
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 200

DATE_FORMAT: Final[str] = "%Y-%m-%d"
DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
DISPLAY_DATE_FORMAT: Final[str] = "%d/%m/%Y"
DISPLAY_DATETIME_FORMAT: Final[str] = "%d/%m/%Y %H:%M"

ALERT_THRESHOLDS: Final[Dict[str, Any]] = {
    "pesaje_vencido_dias": 30,
    "produccion_avicola_dias": 7,
    "gasto_sin_comprobante_valor": 100000,
    "alerta_critica_dias": 7,
    "alerta_advertencia_dias": 30,
}

UI_COLORS: Final[Dict[str, str]] = {
    "primary": "#1B5E20",
    "primary_light": "#2E7D32",
    "secondary": "#0D47A1",
    "accent": "#FF6F00",
    "success": "#2E7D32",
    "warning": "#F9A825",
    "error": "#C62828",
    "info": "#0288D1",
    "background": "#F1F8E9",
    "sidebar_bg": "linear-gradient(180deg, #12351d, #1d5c30)",
    "card_bg": "#FFFFFF",
    "card_border": "#D9E5DB",
    "text_primary": "#1A1A1A",
    "text_secondary": "#68756D",
}

CHART_COLORS: Final[Dict[str, List[str]]] = {
    "clase": ["#2E7D32", "#F9A825"],
    "predios": ["#2E7D32", "#1565C0", "#F9A825", "#C62828"],
    "default": ["#1B5E20", "#2E7D32", "#4CAF50", "#81C784", "#A5D6A7"],
}

MENSAJES: Final[Dict[str, str]] = {
    "login_exitoso": "Inicio de sesión correcto. Bienvenido a MyFinca_Pro.",
    "login_fallido": "Credenciales incorrectas. Verifica tu correo y contraseña.",
    "logout_exitoso": "Sesión cerrada correctamente.",
    "sin_permisos": "No tienes permisos para acceder a este módulo.",
    "guardado_exitoso": "Registro guardado correctamente.",
    "actualizado_exitoso": "Registro actualizado correctamente.",
    "eliminado_exitoso": "Registro eliminado correctamente.",
    "error_guardar": "Error al guardar: {error}",
    "error_actualizar": "Error al actualizar: {error}",
    "error_eliminar": "Error al eliminar: {error}",
    "error_conexion": "Error de conexión con la base de datos.",
    "no_hay_datos": "No hay registros disponibles.",
    "campo_requerido": "El campo {campo} es obligatorio.",
    "confirmar_eliminar": "¿Estás seguro de eliminar este registro? Esta acción no se puede deshacer.",
    "animal_sin_pesaje": "Animal sin pesaje reciente (>30 días)",
    "vacuna_vencida": "Vacuna/desparasitación vencida",
    "produccion_pendiente": "Producción pendiente de registro",
    "gasto_sin_comprobante": "Gasto sin comprobante adjunto",
}
