"""Clase Empleado: especialización de Persona."""
from datetime import date

from dominio.excepciones import DatoInvalidoError, SueldoInvalidoError
from dominio.persona import Persona
from dominio.validaciones import validar_fecha, validar_numero_positivo, validar_texto


class Empleado(Persona):
    """Empleado de EcoTech (UML: Empleado hereda de Persona).

    El cargo (ej. "Gerente", "Analista") es un ATRIBUTO y no una subclase:
    un empleado puede cambiar de cargo sin dejar de ser el mismo objeto.
    """

    # Descuento aproximado de AFP + salud usado para el sueldo líquido
    DESCUENTO_LEGAL = 0.20

    def __init__(self, rut: str, nombre: str, email: str, cargo: str,
                 sueldo_base: float, fecha_ingreso: str | None = None,
                 departamento_id: int | None = None, telefono: str = "",
                 activo: bool = True):
        super().__init__(rut, nombre, email, telefono)
        self.cargo = cargo
        self.sueldo_base = sueldo_base
        self.fecha_ingreso = fecha_ingreso or date.today().isoformat()
        self.departamento_id = departamento_id
        self._activo = bool(activo)

    @property
    def cargo(self) -> str:
        return self._cargo

    @cargo.setter
    def cargo(self, valor: str) -> None:
        self._cargo = validar_texto(valor, "cargo", 60)

    @property
    def sueldo_base(self) -> float:
        return self._sueldo_base

    @sueldo_base.setter
    def sueldo_base(self, valor: float) -> None:
        try:
            self._sueldo_base = validar_numero_positivo(valor, "sueldo base")
        except DatoInvalidoError as error:
            raise SueldoInvalidoError(str(error)) from error

    @property
    def fecha_ingreso(self) -> str:
        return self._fecha_ingreso

    @fecha_ingreso.setter
    def fecha_ingreso(self, valor: str) -> None:
        self._fecha_ingreso = validar_fecha(valor, "fecha de ingreso")

    @property
    def departamento_id(self) -> int | None:
        return self._departamento_id

    @departamento_id.setter
    def departamento_id(self, valor: int | None) -> None:
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0):
            raise DatoInvalidoError("El id de departamento debe ser un entero positivo.")
        self._departamento_id = valor

    @property
    def activo(self) -> bool:
        # Solo lectura: se cambia con desactivar(), no asignando True/False desde afuera
        return self._activo

    def desactivar(self) -> None:
        self._activo = False

    def calcular_sueldo_liquido(self, descuento: float = DESCUENTO_LEGAL) -> float:
        """Sueldo base menos descuentos legales (por defecto 20 %)."""
        if not 0 <= descuento < 1:
            raise DatoInvalidoError("El descuento debe estar entre 0 y 1.")
        return round(self._sueldo_base * (1 - descuento), 0)

    def resumen(self) -> str:
        estado = "activo" if self._activo else "inactivo"
        return (f"[Empleado]     {self.rut:<11} {self.nombre:<25} {self.cargo:<20} "
                f"base ${self._sueldo_base:>12,.0f}  líquido ${self.calcular_sueldo_liquido():>12,.0f}  ({estado})")

    def __str__(self) -> str:
        return self.resumen()
