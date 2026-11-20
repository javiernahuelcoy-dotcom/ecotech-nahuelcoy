"""Repositorio idempotente para caché local de clima e indicadores económicos."""
import sqlite3

from dominio.servicios_externos import IndicadorEconomico, ReporteClima, normalizar_codigo_divisa
from repositorio.base import RepositorioBase


class IndicadoresRepositorio(RepositorioBase):
    def guardar_o_actualizar_clima(self, reporte: ReporteClima) -> None:
        """UPSERT idempotente: no duplica registros ante ejecuciones consecutivas."""
        with self._transaccion() as cursor:
            cursor.execute(
                """
                INSERT INTO clima_registro (
                    ciudad, fecha_consulta, temperatura_c, humedad_relativa,
                    descripcion, viento_kmh, fuente, obtenido_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ciudad, fecha_consulta) DO UPDATE SET
                    temperatura_c    = excluded.temperatura_c,
                    humedad_relativa = excluded.humedad_relativa,
                    descripcion      = excluded.descripcion,
                    viento_kmh       = excluded.viento_kmh,
                    fuente           = excluded.fuente,
                    obtenido_en      = excluded.obtenido_en
                """,
                (
                    reporte.ciudad,
                    reporte.fecha_consulta,
                    reporte.temperatura_c,
                    reporte.humedad_relativa,
                    reporte.descripcion,
                    reporte.viento_kmh,
                    reporte.fuente,
                    reporte.obtenido_en,
                ),
            )

    def obtener_ultimo_clima(self, ciudad: str) -> ReporteClima | None:
        fila = self._consultar_uno(
            """
            SELECT ciudad, fecha_consulta, temperatura_c, humedad_relativa,
                   descripcion, viento_kmh, fuente, obtenido_en
            FROM clima_registro
            WHERE ciudad = ?
            ORDER BY obtenido_en DESC
            LIMIT 1
            """,
            (ciudad,),
        )
        return self._fila_a_clima(fila) if fila else None

    def guardar_o_actualizar_indicador(self, indicador: IndicadorEconomico) -> None:
        """UPSERT idempotente: evita duplicados por (codigo, fecha_dato)."""
        with self._transaccion() as cursor:
            cursor.execute(
                """
                INSERT INTO indicador_economico (
                    codigo, nombre, valor_clp, unidad, fecha_dato, fuente, obtenido_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo, fecha_dato) DO UPDATE SET
                    nombre      = excluded.nombre,
                    valor_clp   = excluded.valor_clp,
                    unidad      = excluded.unidad,
                    fuente      = excluded.fuente,
                    obtenido_en = excluded.obtenido_en
                """,
                (
                    indicador.codigo,
                    indicador.nombre,
                    indicador.valor_clp,
                    indicador.unidad,
                    indicador.fecha_dato,
                    indicador.fuente,
                    indicador.obtenido_en,
                ),
            )

    def obtener_ultimo_indicador(self, codigo: str) -> IndicadorEconomico | None:
        codigo_norm = normalizar_codigo_divisa(codigo)
        fila = self._consultar_uno(
            """
            SELECT codigo, nombre, valor_clp, unidad, fecha_dato, fuente, obtenido_en
            FROM indicador_economico
            WHERE codigo = ?
            ORDER BY obtenido_en DESC
            LIMIT 1
            """,
            (codigo_norm,),
        )
        return self._fila_a_indicador(fila) if fila else None

    @staticmethod
    def _fila_a_clima(fila: sqlite3.Row) -> ReporteClima:
        return ReporteClima(
            ciudad=fila["ciudad"],
            fecha_consulta=fila["fecha_consulta"],
            temperatura_c=fila["temperatura_c"],
            humedad_relativa=fila["humedad_relativa"],
            descripcion=fila["descripcion"],
            viento_kmh=fila["viento_kmh"],
            fuente=fila["fuente"],
            obtenido_en=fila["obtenido_en"],
        )

    @staticmethod
    def _fila_a_indicador(fila: sqlite3.Row) -> IndicadorEconomico:
        return IndicadorEconomico(
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            valor_clp=fila["valor_clp"],
            unidad=fila["unidad"],
            fecha_dato=fila["fecha_dato"],
            fuente=fila["fuente"],
            obtenido_en=fila["obtenido_en"],
        )
