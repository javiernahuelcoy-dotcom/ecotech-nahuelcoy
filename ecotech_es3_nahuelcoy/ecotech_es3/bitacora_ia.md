# Bitácora de Auditoría Técnica de IA — Entrega 3 (TI3021)

**Estudiante:** Javier Elías Nahuelcoy Catril  
**Rama Git:** `e3/nahuelcoy`  
**Proyecto:** EcoTech Solutions — Consumo Seguro de APIs, Persistencia Idempotente y Autenticación  

---

## Matriz de Auditoría de las 5 Señales de Riesgo

| # | Señal de Riesgo Auditada | Fragmento Generado por IA (Inicial) | Riesgo Técnico / CWE | Decisión | Corrección Aplicada y Justificación Técnica |
|---|---|---|---|---|---|
| 1 | **`f-strings` / concatenación en SQL** | `cursor.execute(f"SELECT * FROM clima_registro WHERE ciudad = '{ciudad}'")` | **Inyección SQL (CWE-89):** permite alterar la consulta o extraer datos de otras tablas si `ciudad` proviene de entrada externa. | **Descartado y Modificado** | Se reemplazó por consultas 100% parametrizadas con marcadores `?` (`WHERE ciudad = ?`) y `ON CONFLICT(...) DO UPDATE`, heredando de `RepositorioBase` y pasando la auditoría AST de `test_repositorio.py`. |
| 2 | **`verify=False` en peticiones HTTPS** | `requests.get(url, verify=False)` | **Validación impropia de certificados TLS (CWE-295):** expone el tráfico financiero y climático a ataques *Man-in-the-Middle* (MITM). | **Descartado** | Se eliminó `verify=False` y se fijó explícitamente `verify=True` en `ClienteAPI._ejecutar_get()`, garantizando verificación criptográfica de la cadena de confianza SSL/TLS. |
| 3 | **`except: pass` (silenciamiento ciego)** | `try: data = r.json() except: pass` | **Manejo inadecuado de excepciones (CWE-390):** oculta fallos críticos, deja variables sin definir (`NameError`) o provoca caídas aguas abajo sin trazabilidad. | **Descartado y Modificado** | Se reemplazó por captura específica (`requests.Timeout`, `requests.ConnectionError`, `ValueError`), registro controlado en `logging` sin exponer secretos y traducción a excepciones del dominio (`ApiServicioNoDisponibleError`, `DeserializacionError`) que activan el Plan B. |
| 4 | **Llamadas HTTP sin `timeout`** | `requests.get("https://mindicador.cl/api")` | **Consumo incontrolado de recursos (CWE-400):** si el servidor remoto no responde, el hilo queda bloqueado indefinidamente congelando la aplicación. | **Modificado** | Se impuso un *timeout* explícito de tupla `timeout=(3.0, 7.0)` (conexión y lectura) configurable mediante `.env`, más reintentos acotados (máximo 3) con *backoff* exponencial. |
| 5 | **Librerías inexistentes en PyPI** | `import requests_smart_retry` / `from py_bcrypt_fast import hash_secret` | **Alucinación de paquetes / *Slopsquatting* (CWE-829):** riesgo de instalar dependencias inexistentes o maliciosas publicadas por terceros en PyPI. | **Descartado** | Se auditó el índice oficial PyPI y se utilizaron únicamente paquetes oficiales verificados en `requirements.txt`: `requests==2.32.3`, `bcrypt==4.2.1` y `python-dotenv==1.0.1`. |

---

## Decisiones Aceptadas con Refinamiento

- **Estructura de `DeserializadorAPI`:** Se aceptó la separación entre el transporte HTTP (`ClienteAPI`) y la validación de esquema JSON (`DeserializadorAPI`), añadiendo verificación explícita de tipos (`isinstance(..., bool)` excluido de números), rangos físicos de temperatura/humedad y normalización de códigos de moneda (`dolar` -> `USD`, `euro` -> `EUR`).
- **Patrón *UPSERT* para idempotencia:** Se refinó la persistencia local utilizando `INSERT INTO ... ON CONFLICT(codigo, fecha_dato) DO UPDATE` en SQLite para garantizar que ejecuciones consecutivas actualicen el timestamp `obtenido_en` sin duplicar registros.
