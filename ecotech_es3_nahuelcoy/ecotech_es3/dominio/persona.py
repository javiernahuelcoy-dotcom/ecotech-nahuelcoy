"""Clase base abstracta Persona."""
from abc import abstractmethod

from dominio.reportable import Reportable
from dominio.validaciones import normalizar_rut, validar_email, validar_texto


class Persona(Reportable):
    """Datos comunes a cualquier persona del sistema (UML: clase abstracta Persona).

    Es abstracta: no se puede crear una Persona "suelta", solo sus
    subclases (Empleado). Todos los atributos son protegidos (_atributo) y
    se modifican a través de propiedades que validan el dato.
    """

    def __init__(self, rut: str, nombre: str, email: str, telefono: str = ""):
        # Se asigna a través de las propiedades para que pase por la validación
        self.rut = rut
        self.nombre = nombre
        self.email = email
        self.telefono = telefono

    @property
    def rut(self) -> str:
        return self._rut

    @rut.setter
    def rut(self, valor: str) -> None:
        self._rut = normalizar_rut(valor)

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        self._nombre = validar_texto(valor, "nombre", 80)

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, valor: str) -> None:
        self._email = validar_email(valor)

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str) -> None:
        # El teléfono es opcional: vacío se permite, pero si viene debe ser válido
        valor = (valor or "").strip()
        if valor:
            valor = validar_texto(valor, "teléfono", 20)
        self._telefono = valor

    @abstractmethod
    def resumen(self) -> str:
        """Cada subclase define cómo se resume."""
