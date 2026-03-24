import sqlite3
import os

DB_NAME = "barberia.db"

def conectar():
    return sqlite3.connect(DB_NAME)

def crear_tablas():
    conn = conectar()
    cursor = conn.cursor()

    # Tabla de BARBEROS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barberos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de CLIENTES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de cortes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barbero_id INTEGER NOT NULL,
            cliente_id INTEGER,
            nombre_corte TEXT NOT NULL,
            tiempo_segundos INTEGER NOT NULL,
            ruta_video TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (barbero_id) REFERENCES barberos (id),
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # Tabla de fidelidad (solo para clientes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fidelidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER UNIQUE NOT NULL,
            cortes_acumulados INTEGER DEFAULT 0,
            cortes_gratis_recibidos INTEGER DEFAULT 0,
            ultimo_corte TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # Tabla de citas/reservas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            barbero_id INTEGER,
            fecha_hora TIMESTAMP,
            codigo_qr TEXT UNIQUE,
            estado TEXT DEFAULT 'pendiente',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id),
            FOREIGN KEY (barbero_id) REFERENCES barberos (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Tablas creadas/verificadas correctamente.")

def insertar_barbero_inicial():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO barberos (nombre_usuario, contraseña, nombre_completo)
            VALUES (?, ?, ?)
        ''', ('barbero1', '1234', 'Juan Pérez'))
        conn.commit()
        print("Barbero de prueba insertado.")
    except sqlite3.IntegrityError:
        print("El barbero de prueba ya existe.")

    conn.close()

def insertar_cliente_prueba():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO clientes (nombre_usuario, contraseña, nombre_completo)
            VALUES (?, ?, ?)
        ''', ('cliente1', '1234', 'Carlos López'))
        conn.commit()
        
        # Inicializar fidelidad
        cursor.execute('SELECT id FROM clientes WHERE nombre_usuario = "cliente1"')
        cliente_id = cursor.fetchone()[0]
        cursor.execute('INSERT OR IGNORE INTO fidelidad (cliente_id) VALUES (?)', (cliente_id,))
        conn.commit()
        print("Cliente de prueba insertado.")
    except sqlite3.IntegrityError:
        print("El cliente de prueba ya existe.")

    conn.close()

def init_fidelidad():
    """Inicializa la tabla de fidelidad para clientes existentes"""
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO fidelidad (cliente_id)
        SELECT id FROM clientes
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Inicializando base de datos...")
    crear_tablas()
    insertar_barbero_inicial()
    insertar_cliente_prueba()
    init_fidelidad()
    print("¡Listo!")