# EcoTech Solutions — Consumo Seguro de APIs y Resiliencia (ES3 · TI3021)

Extensión individual sobre la base de ES2 que incorpora:
1. **Autenticación segura (`bcrypt`)** con salt criptográfico único por usuario (`dominio/usuario.py`, `repositorio/usuario_repo.py`).
2. **Cliente HTTP resiliente (`api_cliente.py`)** con `timeout=(3.0, 7.0)`, `verify=True`, no-reintento en `4xx`, respeto de `Retry-After` en `429` y reintentos acotados (máximo 3) con backoff exponencial en `5xx` y fallos de red.
3. **Deserialización y persistencia idempotente (`dominio/servicios_externos.py`, `repositorio/indicadores_repo.py`)** mediante validación de esquema JSON y sentencias SQL parametrizadas con `ON CONFLICT(...) DO UPDATE`.
4. **Degradación controlada (Plan B):** respaldo automático desde SQLite indicando antigüedad (`obtenido_en`) ante cortes de red o caídas de APIs.
5. **Auditoría de IA (`bitacora_ia.md`):** revisión técnica de las 5 señales de riesgo.

## Instalación y ejecución
```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # Linux/Mac: cp .env.example .env

# Ejecución de sincronización directa (Pruebas en vivo #1 y #2: idempotencia y Plan B)
python sincronizar_apis.py

# Ejecución del sistema completo con inicio de sesión y menú interactivo
python main.py
```

## Credenciales iniciales de prueba
- **Administrador:** `admin` / `EcoTech2026#Admin`
- **Analista:** `analista` / `EcoTech2026#User`

## Pruebas automáticas y auditoría AST de SQL
```bash
python -m unittest discover -s pruebas -t . -v
```
