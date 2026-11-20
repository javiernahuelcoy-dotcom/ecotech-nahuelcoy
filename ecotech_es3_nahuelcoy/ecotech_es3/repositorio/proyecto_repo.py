"""Repositorio de Proyecto y de la relación muchos-a-muchos con Empleado."""
import sqlite3

from dominio.excepciones import RegistroNoEncontradoError
from dominio.proyecto import Proyecto
from dominio.validaciones import normalizar_rut
from repositorio.base import RepositorioBase


class ProyectoRepositorio(RepositorioBase):
    MENSAJE_DUPLICADO = "Ya existe un proyecto con ese nombre, o el empleado ya está asignado."
    MENSAJE_REFERENCIA = "El empleado o el proyecto indicado no existe."

    # ---------- CREATE ----------
    def guardar(self, proyecto: Proyecto) -> int:
        """Inserta el proyecto y sus asignaciones en una sola transacción."""
        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO proyecto (nombre, descripcion, fecha_inicio) VALUES (?, ?, ?)",
                (proyecto.nombre, proyecto.descripcion, proyecto.fecha_inicio),
            )
            proyecto.asignar_id(cursor.lastrowid)
            for rut in proyecto.ruts_asignados:
                cursor.execute(
                    "INSERT INTO asignacion (rut_empleado, proyecto_id) VALUES (?, ?)",
                    (rut, proyecto.id),
                )
        return proyecto.id

    def asignar_empleado(self, id_proyecto: int, rut: str) -> None:
        rut = normalizar_rut(rut)
        with self._transaccion() as cursor:
            # Solo se asignan empleados activos: el SELECT dentro del INSERT lo garantiza
            cursor.execute(
                "INSERT INTO asignacion (rut_empleado, proyecto_id) "
                "SELECT rut, ? FROM empleado WHERE rut = ? AND activo = 1",
                (id_proyecto, rut),
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un empleado activo con RUT {rut}.")

    # ---------- READ ----------
    def obtener_por_id(self, id_proyecto: int) -> Proyecto:
        fila = self._consultar_uno(
            "SELECT id, nombre, descripcion, fecha_inicio FROM proyecto WHERE id = ?", (id_proyecto,)
        )
        if fila is None:
            raise RegistroNoEncontradoError(f"No existe un proyecto con id {id_proyecto}.")
        return self._fila_a_proyecto(fila, self._ruts_de(id_proyecto))

    def listar_todos(self) -> list[Proyecto]:
        filas = self._consultar_todos(
            "SELECT id, nombre, descripcion, fecha_inicio FROM proyecto ORDER BY fecha_inicio DESC"
        )
        return [self._fila_a_proyecto(f, self._ruts_de(f["id"])) for f in filas]

    def _ruts_de(self, id_proyecto: int) -> list[str]:
        filas = self._consultar_todos(
            "SELECT rut_empleado FROM asignacion WHERE proyecto_id = ? ORDER BY rut_empleado",
            (id_proyecto,),
        )
        return [f["rut_empleado"] for f in filas]

    # ---------- UPDATE ----------
    def actualizar(self, proyecto: Proyecto) -> None:
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE proyecto SET nombre = ?, descripcion = ?, fecha_inicio = ? WHERE id = ?",
                (proyecto.nombre, proyecto.descripcion, proyecto.fecha_inicio, proyecto.id),
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un proyecto con id {proyecto.id}.")

    # ---------- DELETE ----------
    def eliminar(self, id_proyecto: int) -> None:
        """Borra primero las asignaciones (tabla hija) y luego el proyecto, todo o nada."""
        with self._transaccion() as cursor:
            cursor.execute("DELETE FROM asignacion WHERE proyecto_id = ?", (id_proyecto,))
            cursor.execute("DELETE FROM proyecto WHERE id = ?", (id_proyecto,))
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un proyecto con id {id_proyecto}.")

    def quitar_empleado(self, id_proyecto: int, rut: str) -> None:
        rut = normalizar_rut(rut)
        with self._transaccion() as cursor:
            cursor.execute(
                "DELETE FROM asignacion WHERE proyecto_id = ? AND rut_empleado = ?", (id_proyecto, rut)
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"El empleado {rut} no está asignado al proyecto {id_proyecto}.")

    # ---------- MAPPER ----------
    @staticmethod
    def _fila_a_proyecto(fila: sqlite3.Row, ruts: list[str]) -> Proyecto:
        return Proyecto(
            id_proyecto=fila["id"],
            nombre=fila["nombre"],
            descripcion=fila["descripcion"] or "",
            fecha_inicio=fila["fecha_inicio"],
            ruts_asignados=ruts,
        )
