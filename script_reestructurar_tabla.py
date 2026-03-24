# script_reestructurar_tabla.py
import sqlite3

DB_NAME = 'barberia.db'

def reestructurar_tabla_barberos():
    """Cambia la tabla barberos para permitir reutilizar IDs"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("🔄 Reestructurando tabla barberos...")
    
    # 1. Crear tabla temporal SIN AUTOINCREMENT
    cursor.execute('''
        CREATE TABLE barberos_temp (
            id INTEGER PRIMARY KEY,
            nombre_usuario TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL,
            nombre_completo TEXT NOT NULL
        )
    ''')
    
    # 2. Copiar datos existentes
    cursor.execute('''
        INSERT INTO barberos_temp (id, nombre_usuario, contraseña, nombre_completo)
        SELECT id, nombre_usuario, contraseña, nombre_completo FROM barberos
    ''')
    
    # 3. Eliminar tabla original
    cursor.execute('DROP TABLE barberos')
    
    # 4. Renombrar temporal a original
    cursor.execute('ALTER TABLE barberos_temp RENAME TO barberos')
    
    conn.commit()
    conn.close()
    
    print("✅ Tabla reestructurada con éxito. Ahora los IDs se pueden reutilizar.")

def verificar_tabla():
    """Muestra la estructura actual de la tabla"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='barberos'")
    estructura = cursor.fetchone()
    conn.close()
    
    print("\n📋 Estructura actual de la tabla barberos:")
    print(estructura[0])

if __name__ == '__main__':
    verificar_tabla()
    respuesta = input("\n¿Quieres reestructurar la tabla para reutilizar IDs? (s/n): ")
    if respuesta.lower() == 's':
        reestructurar_tabla_barberos()
        verificar_tabla()