"""Repositorio de Departamento (CRUD parametrizado)."""
import sqlite3

from dominio.departamento import Departamento
from dominio.excepciones import RegistroNoEncontradoError
from repositorio.base import RepositorioBase


class DepartamentoRepositorio(RepositorioBase):
    MENSAJE_DUPLICADO = "Ya existe un departamento con ese nombre."
    MENSAJE_REFERENCIA = "No se puede eliminar: el departamento todavía tiene empleados asociados."

    # ---------- CREATE ----------
    def guardar(self, departamento: Departamento) -> int:
        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO departamento (nombre, presupuesto) VALUES (?, ?)",
                (departamento.nombre, departamento.presupuesto),
            )
            departamento.asignar_id(cursor.lastrowid)
        return departamento.id

    # ---------- READ ----------
    def obtener_por_id(self, id_departamento: int) -> Departamento:
        fila = self._consultar_uno(
            "SELECT id, nombre, presupuesto FROM departamento WHERE id = ?", (id_departamento,)
        )
        if fila is None:
            raise RegistroNoEncontradoError(f"No existe un departamento con id {id_departamento}.")
        return self._fila_a_departamento(fila)

    def listar_todos(self) -> list[Departamento]:
        filas = self._consultar_todos("SELECT id, nombre, presupuesto FROM departamento ORDER BY nombre")
        return [self._fila_a_departamento(f) for f in filas]

    # ---------- UPDATE ----------
    def actualizar(self, departamento: Departamento) -> None:
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE departamento SET nombre = ?, presupuesto = ? WHERE id = ?",
                (departamento.nombre, departamento.presupuesto, departamento.id),
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un departamento con id {departamento.id}.")

    # ---------- DELETE (físico) ----------
    def eliminar(self, id_departamento: int) -> None:
        """La llave foránea de empleado impide borrar un departamento con empleados
        (aunque estén inactivos); ese IntegrityError se traduce a ReferenciaInvalidaError."""
        with self._transaccion() as cursor:
            cursor.execute("DELETE FROM departamento WHERE id = ?", (id_departamento,))
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"No existe un departamento con id {id_departamento}.")

    # ---------- MAPPER ----------
    @staticmethod
    def _fila_a_departamento(fila: sqlite3.Row) -> Departamento:
        return Departamento(
            id_departamento=fila["id"],
            nombre=fila["nombre"],
            presupuesto=fila["presupuesto"],
        )
