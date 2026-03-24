#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCRIPT PARA GESTIONAR BARBEROS (CON REUTILIZACIÓN DE IDs)
Uso: python gestionar_barberos.py
"""

import sqlite3
import sys

DB_NAME = 'barberia.db'

def conectar():
    """Conecta a la base de datos"""
    try:
        conn = sqlite3.connect(DB_NAME)
        return conn
    except sqlite3.Error as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        sys.exit(1)

def verificar_tabla():
    """Verifica que la tabla barberos exista"""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='barberos'
    ''')
    existe = cursor.fetchone()
    conn.close()
    
    if not existe:
        print("❌ La tabla 'barberos' no existe.")
        print("   Ejecuta primero la aplicación para crear las tablas.")
        sys.exit(1)

def obtener_siguiente_id():
    """
    Obtiene el ID más bajo disponible (reutiliza IDs eliminados)
    Si no hay huecos, devuelve el máximo + 1
    """
    conn = conectar()
    cursor = conn.cursor()
    
    # Buscar el ID más bajo que NO esté ocupado
    cursor.execute('''
        SELECT id FROM barberos ORDER BY id
    ''')
    ids_ocupados = [fila[0] for fila in cursor.fetchall()]
    
    if not ids_ocupados:
        return 1
    
    # Buscar el primer hueco
    for i in range(1, max(ids_ocupados) + 2):
        if i not in ids_ocupados:
            conn.close()
            return i
    
    conn.close()
    return max(ids_ocupados) + 1

def listar_barberos():
    """Muestra todos los barberos existentes"""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nombre_usuario, nombre_completo 
        FROM barberos 
        ORDER BY id
    ''')
    barberos = cursor.fetchall()
    conn.close()
    
    if barberos:
        print("\n📋 BARBEROS REGISTRADOS:")
        print("-" * 70)
        print(f"{'ID':<5} {'USUARIO':<15} {'NOMBRE COMPLETO':<30} {'CORTES':<10}")
        print("-" * 70)
        
        for id_barbero, usuario, nombre in barberos:
            # Contar cortes del barbero
            conn2 = conectar()
            cursor2 = conn2.cursor()
            cursor2.execute('SELECT COUNT(*) FROM cortes WHERE barbero_id = ?', (id_barbero,))
            total_cortes = cursor2.fetchone()[0]
            conn2.close()
            
            print(f"{id_barbero:<5} {usuario:<15} {nombre:<30} {total_cortes:<10}")
        
        print("-" * 70)
        print(f"Total: {len(barberos)} barbero(s)")
    else:
        print("\n📋 No hay barberos registrados aún.")
    
    return barberos

def agregar_barbero():
    """Agrega un nuevo barbero REUTILIZANDO IDs libres"""
    print("\n" + "="*70)
    print("   ➕ AGREGAR NUEVO BARBERO")
    print("="*70)
    
    # Datos del barbero
    nombre_completo = input("👤 Nombre completo: ").strip()
    if not nombre_completo:
        print("❌ El nombre no puede estar vacío")
        return False
    
    nombre_usuario = input("🔑 Nombre de usuario: ").strip()
    if not nombre_usuario:
        print("❌ El usuario no puede estar vacío")
        return False
    
    # Verificar si el usuario ya existe
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM barberos WHERE nombre_usuario = ?', (nombre_usuario,))
    if cursor.fetchone():
        print(f"❌ El usuario '{nombre_usuario}' ya existe")
        conn.close()
        return False
    
    # Contraseña VISIBLE
    contraseña = input("🔐 Contraseña (visible): ").strip()
    if not contraseña:
        print("❌ La contraseña no puede estar vacía")
        conn.close()
        return False
    
    # Obtener el siguiente ID disponible
    nuevo_id = obtener_siguiente_id()
    
    # Insertar en la base de datos con el ID específico
    try:
        cursor.execute('''
            INSERT INTO barberos (id, nombre_usuario, contraseña, nombre_completo)
            VALUES (?, ?, ?, ?)
        ''', (nuevo_id, nombre_usuario, contraseña, nombre_completo))
        
        conn.commit()
        print(f"\n✅ ¡Barbero agregado con éxito! ID asignado: {nuevo_id}")
        
    except sqlite3.Error as e:
        print(f"❌ Error al agregar: {e}")
        return False
    finally:
        conn.close()
    
    return True

def eliminar_barbero():
    """Elimina un barbero y reutiliza su ID después"""
    print("\n" + "="*70)
    print("   🗑️ ELIMINAR BARBERO")
    print("="*70)
    
    # Mostrar lista primero
    barberos = listar_barberos()
    if not barberos:
        return False
    
    try:
        id_eliminar = input("\n🔍 Ingresa el ID del barbero a eliminar: ").strip()
        if not id_eliminar.isdigit():
            print("❌ Debes ingresar un número válido")
            return False
        
        id_eliminar = int(id_eliminar)
        
        # Buscar el barbero
        barbero_seleccionado = None
        for b in barberos:
            if b[0] == id_eliminar:
                barbero_seleccionado = b
                break
        
        if not barbero_seleccionado:
            print(f"❌ No existe un barbero con ID {id_eliminar}")
            return False
        
        # Confirmar eliminación
        print(f"\n⚠️ ¿Estás seguro de eliminar a:")
        print(f"   ID: {barbero_seleccionado[0]}")
        print(f"   Usuario: {barbero_seleccionado[1]}")
        print(f"   Nombre: {barbero_seleccionado[2]}")
        
        confirmar = input("\n❓ Escribe 'SI' para confirmar: ").strip()
        if confirmar != 'SI':
            print("❌ Eliminación cancelada")
            return False
        
        # Verificar si tiene cortes asociados
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cortes WHERE barbero_id = ?', (id_eliminar,))
        total_cortes = cursor.fetchone()[0]
        
        if total_cortes > 0:
            print(f"⚠️ Este barbero tiene {total_cortes} corte(s) registrado(s).")
            print("   Si lo eliminas, también se eliminarán sus cortes del ranking.")
            confirmar_cortes = input("❓ ¿Continuar de todas formas? (SI/NO): ").strip()
            if confirmar_cortes != 'SI':
                print("❌ Eliminación cancelada")
                conn.close()
                return False
            
            # Eliminar primero los cortes asociados
            cursor.execute('DELETE FROM cortes WHERE barbero_id = ?', (id_eliminar,))
            print(f"   🗑️ Se eliminaron {total_cortes} corte(s) asociados.")
        
        # Eliminar el barbero
        cursor.execute('DELETE FROM barberos WHERE id = ?', (id_eliminar,))
        conn.commit()
        conn.close()
        
        print(f"\n✅ ¡Barbero eliminado con éxito!")
        print(f"   El ID {id_eliminar} quedará disponible para futuros barberos.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al eliminar: {e}")
        return False

def menu_principal():
    """Muestra el menú principal"""
    while True:
        print("\n" + "="*70)
        print("   🏆 GESTIÓN DE BARBEROS (IDs Reutilizables)")
        print("="*70)
        print("1. 📋 Listar barberos")
        print("2. ➕ Agregar nuevo barbero (reutiliza IDs)")
        print("3. 🗑️ Eliminar barbero")
        print("4. ❌ Salir")
        print("-" * 70)
        
        opcion = input("Selecciona una opción (1-4): ").strip()
        
        if opcion == '1':
            listar_barberos()
        elif opcion == '2':
            agregar_barbero()
        elif opcion == '3':
            eliminar_barbero()
        elif opcion == '4':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")

# ---------- PROGRAMA PRINCIPAL ----------
if __name__ == '__main__':
    verificar_tabla()
    menu_principal()