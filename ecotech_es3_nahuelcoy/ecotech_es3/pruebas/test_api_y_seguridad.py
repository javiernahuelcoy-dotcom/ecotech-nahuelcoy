"""Pruebas unitarias de cliente HTTP, manejo de códigos, Plan B, idempotencia y bcrypt."""
import unittest
from unittest.mock import MagicMock, patch

import requests

from api_cliente import ClienteAPI, ServicioIntegracionEcoTech
from dominio.excepciones import ApiEndpointInvalidoError, AutenticacionError
from dominio.usuario import Usuario
from repositorio.conexion import inicializar_bd, obtener_conexion
from repositorio.indicadores_repo import IndicadoresRepositorio
from repositorio.usuario_repo import UsuarioRepositorio


def _mock_respuesta(status_code: int, json_data=None, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    if isinstance(json_data, Exception):
        resp.json.side_effect = json_data
    else:
        resp.json.return_value = json_data
    return resp


class PruebasClienteApiYResiliencia(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion(":memory:")
        inicializar_bd(self.conexion)
        self.repo_ind = IndicadoresRepositorio(self.conexion)

    def tearDown(self):
        self.conexion.close()

    @patch("api_cliente.time.sleep")
    def test_404_no_reintenta(self, mock_sleep):
        sesion = MagicMock()
        sesion.get.return_value = _mock_respuesta(404)
        cliente = ClienteAPI(max_intentos=3, sesion=sesion)

        with self.assertRaises(ApiEndpointInvalidoError):
            cliente.obtener_json("https://api.ejemplo.cl/ruta-inexistente")

        self.assertEqual(sesion.get.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("api_cliente.time.sleep")
    def test_429_respeta_retry_after(self, mock_sleep):
        sesion = MagicMock()
        sesion.get.side_effect = [
            _mock_respuesta(429, headers={"Retry-After": "4"}),
            _mock_respuesta(200, json_data={"ok": True}),
        ]
        cliente = ClienteAPI(max_intentos=3, sesion=sesion)
        resultado = cliente.obtener_json("https://api.ejemplo.cl/datos")

        self.assertEqual(resultado, {"ok": True})
        self.assertEqual(sesion.get.call_count, 2)
        mock_sleep.assert_called_once_with(4.0)

    @patch("api_cliente.time.sleep")
    def test_503_reintenta_con_backoff_y_activa_plan_b(self, mock_sleep):
        sesion = MagicMock()
        payload_ok = {
            "current": {
                "temperature_2m": 21.5,
                "relative_humidity_2m": 55,
                "weather_code": 1,
                "wind_speed_10m": 12.0,
            }
        }
        sesion.get.return_value = _mock_respuesta(200, json_data=payload_ok)
        servicio = ServicioIntegracionEcoTech(self.repo_ind, ClienteAPI(max_intentos=3, backoff_base=1.0, sesion=sesion))
        clima_online, es_plan_b, _ = servicio.consultar_clima_proyecto("Santiago")
        self.assertFalse(es_plan_b)
        self.assertEqual(clima_online.temperatura_c, 21.5)

        sesion.get.reset_mock()
        sesion.get.side_effect = [_mock_respuesta(503), _mock_respuesta(503), _mock_respuesta(503)]
        clima_offline, es_plan_b_2, aviso = servicio.consultar_clima_proyecto("Santiago")

        self.assertTrue(es_plan_b_2)
        self.assertEqual(clima_offline.temperatura_c, 21.5)
        self.assertIn("PLAN B", aviso)
        self.assertIn("obtenido_en=", aviso)
        self.assertEqual(sesion.get.call_count, 3)
        self.assertEqual([c.args[0] for c in mock_sleep.call_args_list], [1.0, 2.0])

    @patch("api_cliente.time.sleep")
    def test_corte_red_activa_plan_b_e_idempotencia_con_mindicador_real(self, _mock_sleep):
        sesion = MagicMock()
        payload_divisas = {
            "dolar": {"codigo": "dolar", "nombre": "Dólar observado", "valor": 950.5, "fecha": "2026-11-20T03:00:00.000Z"},
            "euro": {"codigo": "euro", "nombre": "Euro", "valor": 1030.2, "fecha": "2026-11-20T03:00:00.000Z"},
        }
        sesion.get.return_value = _mock_respuesta(200, json_data=payload_divisas)
        servicio = ServicioIntegracionEcoTech(self.repo_ind, ClienteAPI(max_intentos=3, sesion=sesion))

        servicio.consultar_indicadores_divisas(("dolar", "euro"))
        servicio.consultar_indicadores_divisas(("dolar", "euro"))
        total = self.conexion.execute("SELECT COUNT(*) FROM indicador_economico").fetchone()[0]
        self.assertEqual(total, 2)

        sesion.get.side_effect = requests.ConnectionError("Sin conexión a Internet")
        respaldo, es_plan_b, aviso = servicio.consultar_indicadores_divisas(("dolar", "euro"))
        self.assertTrue(es_plan_b)
        self.assertEqual(len(respaldo), 2)
        self.assertEqual({r.codigo for r in respaldo}, {"USD", "EUR"})
        self.assertIn("PLAN B", aviso)


class PruebasSeguridadUsuarios(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion(":memory:")
        inicializar_bd(self.conexion)
        self.repo_usuarios = UsuarioRepositorio(self.conexion)

    def tearDown(self):
        self.conexion.close()

    def test_password_hasheada_con_salt_unico(self):
        u1 = Usuario.crear_nuevo("user1", "ClaveSegura2026!", "analista")
        u2 = Usuario.crear_nuevo("user2", "ClaveSegura2026!", "analista")
        self.repo_usuarios.guardar(u1)
        self.repo_usuarios.guardar(u2)

        self.assertNotIn("ClaveSegura2026!", u1.password_hash)
        self.assertTrue(u1.password_hash.startswith("$2b$"))
        self.assertNotEqual(u1.password_hash, u2.password_hash)

        autenticado = self.repo_usuarios.autenticar("user1", "ClaveSegura2026!")
        self.assertEqual(autenticado.username, "user1")

        with self.assertRaises(AutenticacionError):
            self.repo_usuarios.autenticar("user1", "ClaveIncorrecta")
