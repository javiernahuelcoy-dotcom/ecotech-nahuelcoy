"""Funciones de validación reutilizadas por todas las clases del dominio.

Se centralizan aquí para no repetir la misma lógica en Persona, Empleado,
Departamento y Proyecto (principio DRY).
"""
import re
from datetime import date

from dominio.excepciones import DatoInvalidoError, RutInvalidoError

_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def validar_texto(valor, campo: str, largo_maximo: int = 100) -> str:
    """Devuelve el texto sin espacios sobrantes o lanza DatoInvalidoError."""
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalidoError(f"El campo '{campo}' no puede estar vacío.")
    valor = valor.strip()
    if len(valor) > largo_maximo:
        raise DatoInvalidoError(f"El campo '{campo}' admite máximo {largo_maximo} caracteres.")
    return valor


def validar_email(valor) -> str:
    valor = validar_texto(valor, "email", 120).lower()
    if not _PATRON_EMAIL.match(valor):
        raise DatoInvalidoError(f"El email '{valor}' no tiene un formato válido.")
    return valor


def validar_fecha(valor, campo: str) -> str:
    """Acepta 'AAAA-MM-DD', no permite fechas futuras y devuelve el texto ISO."""
    try:
        fecha = date.fromisoformat(str(valor).strip())
    except ValueError as error:
        raise DatoInvalidoError(f"El campo '{campo}' debe tener formato AAAA-MM-DD.") from error
    if fecha > date.today():
        raise DatoInvalidoError(f"El campo '{campo}' no puede ser una fecha futura.")
    return fecha.isoformat()


def validar_numero_positivo(valor, campo: str, permitir_cero: bool = False) -> float:
    # bool es subclase de int en Python, por eso se excluye explícitamente
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise DatoInvalidoError(f"El campo '{campo}' debe ser numérico.")
    if valor < 0 or (valor == 0 and not permitir_cero):
        raise DatoInvalidoError(f"El campo '{campo}' debe ser mayor que cero.")
    return float(valor)


def calcular_digito_verificador(numero: int) -> str:
    """Algoritmo módulo 11 usado por el Registro Civil de Chile."""
    suma = 0
    factor = 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(valor) -> str:
    """Valida un RUT chileno y lo devuelve como '12345678-5'.

    Acepta '12.345.678-5', '12345678-5' o '123456785'.
    """
    if not isinstance(valor, str):
        raise RutInvalidoError("El RUT debe ingresarse como texto.")
    limpio = valor.strip().upper().replace(".", "").replace("-", "")
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise RutInvalidoError(f"El RUT '{valor}' no tiene un formato válido.")
    cuerpo, dv = limpio[:-1], limpio[-1]
    if calcular_digito_verificador(int(cuerpo)) != dv:
        raise RutInvalidoError(f"El dígito verificador del RUT '{valor}' no es correcto.")
    return f"{int(cuerpo)}-{dv}"
