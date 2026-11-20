"""Modelos de datos externos y deserializador con validación estricta de esquemas JSON."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from dominio.excepciones import DatoInvalidoError, DeserializacionError
from dominio.reportable import Reportable

CIUDADES_PROYECTO: dict[str, tuple[float, float]] = {
    "Santiago": (-33.4489, -70.6693),
    "Concepción": (-36.8201, -73.0444),
    "Valdivia": (-39.8142, -73.2459),
    "Antofagasta": (-23.6509, -70.3975),
    "Puerto Montt": (-41.4693, -72.9424),
}

MAPEO_CODIGOS_DIVISA: dict[str, str] = {
    "dolar": "USD",
    "usd": "USD",
    "euro": "EUR",
    "eur": "EUR",
    "uf": "UF",
}

CODIGOS_WMO: dict[int, str] = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    61: "Lluvia leve",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    80: "Chubascos leves",
    95: "Tormenta eléctrica",
}


def normalizar_codigo_divisa(clave: str) -> str:
    limpio = str(clave).strip().lower()
    return MAPEO_CODIGOS_DIVISA.get(limpio, limpio.upper()[:10])


def calcular_antiguedad_texto(obtenido_en_iso: str) -> str:
    """Devuelve cuánto tiempo ha pasado desde 'obtenido_en' en formato legible."""
    try:
        marca = datetime.fromisoformat(obtenido_en_iso)
        if marca.tzinfo is None:
            marca = marca.replace(tzinfo=timezone.utc)
        segundos = max(0, int((datetime.now(timezone.utc) - marca).total_seconds()))
    except ValueError:
        return "antigüedad desconocida"

    if segundos < 60:
        return f"hace {segundos} s"
    minutos, seg = divmod(segundos, 60)
    if minutos < 60:
        return f"hace {minutos} min {seg} s"
    horas, min_rest = divmod(minutos, 60)
    if horas < 24:
        return f"hace {horas} h {min_rest} min"
    dias = horas // 24
    return f"hace {dias} día(s)"


@dataclass(frozen=True)
class ReporteClima(Reportable):
    ciudad: str
    fecha_consulta: str
    temperatura_c: float
    humedad_relativa: float
    descripcion: str
    viento_kmh: float
    fuente: str
    obtenido_en: str

    def apto_trabajo_exterior(self) -> bool:
        return self.temperatura_c >= 0 and self.viento_kmh <= 45 and "Tormenta" not in self.descripcion

    def resumen(self) -> str:
        estado_op = "APTO faena exterior" if self.apto_trabajo_exterior() else "PRECAUCIÓN climática"
        return (
            f"[Clima]        {self.ciudad:<15} {self.temperatura_c:>5.1f}°C | "
            f"Hum: {self.humedad_relativa:>3.0f}% | Viento: {self.viento_kmh:>4.1f} km/h | "
            f"{self.descripcion} ({estado_op}) [obtenido_en: {self.obtenido_en}]"
        )


@dataclass(frozen=True)
class IndicadorEconomico(Reportable):
    codigo: str
    nombre: str
    valor_clp: float
    unidad: str
    fecha_dato: str
    fuente: str
    obtenido_en: str

    def convertir_desde_clp(self, monto_clp: float) -> float:
        if isinstance(monto_clp, bool) or not isinstance(monto_clp, (int, float)) or monto_clp < 0:
            raise DatoInvalidoError("El monto en CLP debe ser numérico y mayor o igual a cero.")
        return round(monto_clp / self.valor_clp, 2)

    def resumen(self) -> str:
        return (
            f"[Indicador]    {self.codigo:<6} ({self.nombre:<20}) "
            f"1 {self.codigo} = ${self.valor_clp:>10,.2f} CLP | Fecha: {self.fecha_dato} "
            f"[obtenido_en: {self.obtenido_en}]"
        )


class DeserializadorAPI:
    """Valida estructura, tipos y rangos de respuestas JSON antes de instanciar objetos."""

    @staticmethod
    def deserializar_clima(payload: Any, ciudad: str, fuente: str) -> ReporteClima:
        if not isinstance(payload, dict) or "current" not in payload or not isinstance(payload["current"], dict):
            raise DeserializacionError("La respuesta de clima no contiene el bloque 'current' esperado.")

        actual = payload["current"]
        campos = ("temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m")
        for campo in campos:
            if campo not in actual or isinstance(actual[campo], bool) or not isinstance(actual[campo], (int, float)):
                raise DeserializacionError(f"Campo climático inválido o ausente: '{campo}'.")

        temp = float(actual["temperature_2m"])
        humedad = float(actual["relative_humidity_2m"])
        viento = float(actual["wind_speed_10m"])
        codigo_wmo = int(actual["weather_code"])

        if not (-90.0 <= temp <= 60.0):
            raise DeserializacionError(f"Temperatura fuera de rango físico: {temp}°C.")
        if not (0.0 <= humedad <= 100.0):
            raise DeserializacionError(f"Humedad fuera de rango porcentual: {humedad}%.")
        if viento < 0.0:
            raise DeserializacionError(f"Velocidad del viento inválida: {viento}.")

        ahora = datetime.now(timezone.utc)
        descripcion = CODIGOS_WMO.get(codigo_wmo, f"Condición WMO {codigo_wmo}")
        return ReporteClima(
            ciudad=ciudad,
            fecha_consulta=ahora.date().isoformat(),
            temperatura_c=round(temp, 1),
            humedad_relativa=round(humedad, 1),
            descripcion=descripcion,
            viento_kmh=round(viento, 1),
            fuente=fuente,
            obtenido_en=ahora.isoformat(timespec="seconds"),
        )

    @staticmethod
    def deserializar_indicadores(payload: Any, codigos: tuple[str, ...], fuente: str) -> list[IndicadorEconomico]:
        if not isinstance(payload, dict):
            raise DeserializacionError("La respuesta de indicadores económicos no es un objeto JSON.")

        ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        resultados: list[IndicadorEconomico] = []

        for clave in codigos:
            bloque = payload.get(clave)
            if not isinstance(bloque, dict):
                raise DeserializacionError(f"Indicador '{clave}' ausente en la respuesta de la API.")

            valor = bloque.get("valor")
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
                raise DeserializacionError(f"Valor inválido para indicador '{clave}': {valor!r}.")

            codigo_normalizado = normalizar_codigo_divisa(bloque.get("codigo", clave))
            nombre = str(bloque.get("nombre", codigo_normalizado))[:60]
            unidad = str(bloque.get("unidad_medida", "Pesos"))[:30]
            fecha_raw = str(bloque.get("fecha", ahora))[:10]

            resultados.append(
                IndicadorEconomico(
                    codigo=codigo_normalizado,
                    nombre=nombre,
                    valor_clp=round(float(valor), 4),
                    unidad=unidad,
                    fecha_dato=fecha_raw,
                    fuente=fuente,
                    obtenido_en=ahora,
                )
            )
        return resultados
