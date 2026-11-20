"""Capa de persistencia: conexión y repositorios (todo el SQL vive aquí)."""
from repositorio.departamento_repo import DepartamentoRepositorio
from repositorio.empleado_repo import EmpleadoRepositorio
from repositorio.indicadores_repo import IndicadoresRepositorio
from repositorio.proyecto_repo import ProyectoRepositorio
from repositorio.usuario_repo import UsuarioRepositorio

__all__ = [
    "DepartamentoRepositorio",
    "EmpleadoRepositorio",
    "IndicadoresRepositorio",
    "ProyectoRepositorio",
    "UsuarioRepositorio",
]
