"""Cliente HTTP seguro y resiliente con reintentos, backoff y degradación controlada (Plan B)."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import os
import time
from typing import Any

import requests

from dominio.excepciones import (
    ApiEndpointInvalidoError,
    ApiError,
    ApiServicioNoDisponibleError,
    DatoInvalidoError,
    DeserializacionError,
)
from dominio.servicios_externos import (
    CIUDADES_PROYECTO,
    DeserializadorAPI,
    IndicadorEconomico,
    ReporteClima,
    calcular_antiguedad_texto,
    normalizar_codigo_divisa,
)
from repositorio.indicadores_repo import IndicadoresRepositorio

logger = logging.getLogger(__name__)


def _leer_float_env(nombre: str, defecto: float) -> float:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        return defecto
    try:
        return float(valor)
    except ValueError:
        return defecto


def _leer_int_env(nombre: str, defecto: int) -> int:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        return defecto
    try:
        return int(valor)
    except ValueError:
        return defecto


class ClienteAPI:
    """Cliente HTTP con timeout explícito, validación TLS y política diferenciada por estado HTTP."""

    HEADERS_POR_DEFECTO = {
        "Accept": "application/json",
        "User-Agent": "EcoTech-Solutions-Client/3.0",
    }

    def __init__(
        self,
        timeout_conexion: float | None = None,
        timeout_lectura: float | None = None,
        max_intentos: int | None = None,
        backoff_base: float | None = None,
        sesion: requests.Session | None = None,
    ):
        t_conn = timeout_conexion if timeout_conexion is not None else _leer_float_env("API_TIMEOUT_CONEXION", 3.0)
        t_read = timeout_lectura if timeout_lectura is not None else _leer_float_env("API_TIMEOUT_LECTURA", 7.0)
        intentos = max_intentos if max_intentos is not None else _leer_int_env("API_MAX_INTENTOS", 3)
        base = backoff_base if backoff_base is not None else _leer_float_env("API_BACKOFF_BASE", 1.0)

        if t_conn <= 0 or t_read <= 0:
            raise DatoInvalidoError("Los tiempos de timeout deben ser mayores que cero.")
        if not (1 <= intentos <= 4):
            raise DatoInvalidoError("El número máximo de intentos debe estar entre 1 y 4.")

        self._timeout: tuple[float, float] = (t_conn, t_read)
        self._max_intentos = intentos
        self._backoff_base = max(0.1, base)
        self._sesion = sesion

    def _ejecutar_get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        if self._sesion is not None:
            return self._sesion.get(
                url,
                params=params,
                headers=self.HEADERS_POR_DEFECTO,
                timeout=self._timeout,
                verify=True,
            )
        return requests.get(
            url,
            params=params,
            headers=self.HEADERS_POR_DEFECTO,
            timeout=self._timeout,
            verify=True,
        )

    def obtener_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Ejecuta GET con manejo diferenciado de códigos HTTP y reintentos acotados."""
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            raise ApiEndpointInvalidoError("La URL del servicio externo debe iniciar con http:// o https://.")

        ultimo_error: Exception | None = None

        for intento in range(1, self._max_intentos + 1):
            try:
                respuesta = self._ejecutar_get(url, params=params)
            except (requests.Timeout, requests.ConnectionError) as error:
                ultimo_error = error
                logger.warning("Fallo de red/timeout en intento %d/%d para %s.", intento, self._max_intentos, url)
                if intento < self._max_intentos:
                    time.sleep(self._calcular_espera(intento))
                    continue
                raise ApiServicioNoDisponibleError(
                    "Servicio externo inalcanzable por fallo de red o tiempo de espera agotado."
                ) from error
            except requests.RequestException as error:
                raise ApiServicioNoDisponibleError("Error inesperado en la comunicación HTTP.") from error

            codigo = respuesta.status_code

            # 2xx: Éxito
            if 200 <= codigo < 300:
                try:
                    return respuesta.json()
                except ValueError as error:
                    raise DeserializacionError("El servicio externo devolvió contenido que no es JSON válido.") from error

            # 429 Too Many Requests: respeta Retry-After y reintenta dentro del límite
            if codigo == 429:
                espera = self._parsear_retry_after(respuesta.headers.get("Retry-After"), intento)
                logger.warning("HTTP 429 recibido. Esperando %.1fs (intento %d/%d).", espera, intento, self._max_intentos)
                if intento < self._max_intentos:
                    time.sleep(espera)
                    continue
                raise ApiServicioNoDisponibleError("Límite de peticiones (HTTP 429) excedido tras reintentos.")

            # Otros 4xx: Error de cliente o endpoint inválido -> NO se reintentan
            if 400 <= codigo < 500:
                raise ApiEndpointInvalidoError(
                    f"Solicitud rechazada por el servidor externo (HTTP {codigo}). No se reintenta."
                )

            # 5xx: Error temporal del servidor -> SÍ se reintentan con backoff exponencial
            if 500 <= codigo < 600:
                logger.warning("HTTP %d en intento %d/%d para %s.", codigo, intento, self._max_intentos, url)
                if intento < self._max_intentos:
                    time.sleep(self._calcular_espera(intento))
                    continue
                raise ApiServicioNoDisponibleError(
                    f"El servicio externo respondió HTTP {codigo} tras {self._max_intentos} intentos."
                )

            raise ApiServicioNoDisponibleError(f"Código HTTP inesperado: {codigo}.")

        raise ApiServicioNoDisponibleError("No se pudo completar la solicitud al servicio externo.") from ultimo_error

    def _calcular_espera(self, intento: int) -> float:
        """Backoff exponencial: base * 2^(intento - 1)."""
        return self._backoff_base * (2 ** (intento - 1))

    def _parsear_retry_after(self, cabecera: str | None, intento: int) -> float:
        if not cabecera:
            return self._calcular_espera(intento)
        texto = cabecera.strip()
        try:
            segundos = float(texto)
            return min(10.0, max(0.5, segundos))
        except ValueError:
            pass
        try:
            fecha_objetivo = parsedate_to_datetime(texto)
            if fecha_objetivo.tzinfo is None:
                fecha_objetivo = fecha_objetivo.replace(tzinfo=timezone.utc)
            delta = (fecha_objetivo - datetime.now(timezone.utc)).total_seconds()
            return min(10.0, max(0.5, delta))
        except (TypeError, ValueError):
            return self._calcular_espera(intento)


class ServicioIntegracionEcoTech:
    """Coordina API externa + deserialización + persistencia idempotente + Plan B local."""

    def __init__(self, repo_indicadores: IndicadoresRepositorio, cliente_api: ClienteAPI | None = None):
        self._repo = repo_indicadores
        self._cliente = cliente_api or ClienteAPI()
        self._url_clima = os.getenv("API_CLIMA_URL", "").strip() or "https://api.open-meteo.com/v1/forecast"
        self._url_divisas = os.getenv("API_DIVISAS_URL", "").strip() or "https://mindicador.cl/api"

    def consultar_clima_proyecto(self, ciudad: str, url_override: str | None = None) -> tuple[ReporteClima, bool, str]:
        """Retorna (ReporteClima, es_plan_b, mensaje_estado)."""
        if ciudad not in CIUDADES_PROYECTO:
            disponibles = ", ".join(CIUDADES_PROYECTO.keys())
            raise DatoInvalidoError(f"Ciudad no soportada. Opciones válidas: {disponibles}.")

        lat, lon = CIUDADES_PROYECTO[ciudad]
        url = url_override or self._url_clima
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "America/Santiago",
        }

        try:
            datos_json = self._cliente.obtener_json(url, params=params)
            reporte = DeserializadorAPI.deserializar_clima(datos_json, ciudad=ciudad, fuente=url)
            self._repo.guardar_o_actualizar_clima(reporte)
            return reporte, False, "Datos actualizados en tiempo real desde la API externa."
        except ApiError as error:
            respaldo = self._repo.obtener_ultimo_clima(ciudad)
            if respaldo is not None:
                antiguedad = calcular_antiguedad_texto(respaldo.obtenido_en)
                aviso = (
                    f"[PLAN B - MODO RESPALDO LOCAL] {error} | "
                    f"Mostrando último registro guardado ({antiguedad}, obtenido_en={respaldo.obtenido_en})."
                )
                return respaldo, True, aviso
            raise ApiServicioNoDisponibleError(
                f"{error} Además, aún no existen datos locales guardados para {ciudad}."
            ) from error

    def consultar_indicadores_divisas(
        self,
        codigos: tuple[str, ...] = ("dolar", "euro"),
        url_override: str | None = None,
    ) -> tuple[list[IndicadorEconomico], bool, str]:
        """Retorna (lista_indicadores, es_plan_b, mensaje_estado)."""
        url = url_override or self._url_divisas
        try:
            datos_json = self._cliente.obtener_json(url)
            indicadores = DeserializadorAPI.deserializar_indicadores(datos_json, codigos=codigos, fuente=url)
            for ind in indicadores:
                self._repo.guardar_o_actualizar_indicador(ind)
            return indicadores, False, "Indicadores económicos actualizados desde la API externa."
        except ApiError as error:
            respaldos: list[IndicadorEconomico] = []
            for cod in codigos:
                codigo_db = normalizar_codigo_divisa(cod)
                item = self._repo.obtener_ultimo_indicador(codigo_db)
                if item is not None:
                    respaldos.append(item)
            if respaldos:
                antiguedad = calcular_antiguedad_texto(respaldos[0].obtenido_en)
                aviso = (
                    f"[PLAN B - MODO RESPALDO LOCAL] {error} | "
                    f"Mostrando caché local ({antiguedad}, obtenido_en={respaldos[0].obtenido_en})."
                )
                return respaldos, True, aviso
            raise ApiServicioNoDisponibleError(
                f"{error} Además, no existe caché local previa para los indicadores solicitados."
            ) from error
