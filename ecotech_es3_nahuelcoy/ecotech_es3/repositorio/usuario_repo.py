"""Repositorio de Usuario: autenticación y persistencia con hashes bcrypt."""
import sqlite3

from dominio.excepciones import AutenticacionError, RegistroNoEncontradoError
from dominio.usuario import Usuario
from repositorio.base import RepositorioBase


class UsuarioRepositorio(RepositorioBase):
    MENSAJE_DUPLICADO = "Ya existe un usuario registrado con ese nombre."

    def guardar(self, usuario: Usuario) -> int:
        with self._transaccion() as cursor:
            cursor.execute(
                "INSERT INTO usuario (username, password_hash, rol, activo, creado_en) "
                "VALUES (?, ?, ?, ?, ?)",
                (usuario.username, usuario.password_hash, usuario.rol, int(usuario.activo), usuario.creado_en),
            )
            usuario.asignar_id(cursor.lastrowid)
        return usuario.id

    def obtener_por_username(self, username: str) -> Usuario:
        fila = self._consultar_uno(
            "SELECT id, username, password_hash, rol, activo, creado_en FROM usuario WHERE username = ?",
            (username.strip().lower(),),
        )
        if fila is None:
            raise RegistroNoEncontradoError(f"El usuario '{username}' no existe.")
        return self._fila_a_usuario(fila)

    def autenticar(self, username: str, password_plana: str) -> Usuario:
        try:
            usuario = self.obtener_por_username(username)
        except RegistroNoEncontradoError as error:
            raise AutenticacionError("Usuario o contraseña incorrectos.") from error
        usuario.autenticar(password_plana)
        return usuario

    def actualizar_password(self, username: str, nueva_password: str) -> None:
        nuevo_hash = Usuario.generar_hash(nueva_password)
        with self._transaccion() as cursor:
            cursor.execute(
                "UPDATE usuario SET password_hash = ? WHERE username = ?",
                (nuevo_hash, username.strip().lower()),
            )
            if cursor.rowcount == 0:
                raise RegistroNoEncontradoError(f"El usuario '{username}' no existe.")

    def listar_todos(self) -> list[Usuario]:
        filas = self._consultar_todos(
            "SELECT id, username, password_hash, rol, activo, creado_en FROM usuario ORDER BY username"
        )
        return [self._fila_a_usuario(f) for f in filas]

    def asegurar_usuarios_iniciales(self) -> None:
        """Crea cuentas base con salt aleatorio si la tabla está vacía (idempotente)."""
        if self.listar_todos():
            return
        self.guardar(Usuario.crear_nuevo("admin", "EcoTech2026#Admin", rol="admin"))
        self.guardar(Usuario.crear_nuevo("analista", "EcoTech2026#User", rol="analista"))

    @staticmethod
    def _fila_a_usuario(fila: sqlite3.Row) -> Usuario:
        return Usuario(
            id_usuario=fila["id"],
            username=fila["username"],
            password_hash=fila["password_hash"],
            rol=fila["rol"],
            activo=bool(fila["activo"]),
            creado_en=fila["creado_en"],
        )
