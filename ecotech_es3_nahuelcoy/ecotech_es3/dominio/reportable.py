"""Interfaz común para todo lo que aparece en el reporte general."""
from abc import ABC, abstractmethod


class Reportable(ABC):
    """Contrato: toda entidad del sistema sabe describirse a sí misma.

    Gracias a esto el reporte general recorre empleados, departamentos y
    proyectos en una sola lista y llama a resumen() sin preguntar el tipo
    de cada objeto (polimorfismo).
    """

    @abstractmethod
    def resumen(self) -> str:
        """Devuelve una línea de texto que describe la entidad."""
