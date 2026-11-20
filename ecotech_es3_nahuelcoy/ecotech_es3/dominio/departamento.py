"""Clase Departamento."""
from dominio.reportable import Reportable
from dominio.validaciones import validar_numero_positivo, validar_texto


class Departamento(Reportable):
    """Área de la empresa (UML: Departamento 1 --- * Empleado).

    La relación con Empleado se guarda en el empleado (departamento_id),
    igual que una llave foránea, así no se duplica la información.
    """

    def __init__(self, nombre: str, presupuesto: float, id_departamento: int | None = None):
        self._id = id_departamento
        self.nombre = nombre
        self.presupuesto = presupuesto

    @property
    def id(self) -> int | None:
        # Solo lectura: el id lo asigna la base de datos al guardar
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = validar_texto(valor, "nombre del departamento", 60)

    @property
    def presupuesto(self) -> float:
        return self._presupuesto

    @presupuesto.setter
    def presupuesto(self, valor: float) -> None:
        self._presupuesto = validar_numero_positivo(valor, "presupuesto", permitir_cero=True)

    def asignar_id(self, nuevo_id: int) -> None:
        """Lo usa el repositorio después del INSERT."""
        self._id = nuevo_id

    def resumen(self) -> str:
        return f"[Departamento] #{self._id or '-':<10} {self.nombre:<25} presupuesto ${self._presupuesto:>14,.0f}"

    def __str__(self) -> str:
        return self.resumen()
