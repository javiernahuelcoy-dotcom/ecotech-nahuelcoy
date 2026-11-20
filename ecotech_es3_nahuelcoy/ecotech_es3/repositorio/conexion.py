"""Conexión oficial a SQLite usando la librería estándar sqlite3.

La ruta de la base de datos NO se escribe en el código: se lee desde la
variable de entorno ECOTECH_DB_PATH (archivo .env, que no se sube a Git).
"""
import logging
import os
import sqlite3
from pathlib import Path

from dominio.excepciones import PersistenciaError

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
ARCHIVO_ESQUEMA = RAIZ_PROYECTO / "datos" / "schema.sql"
RUTA_POR_DEFECTO = "datos/ecotech.db"

logger = logging.getLogger(__name__)


def cargar_variables_entorno() -> None:
    """Carga el archivo .env con python-dotenv (si está instalado)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv no está instalado: se usarán las variables del sistema "
                       "o la ruta por defecto '%s'.", RUTA_POR_DEFECTO)
        return
    load_dotenv(RAIZ_PROYECTO / ".env")


def obtener_ruta_bd() -> str:
    ruta = os.getenv("ECOTECH_DB_PATH", RUTA_POR_DEFECTO)
    if ruta == ":memory:":
        return ruta
    ruta_path = Path(ruta)
    if not ruta_path.is_absolute():
        ruta_path = RAIZ_PROYECTO / ruta_path
    ruta_path.parent.mkdir(parents=True, exist_ok=True)
    return str(ruta_path)


def obtener_conexion(ruta: str | None = None) -> sqlite3.Connection:
    """Abre la conexión y activa la integridad referencial.

    - timeout=5: espera hasta 5 s si el archivo está bloqueado por otro proceso.
    - PRAGMA foreign_keys = ON: SQLite NO revisa las llaves foráneas si no se activa.
    - row_factory = sqlite3.Row: permite leer columnas por nombre (fila["rut"]).
    """
    ruta = ruta or obtener_ruta_bd()
    try:
        conexion = sqlite3.connect(ruta, timeout=5)
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.row_factory = sqlite3.Row
        return conexion
    except sqlite3.Error as error:
        raise PersistenciaError(f"No se pudo conectar a la base de datos '{ruta}': {error}") from error


def inicializar_bd(conexion: sqlite3.Connection | None = None) -> None:
    """Crea las tablas ejecutando datos/schema.sql (CREATE TABLE IF NOT EXISTS)."""
    cerrar_al_final = conexion is None
    if conexion is None:
        cargar_variables_entorno()
        conexion = obtener_conexion()
    try:
        esquema = ARCHIVO_ESQUEMA.read_text(encoding="utf-8")
        conexion.executescript(esquema)
        conexion.commit()
    except OSError as error:
        raise PersistenciaError(f"No se pudo leer el esquema '{ARCHIVO_ESQUEMA}': {error}") from error
    except sqlite3.Error as error:
        raise PersistenciaError(f"Error al crear las tablas: {error}") from error
    finally:
        if cerrar_al_final:
            conexion.close()
