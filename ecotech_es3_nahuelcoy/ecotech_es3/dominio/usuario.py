"""Clase Usuario con almacenamiento seguro de contraseñas mediante bcrypt."""
from datetime import datetime, timezone

import bcrypt

from dominio.excepciones import AutenticacionError, DatoInvalidoError
from dominio.validaciones import validar_texto

ROLES_VALIDOS = ("admin", "analista")


class Usuario:
    """Entidad de autenticación del sistema EcoTech."""

    def __init__(
        self,
        username: str,
        password_hash: str,
        rol: str = "analista",
        id_usuario: int | None = None,
        activo: bool = True,
        creado_en: str | None = None,
    ):
        self._id = id_usuario
        self.username = username
        self.password_hash = password_hash
        self.rol = rol
        self._activo = bool(activo)
        self._creado_en = creado_en or datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def id(self) -> int | None:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, valor: str) -> None:
        limpio = validar_texto(valor, "nombre de usuario", 40).lower()
        if not limpio.replace("_", "").replace(".", "").isalnum():
            raise DatoInvalidoError("El usuario solo admite letras, números, punto o guion bajo.")
        self._username = limpio

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @password_hash.setter
    def password_hash(self, valor: str) -> None:
        if not isinstance(valor, str) or not valor.startswith(("$2a$", "$2b$", "$2y$")):
            raise DatoInvalidoError("La contraseña debe almacenarse como hash bcrypt válido.")
        self._password_hash = valor

    @property
    def rol(self) -> str:
        return self._rol

    @rol.setter
    def rol(self, valor: str) -> None:
        rol_limpio = validar_texto(valor, "rol", 20).lower()
        if rol_limpio not in ROLES_VALIDOS:
            raise DatoInvalidoError(f"Rol inválido. Valores permitidos: {', '.join(ROLES_VALIDOS)}.")
        self._rol = rol_limpio

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def creado_en(self) -> str:
        return self._creado_en

    def asignar_id(self, nuevo_id: int) -> None:
        self._id = nuevo_id

    @staticmethod
    def generar_hash(password_plana: str) -> str:
        """Genera un hash bcrypt con salt criptográfico aleatorio único."""
        if not isinstance(password_plana, str) or len(password_plana) < 8:
            raise DatoInvalidoError("La contraseña debe tener al menos 8 caracteres.")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password_plana.encode("utf-8"), salt).decode("utf-8")

    @classmethod
    def crear_nuevo(cls, username: str, password_plana: str, rol: str = "analista") -> "Usuario":
        return cls(username=username, password_hash=cls.generar_hash(password_plana), rol=rol)

    def verificar_password(self, password_plana: str) -> bool:
        """Compara en tiempo constante contra el hash almacenado."""
        if not self._activo or not isinstance(password_plana, str) or not password_plana:
            return False
        return bcrypt.checkpw(
            password_plana.encode("utf-8"),
            self._password_hash.encode("utf-8"),
        )

    def autenticar(self, password_plana: str) -> None:
        if not self.verificar_password(password_plana):
            raise AutenticacionError("Usuario o contraseña incorrectos.")
