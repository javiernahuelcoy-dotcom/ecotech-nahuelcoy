"""Pruebas de la capa de persistencia con una base SQLite en memoria.

Incluye la prueba de inyección SQL y la de rollback de la transacción.
"""
import ast
import unittest
from pathlib import Path

from dominio import Departamento, Empleado, Proyecto
from dominio.excepciones import (ReferenciaInvalidaError, RegistroDuplicadoError,
                                 RegistroNoEncontradoError, RutInvalidoError)
from repositorio import DepartamentoRepositorio, EmpleadoRepositorio, ProyectoRepositorio
from repositorio.conexion import inicializar_bd, obtener_conexion

CARPETA_REPOSITORIO = Path(__file__).resolve().parent.parent / "repositorio"


class BaseRepoTest(unittest.TestCase):
    def setUp(self):
        self.conexion = obtener_conexion(":memory:")
        inicializar_bd(self.conexion)
        self.empleados = EmpleadoRepositorio(self.conexion)
        self.departamentos = DepartamentoRepositorio(self.conexion)
        self.proyectos = ProyectoRepositorio(self.conexion)
        self.id_ti = self.departamentos.guardar(Departamento("Tecnología", 50_000_000))
        self.empleados.guardar(Empleado("12.345.678-5", "Camila Rojas", "camila@ecotech.cl",
                                        "Gerente de TI", 2_000_000, "2020-01-01", self.id_ti))
        self.empleados.guardar(Empleado("15.678.234-3", "Diego Muñoz", "diego@ecotech.cl",
                                        "Desarrollador", 1_200_000, "2021-01-01", self.id_ti))

    def tearDown(self):
        self.conexion.close()

    def contar(self, tabla: str) -> int:
        # Nombre de tabla fijo de la prueba (no viene del usuario); los marcadores ? no sirven para nombres de tabla
        consultas = {"persona": "SELECT COUNT(*) FROM persona", "empleado": "SELECT COUNT(*) FROM empleado"}
        return self.conexion.execute(consultas[tabla]).fetchone()[0]


class PruebasCrudEmpleado(BaseRepoTest):
    def test_crear_y_leer(self):
        empleado = self.empleados.obtener_por_rut("12345678-5")
        self.assertEqual(empleado.nombre, "Camila Rojas")
        self.assertEqual(len(self.empleados.listar_activos()), 2)

    def test_actualizar(self):
        empleado = self.empleados.obtener_por_rut("15.678.234-3")
        empleado.sueldo_base = 1_500_000
        empleado.cargo = "Desarrollador Senior"
        self.empleados.actualizar(empleado)
        recargado = self.empleados.obtener_por_rut("15678234-3")
        self.assertEqual(recargado.sueldo_base, 1_500_000)
        self.assertEqual(recargado.cargo, "Desarrollador Senior")

    def test_eliminar_logico(self):
        self.empleados.eliminar("15.678.234-3")
        self.assertEqual(len(self.empleados.listar_activos()), 1)
        self.assertFalse(self.empleados.obtener_por_rut("15678234-3").activo)  # el historial se conserva
        with self.assertRaises(RegistroNoEncontradoError):
            self.empleados.eliminar("15.678.234-3")

    def test_rut_duplicado(self):
        with self.assertRaises(RegistroDuplicadoError):
            self.empleados.guardar(Empleado("12.345.678-5", "Otra Persona", "otra@ecotech.cl", "Analista", 900_000))

    def test_no_encontrado(self):
        with self.assertRaises(RegistroNoEncontradoError):
            self.empleados.obtener_por_rut("11.111.111-1")


class PruebasCrudDepartamentoYProyecto(BaseRepoTest):
    def test_crud_departamento(self):
        nuevo_id = self.departamentos.guardar(Departamento("Finanzas", 10_000_000))
        departamento = self.departamentos.obtener_por_id(nuevo_id)
        departamento.presupuesto = 12_000_000
        self.departamentos.actualizar(departamento)
        self.assertEqual(self.departamentos.obtener_por_id(nuevo_id).presupuesto, 12_000_000)
        self.departamentos.eliminar(nuevo_id)
        with self.assertRaises(RegistroNoEncontradoError):
            self.departamentos.obtener_por_id(nuevo_id)

    def test_no_borra_departamento_con_empleados(self):
        with self.assertRaises(ReferenciaInvalidaError):
            self.departamentos.eliminar(self.id_ti)
        self.assertEqual(len(self.departamentos.listar_todos()), 1)

    def test_crud_proyecto_y_asignaciones(self):
        id_proyecto = self.proyectos.guardar(Proyecto("Paneles Solares", "Planta sur", "2026-01-01",
                                                      ruts_asignados=["12.345.678-5"]))
        self.proyectos.asignar_empleado(id_proyecto, "15.678.234-3")
        self.assertEqual(len(self.proyectos.obtener_por_id(id_proyecto).ruts_asignados), 2)
        with self.assertRaises(RegistroDuplicadoError):
            self.proyectos.asignar_empleado(id_proyecto, "15.678.234-3")
        self.proyectos.quitar_empleado(id_proyecto, "15.678.234-3")
        proyecto = self.proyectos.obtener_por_id(id_proyecto)
        proyecto.nombre = "Paneles Solares Fase 2"
        self.proyectos.actualizar(proyecto)
        self.assertEqual(self.proyectos.obtener_por_id(id_proyecto).nombre, "Paneles Solares Fase 2")
        self.proyectos.eliminar(id_proyecto)
        self.assertEqual(self.proyectos.listar_todos(), [])


class PruebasSeguridad(BaseRepoTest):
    PAYLOAD = "' OR '1'='1"

    def test_inyeccion_en_busqueda_por_nombre(self):
        # Con SQL concatenado este payload devolvería TODOS los empleados.
        # Con parámetros, el motor busca literalmente un nombre que contenga ' OR '1'='1
        self.assertEqual(self.empleados.buscar_por_nombre(self.PAYLOAD), [])
        self.assertEqual(len(self.empleados.listar_activos()), 2)  # los datos siguen intactos

    def test_inyeccion_en_rut_se_rechaza_antes_de_la_bd(self):
        with self.assertRaises(RutInvalidoError):
            self.empleados.obtener_por_rut(self.PAYLOAD)

    def test_ningun_execute_usa_sql_armado(self):
        """Auditoría automática: ninguna consulta del repositorio usa f-string, + o %."""
        for archivo in CARPETA_REPOSITORIO.glob("*.py"):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                        and nodo.func.attr in ("execute", "_consultar_uno", "_consultar_todos") and nodo.args):
                    sql = nodo.args[0]
                    with self.subTest(archivo=archivo.name, linea=nodo.lineno):
                        self.assertNotIsInstance(sql, (ast.JoinedStr, ast.BinOp),
                                                 "Consulta armada con f-string, + o %")


class PruebasTransaccion(BaseRepoTest):
    def test_rollback_si_falla_la_segunda_escritura(self):
        personas_antes = self.contar("persona")
        # El INSERT en persona funciona, pero el INSERT en empleado falla
        # porque el departamento 999 no existe (FOREIGN KEY).
        with self.assertRaises(ReferenciaInvalidaError):
            self.empleados.guardar(Empleado("18.234.567-9", "Valentina Soto", "vale@ecotech.cl",
                                            "Analista", 1_000_000, departamento_id=999))
        # Gracias al rollback no quedó una persona "huérfana"
        self.assertEqual(self.contar("persona"), personas_antes)
        self.assertEqual(self.contar("empleado"), 2)


if __name__ == "__main__":
    unittest.main()
