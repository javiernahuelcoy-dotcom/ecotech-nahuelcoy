-- Esquema relacional de EcoTech Solutions (SQLite 3 - ES2 + ES3)
-- Se ejecuta con inicializar_bd(); es seguro correrlo varias veces (IF NOT EXISTS).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departamento (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL UNIQUE,
    presupuesto  REAL    NOT NULL CHECK (presupuesto >= 0)
);

-- Persona (padre) y Empleado (hijo) reflejan la herencia del diagrama UML
CREATE TABLE IF NOT EXISTS persona (
    rut       TEXT PRIMARY KEY,
    nombre    TEXT NOT NULL,
    email     TEXT NOT NULL,
    telefono  TEXT
);

CREATE TABLE IF NOT EXISTS empleado (
    rut              TEXT    PRIMARY KEY,
    cargo            TEXT    NOT NULL,
    sueldo_base      REAL    NOT NULL CHECK (sueldo_base > 0),
    fecha_ingreso    TEXT    NOT NULL,
    departamento_id  INTEGER,
    activo           INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    FOREIGN KEY (rut)             REFERENCES persona(rut),
    FOREIGN KEY (departamento_id) REFERENCES departamento(id)
);

CREATE TABLE IF NOT EXISTS proyecto (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL UNIQUE,
    descripcion   TEXT,
    fecha_inicio  TEXT NOT NULL
);

-- Tabla intermedia de la relación muchos-a-muchos Empleado <-> Proyecto
CREATE TABLE IF NOT EXISTS asignacion (
    rut_empleado  TEXT    NOT NULL,
    proyecto_id   INTEGER NOT NULL,
    PRIMARY KEY (rut_empleado, proyecto_id),
    FOREIGN KEY (rut_empleado) REFERENCES empleado(rut),
    FOREIGN KEY (proyecto_id)  REFERENCES proyecto(id)
);

-- =====================================================================
-- Tablas Unidad 3: Autenticación y Caché Resiliente de APIs Externas
-- =====================================================================

CREATE TABLE IF NOT EXISTS usuario (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT    NOT NULL UNIQUE,
    password_hash  TEXT    NOT NULL,
    rol            TEXT    NOT NULL CHECK (rol IN ('admin', 'analista')),
    activo         INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS clima_registro (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ciudad            TEXT    NOT NULL,
    fecha_consulta    TEXT    NOT NULL,
    temperatura_c     REAL    NOT NULL,
    humedad_relativa  REAL    NOT NULL,
    descripcion       TEXT    NOT NULL,
    viento_kmh        REAL    NOT NULL,
    fuente            TEXT    NOT NULL,
    obtenido_en       TEXT    NOT NULL,
    UNIQUE (ciudad, fecha_consulta)
);

CREATE TABLE IF NOT EXISTS indicador_economico (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo       TEXT    NOT NULL,
    nombre       TEXT    NOT NULL,
    valor_clp    REAL    NOT NULL CHECK (valor_clp > 0),
    unidad       TEXT    NOT NULL,
    fecha_dato   TEXT    NOT NULL,
    fuente       TEXT    NOT NULL,
    obtenido_en  TEXT    NOT NULL,
    UNIQUE (codigo, fecha_dato)
);
