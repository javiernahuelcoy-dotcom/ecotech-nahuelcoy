"""Repositorio de Empleado: único lugar donde se escribe SQL de empleados.

TODAS las consultas usan marcadores '?' y los valores viajan aparte en una
tupla. Nunca se arma SQL con +, % ni f-strings.
"""
import sqlite3

from dominio.empleado import Empleado
from dominio.excepciones import RegistroNoEncontradoError
from dominio.validaciones import normalizar_rut
from repositorio.base import RepositorioBase


class EmpleadoRepositorio(RepositorioBase):
    MENSAJE_DUPLICADO = "Ya existe una persona registrada con ese RUT."
    MENSAJE_REFERENCIA = "El departamento indicado no existe."

    # Cada consulta se escribe completa (sin unir trozos con +) para que se lea
    # de una vez y nadie pueda pensar que se armó con datos del usuario.
    _SQL_POR_RUT = """
        SELECT p.rut, p.nombre, p.email, p.telefono,
               e.cargo, e.sueldo_base, e.fecha_ingreso, e.departamento_id, e.activo
        FROM empleado e JOIN persona p ON p.rut = e.rut
        WHERE e.rut = ?
    """
    _SQL_ACTIVOS = """
        SELECT p.rut, p.nombre, p.email, p.telefono,
               e.cargo, e.sueldo_base, e.fecha_ingreso, e.departamento_id, e.activo
        FROM empleado e JOIN persona p ON p.rut = e.rut
        WHERE e.activo = 1
        ORDER BY p.nombre
    """
    _SQL_POR_NOMBRE = """
        SELECT p.rut, p.nombre, p.email, p.telefono,
               e.cargo, e.sueldo_base, e.fecha_ingreso, e.departamento_id, e.activo
        FROM empleado e JOIN persona p ON p.rut = e.rut
        WHERE e.activo = 1 AND p.nombre LIKE '%' || ? || '%'
        ORDER BY p.nombre
    """
    _SQL_POR_DEPARTAMENTO = """
        SELECT p.rut, p.nombre, p.email, p.telefono,
               e.cargo, e.sueldo_base, e.fecha_ingreso, e.departamento_id, e.activo
        FROM empleado e JOIN persona p ON p.rut = e.rut
        WHERE e.activo = 1 AND e.departamento_id = ?
        ORDER BY p.nombre
    """

    # ---------- CREATE ----------
    def guardar(self, empleado: Empleado) -> None:
        """Inserta en persona y en empleado dentro de UNA transacción.

        Si el segundo INSERT falla (ej. departamento inexistente), el rollback
        deshace también el primero y no queda una persona "huérfana".
        """
        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO persona (rut, nombre, email, telefono) VALUES (?, ?, ?, ?)",
                (empleado.rut, empleado.nombre, empleado.email, empleado.telefono),
            )
            cursor.execute(
                "INSERT INTO empleado (rut, cargo, sueldo_base, fecha_ingreso, departamento_id, activo) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (empleado.rut, empleado.cargo, empleado.sueldo_base, empleado.fecha_ingreso,
                 empleado.departamento_id, int(empleado.activo)),
            )

    # ---------- READ ----------
    def obtener_por_rut(self, rut: str) -> Empleado:
        rut = normalizar_rut(rut)
        fila = self._consultar_uno(self._SQL_POR_RUT, (rut,))
        if fila is None:
            raise RegistroNoEncontradoError(f"No existe un empleado con RUT {rut}.")
        return self._fila_a_empleado(fila)

    def listar_activos(self) -> list[Empleado]:
        filas = self._consultar_todos(self._SQL_ACTIVOS)
        return [self._fila_a_empleado(f) for f in filas]

    def buscar_por_nombre(self, texto: str) -> list[Empleado]:
        """Búsqueda parcial. Los '%' se agregan dentro del SQL con ||; el texto del
        usuario viaja como parámetro y el motor lo trata solo como dato."""
        filas = self._consultar_todos(self._SQL_POR_NOMBRE, (texto,))
        return [self._fila_a_empleado(f) for f in filas]

    def listar_por_departamento(self, departamento_id: int) -> list[Empleado]:
        filas = self._consultar_todos(self._SQL_POR_DEPARTAMENTO, (departamento_id,))
        return [self._fila_a_empleado(f) for f in filas]

    # ---------- UPDATE ----------
    def actualizar(self, empleado: Empleado) -> None:
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE persona SET nombre = ?, email = ?, telefono = ? WHERE rut = ?",
                (empleado.nombre, empleado.email, empleado.telefono, empleado.rut),
            )
            cursor.execute(
                "UPDATE empleado SET cargo = ?, sueldo_base = ?, departamento_id = ? WHERE rut = ?",
                (empleado.cargo, empleado.sueldo_base, empleado.departamento_id, empleado.rut),
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un empleado con RUT {empleado.rut}.")

    # ---------- DELETE (lógico) ----------
    def eliminar(self, rut: str) -> None:
        """Borrado lógico: se marca activo = 0 para conservar el historial."""
        rut = normalizar_rut(rut)
        with self._transaccion() as cursor:
            cursor.execute("UPDATE empleado SET activo = 0 WHERE rut = ? AND activo = 1", (rut,))
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un empleado activo con RUT {rut}.")
            # Al desvincularlo también se quita de los proyectos donde estaba asignado
            cursor.execute("DELETE FROM asignacion WHERE rut_empleado = ?", (rut,))

    # ---------- MAPPER ----------
    @staticmethod
    def _fila_a_empleado(fila: sqlite3.Row) -> Empleado:
        """Único punto donde una fila de la BD se convierte en objeto Empleado."""
        return Empleado(
            rut=fila["rut"],
            nombre=fila["nombre"],
            email=fila["email"],
            telefono=fila["telefono"] or "",
            cargo=fila["cargo"],
            sueldo_base=fila["sueldo_base"],
            fecha_ingreso=fila["fecha_ingreso"],
            departamento_id=fila["departamento_id"],
            activo=bool(fila["activo"]),
        )
