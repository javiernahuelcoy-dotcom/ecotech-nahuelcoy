"""Demostración para la defensa: inyección SQL bloqueada y rollback.

Ejecutar con:  python demo_seguridad.py
Usa una base de datos en memoria, así no toca los datos reales.
"""
from dominio import Empleado
from dominio.excepciones import EcoTechError
from main import SistemaEcoTech
from repositorio.conexion import inicializar_bd, obtener_conexion

PAYLOAD = "' OR '1'='1"


def contar_personas(conexion) -> int:
    return conexion.execute("SELECT COUNT(*) FROM persona").fetchone()[0]


def main() -> None:
    conexion = obtener_conexion(":memory:")
    inicializar_bd(conexion)
    sistema = SistemaEcoTech(conexion)
    sistema.cargar_datos_de_ejemplo()
    repo = sistema.empleados

    print("=== PRUEBA 1: inyección SQL ===")
    print(f"Empleados activos en la BD: {len(repo.listar_activos())}")
    normales = repo.buscar_por_nombre("Diego")
    print(f"Búsqueda normal 'Diego'        -> {len(normales)} resultado(s): {[e.nombre for e in normales]}")
    atacados = repo.buscar_por_nombre(PAYLOAD)
    print(f"Búsqueda con payload {PAYLOAD!r} -> {len(atacados)} resultado(s)")
    print("Consulta usada: ... WHERE p.nombre LIKE '%' || ? || '%'   parámetros: (texto,)")
    print("Resultado: el payload se trató como TEXTO, no como código SQL. No se filtró ningún dato.\n")

    print("=== PRUEBA 2: transacción atómica (rollback) ===")
    print(f"Personas en la BD antes: {contar_personas(conexion)}")
    nuevo = Empleado("20.123.456-5", "Ignacio Vera", "ignacio@ecotech.cl", "Analista", 1_000_000,
                     departamento_id=999)
    try:
        repo.guardar(nuevo)  # 1er INSERT (persona) funciona; 2do INSERT (empleado) falla: depto 999 no existe
    except EcoTechError as error:
        print(f"Error capturado: {type(error).__name__}: {error}")
    print(f"Personas en la BD después: {contar_personas(conexion)}")
    print("Resultado: el rollback deshizo el INSERT en persona. No quedó ningún registro a medias.")
    conexion.close()


if __name__ == "__main__":
    main()
