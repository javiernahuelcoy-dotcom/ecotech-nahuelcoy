"""Pruebas de las clases del dominio (sin base de datos).

Ejecutar desde la carpeta del proyecto:  python -m unittest discover -s pruebas -t . -v
"""
import unittest

from dominio import Departamento, Empleado, Persona, Proyecto
from dominio.excepciones import DatoInvalidoError, RutInvalidoError, SueldoInvalidoError
from dominio.validaciones import normalizar_rut


def empleado_valido(**cambios) -> Empleado:
    datos = dict(rut="12.345.678-5", nombre="Camila Rojas", email="camila@ecotech.cl",
                 cargo="Analista", sueldo_base=1_000_000, fecha_ingreso="2024-03-01")
    datos.update(cambios)
    return Empleado(**datos)


class PruebasRut(unittest.TestCase):
    def test_normaliza_formatos(self):
        for entrada in ("12.345.678-5", "12345678-5", "123456785", " 12345678-5 "):
            self.assertEqual(normalizar_rut(entrada), "12345678-5")

    def test_dv_k(self):
        self.assertEqual(normalizar_rut("10.000.013-k"), "10000013-K")

    def test_dv_incorrecto(self):
        with self.assertRaises(RutInvalidoError):
            normalizar_rut("12.345.678-9")

    def test_formato_invalido(self):
        for entrada in ("", "abc", "' OR '1'='1", "1-9"):
            with self.assertRaises(RutInvalidoError):
                normalizar_rut(entrada)


class PruebasEncapsulamiento(unittest.TestCase):
    def test_persona_es_abstracta(self):
        with self.assertRaises(TypeError):
            Persona("12.345.678-5", "Ana", "ana@ecotech.cl")

    def test_sueldo_negativo_o_cero(self):
        for sueldo in (-1, 0):
            with self.assertRaises(SueldoInvalidoError):
                empleado_valido(sueldo_base=sueldo)

    def test_sueldo_texto(self):
        with self.assertRaises(SueldoInvalidoError):
            empleado_valido(sueldo_base="mucho")

    def test_setter_valida_despues_de_crear(self):
        empleado = empleado_valido()
        with self.assertRaises(SueldoInvalidoError):
            empleado.sueldo_base = -500
        self.assertEqual(empleado.sueldo_base, 1_000_000)  # el valor anterior no se perdió

    def test_email_invalido(self):
        with self.assertRaises(DatoInvalidoError):
            empleado_valido(email="correo-sin-arroba")

    def test_nombre_vacio(self):
        with self.assertRaises(DatoInvalidoError):
            empleado_valido(nombre="   ")

    def test_fecha_futura(self):
        with self.assertRaises(DatoInvalidoError):
            empleado_valido(fecha_ingreso="2999-01-01")

    def test_activo_es_solo_lectura(self):
        empleado = empleado_valido()
        with self.assertRaises(AttributeError):
            empleado.activo = False
        empleado.desactivar()
        self.assertFalse(empleado.activo)


class PruebasHerenciaYPolimorfismo(unittest.TestCase):
    def test_empleado_hereda_de_persona(self):
        empleado = empleado_valido()
        self.assertIsInstance(empleado, Persona)
        self.assertEqual(empleado.rut, "12345678-5")  # validado por el setter heredado

    def test_sueldo_liquido(self):
        self.assertEqual(empleado_valido().calcular_sueldo_liquido(), 800_000)

    def test_resumen_polimorfico(self):
        entidades = [Departamento("TI", 1_000_000, 1), empleado_valido(), Proyecto("Solar", fecha_inicio="2026-01-01")]
        resumenes = [e.resumen() for e in entidades]
        self.assertTrue(resumenes[0].startswith("[Departamento]"))
        self.assertTrue(resumenes[1].startswith("[Empleado]"))
        self.assertTrue(resumenes[2].startswith("[Proyecto]"))

    def test_proyecto_no_repite_empleado(self):
        proyecto = Proyecto("Solar")
        proyecto.agregar_empleado("12.345.678-5")
        with self.assertRaises(DatoInvalidoError):
            proyecto.agregar_empleado("12345678-5")


if __name__ == "__main__":
    unittest.main()
