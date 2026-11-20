"""Capa de dominio: clases del negocio (POO pura, sin SQL)."""
from dominio.departamento import Departamento
from dominio.empleado import Empleado
from dominio.persona import Persona
from dominio.proyecto import Proyecto
from dominio.reportable import Reportable
from dominio.servicios_externos import DeserializadorAPI, IndicadorEconomico, ReporteClima
from dominio.usuario import Usuario

__all__ = [
    "Departamento",
    "DeserializadorAPI",
    "Empleado",
    "IndicadorEconomico",
    "Persona",
    "Proyecto",
    "Reportable",
    "ReporteClima",
    "Usuario",
]
