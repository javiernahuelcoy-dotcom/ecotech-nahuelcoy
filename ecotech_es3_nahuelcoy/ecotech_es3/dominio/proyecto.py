"""Clase Proyecto."""
from datetime import date

from dominio.excepciones import DatoInvalidoError
from dominio.reportable import Reportable
from dominio.validaciones import normalizar_rut, validar_fecha, validar_texto


class Proyecto(Reportable):
    """Proyecto de la empresa (UML: Proyecto * --- * Empleado).

    Guarda los RUT de los empleados asignados. En la base de datos esta
    relación muchos-a-muchos se representa con la tabla 'asignacion'.
    """

    def __init__(self, nombre: str, descripcion: str = "", fecha_inicio: str | None = None,
                 id_proyecto: int | None = None, ruts_asignados: list[str] | None = None):
        self._id = id_proyecto
        self.nombre = nombre
        self.descripcion = descripcion
        self.fecha_inicio = fecha_inicio or date.today().isoformat()
        self._ruts_asignados = [normalizar_rut(r) for r in (ruts_asignados or [])]

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = validar_texto(valor, "nombre del proyecto", 80)

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @descripcion.setter
    def descripcion(self, valor: str) -> None:
        valor = (valor or "").strip()
        if len(valor) > 250:
            raise DatoInvalidoError("La descripción admite máximo 250 caracteres.")
        self._descripcion = valor

    @property
    def fecha_inicio(self) -> str:
        return self._fecha_inicio

    @fecha_inicio.setter
    def fecha_inicio(self, valor: str) -> None:
        self._fecha_inicio = validar_fecha(valor, "fecha de inicio")

    @property
    def ruts_asignados(self) -> tuple[str, ...]:
        # Se devuelve una tupla (inmutable) para que nadie modifique la lista interna desde afuera
        return tuple(self._ruts_asignados)

    def asignar_id(self, nuevo_id: int) -> None:
        self._id = nuevo_id

    def agregar_empleado(self, rut: str) -> None:
        rut = normalizar_rut(rut)
        if rut in self._ruts_asignados:
            raise DatoInvalidoError(f"El empleado {rut} ya está asignado a este proyecto.")
        self._ruts_asignados.append(rut)

    def resumen(self) -> str:
        return (f"[Proyecto]     #{self._id or '-':<10} {self.nombre:<25} inicio {self.fecha_inicio}  "
                f"{len(self._ruts_asignados)} empleado(s) asignado(s)")

    def __str__(self) -> str:
        return self.resumen()
