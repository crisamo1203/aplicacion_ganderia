from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime
from typing import Optional, List, Any
from config.constants import (
    ClaseAnimal, SexoAnimal, EstadoAnimal, TipoAnimal,
    PropositoAnimal, EspecieAnimal, OrigenAnimal,
    TipoVenta, MetodoPago, TipoMovimiento, ProcedimientoSalud,
    RolUsuario, ALERT_THRESHOLDS
)


class AnimalBase(BaseModel):
    lote_id: str = Field(..., description="Lote al que pertenece el animal")
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre o identificación del animal")
    arete: str = Field(..., min_length=1, max_length=50, description="Número de arete")
    clase: str = Field(..., description="Clase del animal")
    raza: Optional[str] = Field(None, max_length=100)
    propietario: Optional[str] = Field(None, max_length=100)
    predio: Optional[str] = Field(None, max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: str = Field(default=SexoAnimal.NO_APLICA.value)
    estado: str = Field(default=EstadoAnimal.ACTIVO.value)
    tipo: str = Field(default=TipoAnimal.INDIVIDUAL.value)
    proposito: Optional[str] = None
    especie: Optional[str] = None
    origen: Optional[str] = None
    proveedor: Optional[str] = Field(None, max_length=100)
    valor_compra: Optional[float] = Field(None, ge=0)
    valor_venta: Optional[float] = Field(None, ge=0)
    marca: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)
    peso_kg: Optional[float] = Field(None, ge=0)
    observaciones: Optional[str] = None

    @field_validator("clase")
    @classmethod
    def validate_clase(cls, v):
        if v not in ClaseAnimal.opciones():
            raise ValueError(f"Clase debe ser uno de: {ClaseAnimal.opciones()}")
        return v

    @field_validator("sexo")
    @classmethod
    def validate_sexo(cls, v):
        if v not in SexoAnimal.opciones():
            raise ValueError(f"Sexo debe ser uno de: {SexoAnimal.opciones()}")
        return v

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, v):
        if v not in EstadoAnimal.opciones():
            raise ValueError(f"Estado debe ser uno de: {EstadoAnimal.opciones()}")
        return v

    @field_validator("fecha_nacimiento", mode="before")
    @classmethod
    def parse_fecha_nacimiento(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return None
        return v


class AnimalCreate(AnimalBase):
    pass


class AnimalUpdate(AnimalBase):
    lote_id: Optional[str] = None
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    arete: Optional[str] = Field(None, max_length=50)
    clase: Optional[str] = None


class VentaBase(BaseModel):
    fecha: date
    predio_id: Optional[str] = None
    clase: Optional[str] = None
    tipo: str = Field(..., description="Tipo de venta")
    detalle: Optional[str] = None
    cantidad: float = Field(..., gt=0)
    valor_unitario: float = Field(..., ge=0)
    valor_total: Optional[float] = Field(None, ge=0)
    metodo_pago: str = Field(default=MetodoPago.EFECTIVO.value)
    observaciones: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in TipoVenta.opciones():
            raise ValueError(f"Tipo debe ser uno de: {TipoVenta.opciones()}")
        return v

    @field_validator("metodo_pago")
    @classmethod
    def validate_metodo(cls, v):
        if v not in MetodoPago.opciones():
            raise ValueError(f"Método debe ser uno de: {MetodoPago.opciones()}")
        return v

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return date.today()
        return v

    @model_validator(mode="after")
    def compute_total(self):
        if self.cantidad is not None and self.valor_unitario is not None:
            self.valor_total = self.cantidad * self.valor_unitario
        return self


class VentaCreate(VentaBase):
    pass


class VentaUpdate(VentaBase):
    fecha: Optional[date] = None
    cantidad: Optional[float] = Field(None, gt=0)
    valor_unitario: Optional[float] = Field(None, ge=0)


class ProduccionBase(BaseModel):
    fecha: date
    predio_id: Optional[str] = None
    animal_id: Optional[str] = None
    clase: Optional[str] = None
    nombre_referencia: Optional[str] = None
    ordeno: bool = False
    kilos_leche: Optional[float] = Field(None, ge=0)
    litros_leche: Optional[float] = Field(None, ge=0)
    cantidad_huevos: int = Field(default=0, ge=0)
    observaciones: Optional[str] = None

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return date.today()
        return v


class ProduccionCreate(ProduccionBase):
    @model_validator(mode="after")
    def validate_produccion(self):
        if self.clase == ClaseAnimal.AVICOLA.value and self.cantidad_huevos == 0:
            raise ValueError("Para avícola, cantidad de huevos es obligatoria")
        if self.clase == ClaseAnimal.BOVINO.value and not self.litros_leche and not self.kilos_leche:
            raise ValueError("Para bovino, litros o kilos de leche es obligatorio")
        return self


class ProduccionUpdate(ProduccionBase):
    fecha: Optional[date] = None


class PesajeBase(BaseModel):
    animal_id: str
    fecha: date
    peso_kg: float = Field(..., gt=0, description="Peso en kilogramos")
    nota: Optional[str] = Field(None, max_length=300)

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return date.today()
        return v


class PesajeCreate(PesajeBase):
    pass


class PesajeUpdate(PesajeBase):
    animal_id: Optional[str] = None
    fecha: Optional[date] = None
    peso_kg: Optional[float] = Field(None, gt=0)


class MovimientoBase(BaseModel):
    animal_id: Optional[str] = None
    predio_id: Optional[str] = None
    tipo: str = Field(..., description="Tipo de movimiento")
    valor: Optional[float] = Field(None, ge=0)
    fecha: datetime = Field(default_factory=datetime.now)
    comentarios: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in TipoMovimiento.opciones():
            raise ValueError(f"Tipo debe ser uno de: {TipoMovimiento.opciones()}")
        return v

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now()
        return v


class MovimientoCreate(MovimientoBase):
    pass


class MovimientoUpdate(MovimientoBase):
    animal_id: Optional[str] = None
    predio_id: Optional[str] = None
    tipo: Optional[str] = None


class GastoBase(BaseModel):
    fecha: date
    predio_id: Optional[str] = None
    detalle: str = Field(..., min_length=1, max_length=200)
    valor: float = Field(..., ge=0)
    metodo_pago: str = Field(default=MetodoPago.EFECTIVO.value)
    inversor: Optional[str] = Field(None, max_length=100)
    observaciones: Optional[str] = None

    @field_validator("metodo_pago")
    @classmethod
    def validate_metodo(cls, v):
        if v not in MetodoPago.opciones():
            raise ValueError(f"Método debe ser uno de: {MetodoPago.opciones()}")
        return v

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return date.today()
        return v


class GastoCreate(GastoBase):
    pass


class GastoUpdate(GastoBase):
    fecha: Optional[date] = None
    detalle: Optional[str] = Field(None, min_length=1, max_length=200)
    valor: Optional[float] = Field(None, ge=0)


class SaludBase(BaseModel):
    animal_id: str
    fecha: date
    tipo_procedimiento: str = Field(..., description="Tipo de procedimiento")
    medicamento: Optional[str] = Field(None, max_length=100)
    veterinario: Optional[str] = Field(None, max_length=100)
    proxima_cita: Optional[date] = None
    observaciones: Optional[str] = None

    @field_validator("tipo_procedimiento")
    @classmethod
    def validate_tipo(cls, v):
        if v not in ProcedimientoSalud.opciones():
            raise ValueError(f"Tipo debe ser uno de: {ProcedimientoSalud.opciones()}")
        return v

    @field_validator("fecha", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return date.today()
        return v

    @field_validator("proxima_cita", mode="before")
    @classmethod
    def parse_proxima_cita(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return None
        return v

    @model_validator(mode="after")
    def validate_proxima_cita(self):
        if ProcedimientoSalud.requiere_proxima_cita(self.tipo_procedimiento) and not self.proxima_cita:
            raise ValueError(f"Para {self.tipo_procedimiento}, la próxima cita es obligatoria")
        if self.proxima_cita and self.proxima_cita < self.fecha:
            raise ValueError("La próxima cita no puede ser anterior a la fecha del procedimiento")
        return self


class SaludCreate(SaludBase):
    pass


class SaludUpdate(SaludBase):
    animal_id: Optional[str] = None
    fecha: Optional[date] = None
    tipo_procedimiento: Optional[str] = None


class ProfileBase(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    rol: str = Field(default=RolUsuario.COLABORADOR.value)
    grupo: Optional[str] = None
    activo: bool = True

    @field_validator("rol")
    @classmethod
    def validate_rol(cls, v):
        if v not in RolUsuario.opciones():
            raise ValueError(f"Rol debe ser uno de: {RolUsuario.opciones()}")
        return v


class ProfileUpdate(ProfileBase):
    pass


class PredioBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    owner_id: Optional[str] = None


class PredioCreate(PredioBase):
    pass


class LoteBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    predio_id: str
    activo: bool = True


class LoteCreate(LoteBase):
    pass


class GlobalFilters(BaseModel):
    predio: List[str] = Field(default_factory=list)
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    clase: List[str] = Field(default_factory=list)
    propietario: List[str] = Field(default_factory=list)

    @field_validator("fecha_inicio", "fecha_fin", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                return None
        return v


def validate_form(model_class: type[BaseModel], form_data: dict) -> tuple[bool, Optional[BaseModel], List[str]]:
    try:
        model = model_class(**form_data)
        return True, model, []
    except Exception as e:
        errors = []
        if hasattr(e, "errors"):
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
        else:
            errors.append(str(e))
        return False, None, errors
