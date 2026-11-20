"""Script de sincronización externa idempotente y resiliencia Plan B.

Ejecutar con: python sincronizar_apis.py
"""
import logging
import sys

from api_cliente import ServicioIntegracionEcoTech
from dominio.excepciones import EcoTechError
from repositorio.conexion import cargar_variables_entorno, inicializar_bd, obtener_conexion
from repositorio.indicadores_repo import IndicadoresRepositorio
from repositorio.usuario_repo import UsuarioRepositorio


def ejecutar_sincronizacion() -> int:
    logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
    cargar_variables_entorno()
    conexion = obtener_conexion()
    inicializar_bd(conexion)

    try:
        UsuarioRepositorio(conexion).asegurar_usuarios_iniciales()
        repo = IndicadoresRepositorio(conexion)
        servicio = ServicioIntegracionEcoTech(repo)

        print("=== SINCRONIZACIÓN DE SERVICIOS EXTERNOS - ECOTECH SOLUTIONS ===")
        for ciudad in ("Santiago", "Concepción"):
            try:
                clima, _, estado = servicio.consultar_clima_proyecto(ciudad)
                print(f"\n[{ciudad}] {estado}")
                print(" ", clima.resumen())
            except EcoTechError as error:
                print(f"\n[{ciudad}] Aviso controlado: {error}")

        try:
            indicadores, _, estado_div = servicio.consultar_indicadores_divisas(("dolar", "euro"))
            print(f"\n[Divisas] {estado_div}")
            for ind in indicadores:
                print(" ", ind.resumen())
        except EcoTechError as error:
            print(f"\n[Divisas] Aviso controlado: {error}")

        total_clima = conexion.execute("SELECT COUNT(*) FROM clima_registro").fetchone()[0]
        total_ind = conexion.execute("SELECT COUNT(*) FROM indicador_economico").fetchone()[0]
        print(f"\nTotal registros en BD -> clima_registro: {total_clima} | indicador_economico: {total_ind}")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    sys.exit(ejecutar_sincronizacion())
