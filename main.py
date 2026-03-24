import sqlite3
import os
import datetime
import re
import random
import string
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from plyer import camera
from plyer import storagepath
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

# IMPORTACIÓN EXPLÍCITA
from kivy.uix import textinput

Window.size = (400, 700)

# ---------- BASE DE DATOS ----------
def conectar():
    return sqlite3.connect('barberia.db')

def crear_tablas():
    conn = conectar()
    cursor = conn.cursor()
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codigos_servicio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            codigo TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_uso TIMESTAMP,
            usado INTEGER DEFAULT 0,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    conn.commit()
    conn.close()

def insertar_barbero_inicial():
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO barberos (nombre_usuario, contraseña, nombre_completo)
            VALUES (?, ?, ?)
        ''', ('barbero1', '1234', 'Juan Pérez'))
        conn.commit()
    except:
        pass
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
        cursor.execute('SELECT id FROM clientes WHERE nombre_usuario = "cliente1"')
        cliente_id = cursor.fetchone()[0]
        cursor.execute('INSERT OR IGNORE INTO fidelidad (cliente_id) VALUES (?)', (cliente_id,))
        conn.commit()
    except:
        pass
    conn.close()

crear_tablas()
insertar_barbero_inicial()
insertar_cliente_prueba()

# ---------- PANTALLA LOGIN ----------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validar_login(self):
        usuario = self.ids.usuario.text
        contraseña = self.ids.contraseña.text

        if not usuario or not contraseña:
            self.mostrar_popup('Error', 'Completa todos los campos')
            return

        try:
            conn = conectar()
            cursor = conn.cursor()
            
            # Buscar en barberos
            cursor.execute('''
                SELECT id, nombre_completo, 'barbero' as rol FROM barberos 
                WHERE nombre_usuario = ? AND contraseña = ?
            ''', (usuario, contraseña))
            usuario_data = cursor.fetchone()
            
            # Si no está en barberos, buscar en clientes
            if not usuario_data:
                cursor.execute('''
                    SELECT id, nombre_completo, 'cliente' as rol FROM clientes 
                    WHERE nombre_usuario = ? AND contraseña = ?
                ''', (usuario, contraseña))
                usuario_data = cursor.fetchone()
            
            conn.close()

            if usuario_data:
                self.manager.current_user = {
                    'id': usuario_data[0],
                    'nombre': usuario_data[1],
                    'rol': usuario_data[2],
                    'usuario': usuario
                }
                self.manager.current = 'principal'
                self.ids.usuario.text = ''
                self.ids.contraseña.text = ''
                print(f"DEBUG: Login exitoso como {usuario_data[2]}")
            else:
                self.mostrar_popup('Error', 'Usuario o contraseña incorrectos')
        except Exception as e:
            self.mostrar_popup('Error de sistema', f'Error: {str(e)}')

    def mostrar_popup(self, titulo, mensaje):
        popup = Popup(title=titulo, content=Label(text=mensaje), size_hint=(0.8, 0.3))
        popup.open()

    def ir_registro(self):
        self.manager.current = 'registro'


# ---------- PANTALLA DE REGISTRO (SOLO CLIENTES) ----------
class RegistroScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def registrar(self):
        nombre_usuario = self.ids.nombre_usuario.text.strip()
        contraseña = self.ids.contraseña.text.strip()
        confirmar = self.ids.confirmar.text.strip()
        nombre_completo = self.ids.nombre_completo.text.strip()
        email = self.ids.email.text.strip()
        telefono = self.ids.telefono.text.strip()

        if not all([nombre_usuario, contraseña, nombre_completo]):
            self.mostrar_popup('Error', 'Completa los campos obligatorios')
            return

        if contraseña != confirmar:
            self.mostrar_popup('Error', 'Las contraseñas no coinciden')
            return

        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO clientes (nombre_usuario, contraseña, nombre_completo, email, telefono)
                VALUES (?, ?, ?, ?, ?)
            ''', (nombre_usuario, contraseña, nombre_completo, email, telefono))
            conn.commit()
            
            # Inicializar fidelidad
            cliente_id = cursor.lastrowid
            cursor.execute('INSERT INTO fidelidad (cliente_id) VALUES (?)', (cliente_id,))
            conn.commit()
            conn.close()

            self.mostrar_popup('Éxito', 'Registro completado. ¡Ya puedes iniciar sesión!')
            self.manager.current = 'login'
        except sqlite3.IntegrityError:
            self.mostrar_popup('Error', 'El nombre de usuario ya existe')
        except Exception as e:
            self.mostrar_popup('Error', f'Error: {str(e)}')

    def volver_login(self):
        self.manager.current = 'login'

    def mostrar_popup(self, titulo, mensaje):
        popup = Popup(title=titulo, content=Label(text=mensaje), size_hint=(0.8, 0.3))
        popup.open()


# ---------- PANTALLA PRINCIPAL (con menú según rol) ----------
# ---------- PANTALLA PRINCIPAL (con menú según rol) ----------
class PrincipalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pestana_actual = None
        Clock.schedule_once(lambda dt: self.cargar_menu_segun_rol(), 0.1)

    def cargar_menu_segun_rol(self):
        # Verificar que current_user existe
        if not hasattr(self.manager, 'current_user'):
            self.manager.current = 'login'
            return
        
        # Verificar que tiene rol
        if 'rol' not in self.manager.current_user:
            self.manager.current = 'login'
            return
        
        # Mostrar menú según rol
        rol = self.manager.current_user['rol']
        print(f"DEBUG: Rol detectado = '{rol}'")
        
        if rol == 'barbero':
            print("DEBUG: Ejecutando menú BARBERO")
            self.mostrar_nuevo_corte_barbero()
        elif rol == 'cliente':
            print("DEBUG: Ejecutando menú CLIENTE")
            self.mostrar_tarjeta_fidelidad()
        else:
            print(f"DEBUG: Rol desconocido: {rol}")
            self.manager.current = 'login'

    def resetear_colores_botones(self):
        self.ids.btn_barberos.background_color = (0.3, 0.3, 0.3, 1)
        self.ids.btn_cortes.background_color = (0.3, 0.3, 0.3, 1)
        self.ids.btn_nuevo.background_color = (0.9, 0.2, 0.2, 1)

    # ========== MÉTODOS PARA BARBERO ==========
    def mostrar_nuevo_corte_barbero(self):
        """Barbero: muestra opciones para nuevo corte o escanear QR"""
        self.resetear_colores_botones()
        self.ids.contenido.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        
        img_titulo = Image(
            source='images/decoraciones/Titulo_Nuevo_Corte.png',
            size_hint_y=None,
            height=80,
            keep_ratio=True,
            allow_stretch=True
        )
        layout.add_widget(img_titulo)
        
        # Botón para registrar servicio (QR o código)
        btn_registrar = Button(
            text='📷 REGISTRAR SERVICIO (QR / CÓDIGO)',
            font_size=20,
            size_hint_y=None,
            height=80,
            background_color=(0.3, 0.3, 0.8, 1),
            background_normal=''
        )
        btn_registrar.bind(on_press=lambda x: self.registrar_servicio())
        layout.add_widget(btn_registrar)
        
        # Separador
        layout.add_widget(Label(
            text='O',
            font_size=18,
            size_hint_y=None,
            height=30,
            color=(0.8, 0.8, 0.8, 1)
        ))
        
        # Botón para iniciar corte manual
        btn_grande = Button(
            background_normal='images/botones/Botón_Comenzar_Normal.png',
            background_down='images/botones/Botón_Comenzar_Pressed.png',
            text='',
            size_hint_y=None,
            height=80,
            border=(0,0,0,0)
        )
        btn_grande.bind(on_press=lambda x: self.iniciar_nuevo_corte())
        layout.add_widget(btn_grande)
        
        self.ids.contenido.add_widget(layout)
    
    def registrar_servicio(self):
        """Barbero: ventana para registrar servicio (QR real o código manual)"""
        from kivy.uix.camera import Camera
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Título
        content.add_widget(Label(
            text='REGISTRAR SERVICIO',
            font_size=20,
            color=(0.9, 0.2, 0.2, 1),
            size_hint_y=None,
            height=50
        ))
        
        # Pestañas
        tp = TabbedPanel(size_hint_y=0.7, do_default_tab=False)
        
        # Pestaña QR con CÁMARA REAL
        tab_qr = TabbedPanelItem(text='📷 QR (CÁMARA)')
        qr_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Instrucciones
        qr_layout.add_widget(Label(
            text='Apunta la cámara al código QR del cliente',
            font_size=14,
            size_hint_y=None,
            height=40
        ))
        
        # Vista previa de cámara
        self.camera_widget = Camera(resolution=(640, 480), size_hint=(1, 0.6))
        qr_layout.add_widget(self.camera_widget)
        
        # Botón para capturar
        btn_capturar = Button(
            text='CAPTURAR QR',
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        btn_capturar.bind(on_press=lambda x: self.capturar_qr())
        qr_layout.add_widget(btn_capturar)
        
        # Resultado de escaneo
        self.qr_resultado = Label(
            text='Esperando escaneo...',
            font_size=12,
            size_hint_y=None,
            height=40
        )
        qr_layout.add_widget(self.qr_resultado)
        
        tab_qr.add_widget(qr_layout)
        
        # Pestaña QR Manual (fallback)
        tab_qr_manual = TabbedPanelItem(text='📱 QR MANUAL')
        qr_manual_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        qr_manual_layout.add_widget(Label(
            text='Ingresa el código QR manualmente',
            font_size=14,
            size_hint_y=None,
            height=30
        ))
        self.qr_manual_input = TextInput(
            hint_text='BARBERIA_POLAR|CLIENTE|ID|NOMBRE',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        qr_manual_layout.add_widget(self.qr_manual_input)
        tab_qr_manual.add_widget(qr_manual_layout)
        
        # Pestaña Código de 6 dígitos
        tab_codigo = TabbedPanelItem(text='🔢 CÓDIGO')
        codigo_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        codigo_layout.add_widget(Label(
            text='Ingresa el código de 6 dígitos del cliente',
            font_size=14,
            size_hint_y=None,
            height=30
        ))
        self.codigo_input = TextInput(
            hint_text='Ej: A3B9X2',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        codigo_layout.add_widget(self.codigo_input)
        tab_codigo.add_widget(codigo_layout)
        
        tp.add_widget(tab_qr)
        tp.add_widget(tab_qr_manual)
        tp.add_widget(tab_codigo)
        content.add_widget(tp)
        
        # Resultado general
        self.servicio_resultado = Label(
            text='',
            font_size=14,
            size_hint_y=None,
            height=40
        )
        content.add_widget(self.servicio_resultado)
        
        # Botones
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_procesar = Button(text='PROCESAR', background_color=(0.2, 0.8, 0.2, 1))
        btn_cancelar = Button(text='CANCELAR', background_color=(0.8, 0.2, 0.2, 1))
        btn_layout.add_widget(btn_procesar)
        btn_layout.add_widget(btn_cancelar)
        content.add_widget(btn_layout)
        
        self.servicio_popup = Popup(title='Registrar Servicio', content=content, size_hint=(0.95, 0.9), auto_dismiss=False)
        
        def procesar(instance):
            if tp.current_tab.text == '📷 QR (CÁMARA)':
                # Ya se procesa con capturar_qr
                pass
            elif tp.current_tab.text == '📱 QR MANUAL':
                codigo = self.qr_manual_input.text.strip()
                if codigo:
                    self.procesar_qr(codigo)
                else:
                    self.servicio_resultado.text = '❌ Ingresa un código QR'
                    self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)
            else:
                codigo = self.codigo_input.text.strip().upper()
                if codigo and len(codigo) == 6:
                    self.procesar_codigo_servicio(codigo)
                else:
                    self.servicio_resultado.text = '❌ Ingresa un código válido de 6 caracteres'
                    self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)
        
        def cancelar(instance):
            self.servicio_popup.dismiss()
        
        btn_procesar.bind(on_press=procesar)
        btn_cancelar.bind(on_press=cancelar)
        
        self.servicio_popup.open()

    def capturar_qr(self):
        """Captura y procesa el QR desde la cámara"""
        try:
            from PIL import Image as PILImage
            from pyzbar.pyzbar import decode
            
            # Capturar el frame actual de la cámara
            self.camera_widget.export_to_png('temp_qr.png')
            
            # Leer y decodificar QR
            img = PILImage.open('temp_qr.png')
            decoded_objects = decode(img)
            
            if decoded_objects:
                codigo = decoded_objects[0].data.decode('utf-8')
                self.qr_resultado.text = f'✅ QR detectado!'
                self.qr_resultado.color = (0.2, 0.8, 0.2, 1)
                self.procesar_qr(codigo)
            else:
                self.qr_resultado.text = '❌ No se detectó ningún QR. Intenta de nuevo.'
                self.qr_resultado.color = (0.9, 0.2, 0.2, 1)
            
            # Limpiar archivo temporal
            if os.path.exists('temp_qr.png'):
                os.remove('temp_qr.png')
                
        except Exception as e:
            self.qr_resultado.text = f'Error al escanear: {str(e)[:40]}'
            self.qr_resultado.color = (0.9, 0.2, 0.2, 1)

    def procesar_qr(self, codigo_qr):
        """Procesa el QR escaneado"""
        match = re.search(r'CLIENTE\|(\d+)', codigo_qr)
        if match:
            cliente_id = int(match.group(1))
            self.registrar_corte_por_cliente(cliente_id, codigo_qr, 'QR')
        else:
            self.servicio_resultado.text = '❌ QR inválido'
            self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)

    def procesar_codigo_servicio(self, codigo):
        """Procesa un código de servicio de 6 dígitos de un solo uso"""
        try:
            conn = conectar()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cliente_id, usado FROM codigos_servicio 
                WHERE codigo = ? AND usado = 0
            ''', (codigo,))
            codigo_data = cursor.fetchone()
            
            if codigo_data:
                cliente_id = codigo_data[0]
                self.registrar_corte_por_cliente(cliente_id, codigo, 'CÓDIGO')
                
                # Marcar el código como usado
                cursor.execute('''
                    UPDATE codigos_servicio SET usado = 1, fecha_uso = ?
                    WHERE codigo = ?
                ''', (datetime.datetime.now(), codigo))
                conn.commit()
            else:
                self.servicio_resultado.text = '❌ Código inválido o ya utilizado'
                self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)
                
            conn.close()
            
        except Exception as e:
            self.servicio_resultado.text = f'Error: {str(e)}'
            self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)

    def registrar_corte_por_cliente(self, cliente_id, codigo_origen, tipo):
        """Registra un corte para un cliente y actualiza su fidelidad"""
        try:
            conn = conectar()
            cursor = conn.cursor()
            
            # Obtener información del cliente
            cursor.execute('SELECT nombre_completo FROM clientes WHERE id = ?', (cliente_id,))
            cliente = cursor.fetchone()
            
            if cliente:
                # Obtener fidelidad actual
                cursor.execute('SELECT cortes_acumulados, cortes_gratis_recibidos FROM fidelidad WHERE cliente_id = ?', (cliente_id,))
                fidelidad = cursor.fetchone()
                
                if fidelidad:
                    cortes_actuales = fidelidad[0]
                    gratis_recibidos = fidelidad[1]
                    
                    # Verificar si tiene corte gratis pendiente
                    if cortes_actuales >= 4:
                        nuevos_cortes = cortes_actuales - 4
                        nuevos_gratis = gratis_recibidos + 1
                        mensaje = f'✅ ¡Corte GRATIS canjeado para {cliente[0]}!'
                    else:
                        nuevos_cortes = cortes_actuales + 1
                        nuevos_gratis = gratis_recibidos
                        mensaje = f'✅ Corte registrado para {cliente[0]}'
                    
                    # Actualizar fidelidad
                    cursor.execute('''
                        UPDATE fidelidad 
                        SET cortes_acumulados = ?, cortes_gratis_recibidos = ?, ultimo_corte = ?
                        WHERE cliente_id = ?
                    ''', (nuevos_cortes, nuevos_gratis, datetime.datetime.now(), cliente_id))
                    
                    # Registrar el corte
                    cursor.execute('''
                        INSERT INTO cortes (barbero_id, cliente_id, nombre_corte, tiempo_segundos, ruta_video)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (self.manager.current_user['id'], cliente_id, f'{tipo} - Corte', 0, codigo_origen))
                    
                    conn.commit()
                    self.servicio_resultado.text = mensaje
                    self.servicio_resultado.color = (0.2, 0.8, 0.2, 1)
                    
                    # Cerrar popup después de 2 segundos
                    Clock.schedule_once(lambda dt: self.servicio_popup.dismiss(), 2)
                else:
                    self.servicio_resultado.text = '❌ Cliente sin tarjeta de fidelidad'
                    self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)
            else:
                self.servicio_resultado.text = '❌ Cliente no encontrado'
                self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)
                
            conn.close()
            
        except Exception as e:
            self.servicio_resultado.text = f'Error: {str(e)}'
            self.servicio_resultado.color = (0.9, 0.2, 0.2, 1)

    def mostrar_barberos_barbero(self):
        self.resetear_colores_botones()
        self.ids.btn_barberos.background_color = (0.6, 0.6, 0.6, 1)
        self.ids.contenido.clear_widgets()

        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        img_titulo = Image(
            source='images/decoraciones/Titulo_Barberos.png',
            size_hint_y=None,
            height=80,
            keep_ratio=True,
            allow_stretch=True
        )
        layout.add_widget(img_titulo)

        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('SELECT nombre_completo FROM barberos ORDER BY nombre_completo ASC')
            barberos = [fila[0] for fila in cursor.fetchall()]
            conn.close()
        except:
            barberos = ['Error cargando datos']

        if not barberos:
            barberos = ['No hay barberos registrados']

        self.spinner_barberos = Spinner(
            text='Selecciona un barbero',
            values=barberos,
            size_hint_y=None,
            height=45,
            background_color=(0.3, 0.3, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        self.spinner_barberos.bind(text=self.mostrar_estadisticas_barbero)
        layout.add_widget(self.spinner_barberos)

        self.resultado_barberos = Label(
            text='Selecciona un barbero para ver sus estadísticas',
            size_hint_y=None,
            height=300,
            halign='left',
            valign='top',
            text_size=(Window.width - 40, None)
        )
        layout.add_widget(self.resultado_barberos)
        self.ids.contenido.add_widget(layout)

    def mostrar_estadisticas_barbero(self, spinner, text):
        if text in ['Selecciona un barbero', 'No hay barberos registrados', 'Error cargando datos']:
            self.resultado_barberos.text = 'Selecciona un barbero para ver sus estadísticas'
            return

        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.nombre_corte, c.tiempo_segundos
                FROM cortes c
                JOIN barberos b ON c.barbero_id = b.id
                WHERE b.nombre_completo = ?
                ORDER BY c.tiempo_segundos ASC
            ''', (text,))
            filas = cursor.fetchall()
            conn.close()

            if not filas:
                self.resultado_barberos.text = f'{text} aún no tiene cortes registrados'
                return

            total = len(filas)
            suma = sum(t for _, t in filas)
            promedio = suma // total if total > 0 else 0
            mejor_tiempo = min(t for _, t in filas)
            mejor_corte = next((c for c, t in filas if t == mejor_tiempo), "")

            texto = f"📊 ESTADÍSTICAS DE {text.upper()}\n"
            texto += "="*30 + "\n"
            texto += f"📌 Cortes realizados: {total}\n"
            texto += f"⏱️ Tiempo promedio: {promedio//60:02d}:{promedio%60:02d}\n"
            texto += f"🏆 Mejor corte: {mejor_corte} en {mejor_tiempo//60:02d}:{mejor_tiempo%60:02d}\n\n"
            texto += "📋 HISTORIAL:\n"

            for corte, tiempo in filas[:10]:
                texto += f"   • {corte}: {tiempo//60:02d}:{tiempo%60:02d}\n"

            self.resultado_barberos.text = texto
        except Exception as e:
            self.resultado_barberos.text = f"Error: {str(e)}"

    def mostrar_filtros_barberos(self):
        """Cliente: muestra filtros para buscar barberos (estilo exacto a la imagen)"""
        self.resetear_colores_botones()
        self.ids.btn_barberos.background_color = (0.6, 0.6, 0.6, 1)
        self.ids.contenido.clear_widgets()
        
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.anchorlayout import AnchorLayout
        
        # Scroll principal
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=20, spacing=15)
        layout.bind(minimum_height=layout.setter('height'))
        
        # Título (igual a la imagen)
        layout.add_widget(Label(
            text='BUSCAR BARBEROS POR SERVICIO',
            font_size=20,
            color=(0.9, 0.2, 0.2, 1),
            bold=True,
            size_hint_y=None,
            height=45,
            halign='center'
        ))
        
        # Grid de 3 columnas (como en la imagen)
        grid = GridLayout(cols=3, spacing=15, size_hint_y=None, padding=[0, 15, 0, 15])
        grid.bind(minimum_height=grid.setter('height'))
        
        # Filtros con emoji y texto (exactamente como en la imagen)
        filtros = [
            {'nombre': 'Degradado', 'emoji': '✂️'},
            {'nombre': 'Tijera', 'emoji': '✂️'},
            {'nombre': 'Navaja', 'emoji': '🪒'},
            {'nombre': 'Tinte', 'emoji': '🎨'},
            {'nombre': 'Diseño', 'emoji': '💇'},
            {'nombre': 'Barba', 'emoji': '🧔'},
            {'nombre': 'Cejas', 'emoji': '✨'},
            {'nombre': 'Tratamiento', 'emoji': '💆'}
        ]
        
        # Calcular ancho del cuadrado (pantalla / 3 - espacio)
        ancho_cuadro = (Window.width - 60) / 3
        
        for filtro in filtros:
            # Contenedor cuadrado
            cuadro = BoxLayout(
                orientation='vertical',
                size_hint_x=None,
                width=ancho_cuadro,
                size_hint_y=None,
                height=ancho_cuadro,
                padding=[0, 12, 0, 12],
                spacing=0
            )
            
            # Fondo gris oscuro con bordes redondeados
            with cuadro.canvas.before:
                Color(0.18, 0.18, 0.18, 1)
                RoundedRectangle(pos=cuadro.pos, size=cuadro.size, radius=[16, 16, 16, 16])
                # Borde sutil dorado
                Color(0.8, 0.6, 0.2, 0.8)
                Line(rounded_rectangle=(cuadro.x, cuadro.y, cuadro.width, cuadro.height, 16), width=1)
            
            def actualizar_cuadro(instance, value):
                for instr in instance.canvas.before.children:
                    if isinstance(instr, RoundedRectangle):
                        instr.pos = instance.pos
                        instr.size = instance.size
                    elif isinstance(instr, Line):
                        instr.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 16)
            cuadro.bind(pos=actualizar_cuadro, size=actualizar_cuadro)
            
            # Área para el emoji (centrado)
            anchor_emoji = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=0.7)
            emoji_label = Label(
                text=filtro['emoji'],
                font_size=38,
                size_hint=(None, None),
                size=(ancho_cuadro * 0.55, ancho_cuadro * 0.55)
            )
            anchor_emoji.add_widget(emoji_label)
            cuadro.add_widget(anchor_emoji)
            
            # Contenedor para el texto (abajo)
            texto_container = BoxLayout(size_hint_y=0.3, padding=[0, 0, 0, 5])
            texto_label = Label(
                text=filtro['nombre'],
                font_size=13,
                bold=True,
                halign='center',
                valign='middle',
                color=(0.95, 0.85, 0.55, 1)
            )
            texto_label.bind(size=texto_label.setter('text_size'))
            texto_container.add_widget(texto_label)
            cuadro.add_widget(texto_container)
            
            # Botón transparente que cubre todo el cuadrado
            btn = Button(
                text='',
                size_hint=(1, 1),
                background_color=(0, 0, 0, 0),
                background_normal=''
            )
            btn.bind(on_press=lambda x, f=filtro['nombre']: self.buscar_por_filtro(f))
            cuadro.add_widget(btn)
            
            grid.add_widget(cuadro)
        
        layout.add_widget(grid)
        
        # Botón "VER TODOS LOS BARBEROS" (igual a la imagen)
        btn_todos = Button(
            text='VER TODOS LOS BARBEROS',
            size_hint_y=None,
            height=52,
            background_color=(0.9, 0.2, 0.2, 1),
            background_normal='',
            color=(1, 1, 1, 1),
            font_size=18,
            bold=True,
            size_hint_x=0.9,
            pos_hint={'center_x': 0.5}
        )
        btn_todos.bind(on_press=lambda x: self.mostrar_todos_barberos())
        layout.add_widget(btn_todos)
        
        # Resultado de búsqueda
        self.resultado_filtros = BoxLayout(orientation='vertical', size_hint_y=None, height=300)
        layout.add_widget(self.resultado_filtros)
        
        scroll.add_widget(layout)
        self.ids.contenido.add_widget(scroll)

    def generar_codigo_servicio(self, instance):
        """Cliente: genera un código de 6 dígitos de un solo uso"""
        # Generar código de 6 dígitos (letras mayúsculas + números)
        caracteres = string.ascii_uppercase + string.digits
        # Excluir caracteres confusos: 0, O, 1, I
        caracteres = ''.join([c for c in caracteres if c not in '0O1I'])
        codigo = ''.join(random.choices(caracteres, k=6))
        
        try:
            conn = conectar()
            cursor = conn.cursor()
            
            # Guardar código en la tabla
            cursor.execute('''
                INSERT INTO codigos_servicio (cliente_id, codigo)
                VALUES (?, ?)
            ''', (self.manager.current_user['id'], codigo))
            conn.commit()
            conn.close()
            
            # Mostrar popup con el código
            content = BoxLayout(orientation='vertical', padding=20, spacing=15)
            content.add_widget(Label(
                text='🎫 CÓDIGO DE SERVICIO',
                font_size=24,
                color=(0.9, 0.2, 0.2, 1),
                size_hint_y=None,
                height=50
            ))
            
            # Código grande
            codigo_label = Label(
                text=codigo,
                font_size=48,
                bold=True,
                color=(0.2, 0.8, 0.2, 1),
                size_hint_y=None,
                height=80
            )
            content.add_widget(codigo_label)
            
            content.add_widget(Label(
                text='Presenta este código al barbero\n(Solo válido por 1 uso)',
                font_size=14,
                size_hint_y=None,
                height=50
            ))
            
            btn_cerrar = Button(text='CERRAR', size_hint_y=None, height=50)
            popup = Popup(title='Código de Servicio', content=content, size_hint=(0.8, 0.5), auto_dismiss=False)
            btn_cerrar.bind(on_press=popup.dismiss)
            content.add_widget(btn_cerrar)
            
            popup.open()
            
        except Exception as e:
            self.mostrar_popup('Error', f'Error al generar código: {str(e)}')
    
    def mostrar_tarjeta_fidelidad(self):
        """Cliente: muestra tarjeta de fidelidad (se refresca cada vez)"""
        self.resetear_colores_botones()
        self.ids.contenido.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Título con imagen
        layout.add_widget(Image(
            source='images/decoraciones/Titulo_Fidelidad.png',
            size_hint_y=None,
            height=80,
            keep_ratio=True,
            allow_stretch=True
        ))
        
        # Mostrar información de fidelidad
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT cortes_acumulados, cortes_gratis_recibidos 
                FROM fidelidad WHERE cliente_id = ?
            ''', (self.manager.current_user['id'],))
            fidelidad = cursor.fetchone()
            conn.close()
            
            if fidelidad:
                cortes = fidelidad[0]
                gratis = fidelidad[1]
                faltan = 4 - cortes
                
                # Tarjeta visual
                tarjeta = BoxLayout(orientation='vertical', padding=15, spacing=10, size_hint_y=None, height=190)
                with tarjeta.canvas.before:
                    Color(0.2, 0.2, 0.2, 1)
                    RoundedRectangle(pos=tarjeta.pos, size=tarjeta.size, radius=[20, 20, 20, 20])
                
                def actualizar_rect(instance, value):
                    for instr in instance.canvas.before.children:
                        if isinstance(instr, RoundedRectangle):
                            instr.pos = instance.pos
                            instr.size = instance.size
                tarjeta.bind(pos=actualizar_rect, size=actualizar_rect)
                
                # Título de cortes
                tarjeta.add_widget(Label(
                    text=f'✂️ {cortes}/4 cortes',
                    font_size=28,
                    bold=True,
                    size_hint_y=None,
                    height=50
                ))
                
                # Barra de progreso con cuadrados y X rojas
                progreso = BoxLayout(size_hint_y=None, height=60, spacing=10)
                
                for i in range(4):
                    if i < cortes:
                        # Cuadrado con X roja (corte realizado)
                        cuadro = BoxLayout(size_hint_x=0.25, size_hint_y=None, height=55)
                        with cuadro.canvas.before:
                            # Fondo blanco/gris claro
                            Color(0.95, 0.95, 0.95, 1)
                            RoundedRectangle(pos=cuadro.pos, size=cuadro.size, radius=[12, 12, 12, 12])
                            # Borde rojo
                            Color(0.9, 0.2, 0.2, 1)
                            Line(rounded_rectangle=(cuadro.x, cuadro.y, cuadro.width, cuadro.height, 12), width=2)
                        # X roja
                        x_label = Label(text='✗', font_size=42, color=(0.9, 0.2, 0.2, 1), bold=True, size_hint=(1, 1))
                        cuadro.add_widget(x_label)
                        
                        def actualizar_cuadro(instance, value):
                            for instr in instance.canvas.before.children:
                                if isinstance(instr, RoundedRectangle):
                                    instr.pos = instance.pos
                                    instr.size = instance.size
                                elif isinstance(instr, Line):
                                    instr.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 12)
                        cuadro.bind(pos=actualizar_cuadro, size=actualizar_cuadro)
                        progreso.add_widget(cuadro)
                    else:
                        # Cuadrado vacío (corte pendiente)
                        cuadro = BoxLayout(size_hint_x=0.25, size_hint_y=None, height=55)
                        with cuadro.canvas.before:
                            Color(0.25, 0.25, 0.25, 1)
                            RoundedRectangle(pos=cuadro.pos, size=cuadro.size, radius=[12, 12, 12, 12])
                            Color(0.5, 0.5, 0.5, 1)
                            Line(rounded_rectangle=(cuadro.x, cuadro.y, cuadro.width, cuadro.height, 12), width=1)
                        
                        def actualizar_cuadro(instance, value):
                            for instr in instance.canvas.before.children:
                                if isinstance(instr, RoundedRectangle):
                                    instr.pos = instance.pos
                                    instr.size = instance.size
                                elif isinstance(instr, Line):
                                    instr.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 12)
                        cuadro.bind(pos=actualizar_cuadro, size=actualizar_cuadro)
                        progreso.add_widget(cuadro)
                
                tarjeta.add_widget(progreso)
                
                # Mensaje
                if cortes >= 4:
                    tarjeta.add_widget(Label(
                        text='✅ ¡TIENES UN CORTE GRATIS!',
                        font_size=18,
                        color=(0.2, 0.8, 0.2, 1),
                        size_hint_y=None,
                        height=40
                    ))
                else:
                    tarjeta.add_widget(Label(
                        text=f'⏳ Te faltan {faltan} cortes para uno gratis',
                        font_size=16,
                        size_hint_y=None,
                        height=40
                    ))
                
                tarjeta.add_widget(Label(
                    text=f'🎁 Cortes gratis recibidos: {gratis}',
                    font_size=14,
                    size_hint_y=None,
                    height=30
                ))
                
                layout.add_widget(tarjeta)
        except Exception as e:
            layout.add_widget(Label(text=f'Error: {str(e)}', size_hint_y=None, height=100))
        
        # Botón "MI QR"
        btn_qr = Button(
            text='📱 MI CÓDIGO QR',
            size_hint_y=None,
            height=60,
            background_color=(0.9, 0.2, 0.2, 1),
            background_normal='',
            font_size=18,
            bold=True
        )
        btn_qr.bind(on_press=self.mostrar_mi_qr)
        layout.add_widget(btn_qr)
        
        # Botón "GENERAR CÓDIGO"
        btn_codigo = Button(
            text='🔢 GENERAR CÓDIGO DE SERVICIO',
            size_hint_y=None,
            height=60,
            background_color=(0.3, 0.3, 0.8, 1),
            background_normal='',
            font_size=18,
            bold=True
        )
        btn_codigo.bind(on_press=self.generar_codigo_servicio)
        layout.add_widget(btn_codigo)
        
        self.ids.contenido.add_widget(layout)

    def mostrar_ranking_barberos(self):
        """Cliente: muestra ranking de barberos"""
        self.resetear_colores_botones()
        self.ids.btn_cortes.background_color = (0.6, 0.6, 0.6, 1)
        self.ids.contenido.clear_widgets()
        
        from kivy.uix.scrollview import ScrollView
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Título con imagen
        layout.add_widget(Image(
            source='images/decoraciones/Titulo_Ranking.png',
            size_hint_y=None,
            height=70,
            keep_ratio=True,
            allow_stretch=True
        ))
        
        # ScrollView para ranking
        scroll = ScrollView(size_hint_y=None, height=550)
        self.ranking_content = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
        self.ranking_content.bind(minimum_height=self.ranking_content.setter('height'))
        scroll.add_widget(self.ranking_content)
        layout.add_widget(scroll)
        
        # Cargar ranking
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.nombre_completo, 
                       COUNT(c.id) as total_cortes,
                       AVG(c.tiempo_segundos) as tiempo_promedio
                FROM barberos b
                LEFT JOIN cortes c ON c.barbero_id = b.id
                GROUP BY b.id
                ORDER BY tiempo_promedio ASC, total_cortes DESC
                LIMIT 10
            ''')
            
            rankings = cursor.fetchall()
            conn.close()
            
            self.ranking_content.clear_widgets()
            
            for i, (barbero, total, tiempo) in enumerate(rankings, 1):
                if tiempo:
                    minutos = int(tiempo) // 60
                    segs = int(tiempo) % 60
                    tiempo_str = f'{minutos:02d}:{segs:02d}'
                else:
                    tiempo_str = '--:--'
                
                if i == 1:
                    medalla = '🥇'
                elif i == 2:
                    medalla = '🥈'
                elif i == 3:
                    medalla = '🥉'
                else:
                    medalla = f'{i}.'
                
                item = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=10)
                with item.canvas.before:
                    Color(0.15, 0.15, 0.15, 1)
                    RoundedRectangle(pos=item.pos, size=item.size, radius=[12, 12, 12, 12])
                
                def actualizar_rect(instance, value):
                    for instr in instance.canvas.before.children:
                        if isinstance(instr, RoundedRectangle):
                            instr.pos = instance.pos
                            instr.size = instance.size
                item.bind(pos=actualizar_rect, size=actualizar_rect)
                
                item.add_widget(Label(
                    text=f'{medalla} {barbero}',
                    font_size=18,
                    bold=True,
                    size_hint_y=None,
                    height=35
                ))
                item.add_widget(Label(
                    text=f'✂️ {total} cortes | ⏱️ {tiempo_str} promedio',
                    font_size=14,
                    size_hint_y=None,
                    height=25
                ))
                
                self.ranking_content.add_widget(item)
            
            if not rankings:
                self.ranking_content.add_widget(Label(text='No hay cortes registrados aún'))
                
        except Exception as e:
            self.ranking_content.add_widget(Label(text=f'Error: {str(e)}'))
        
        self.ids.contenido.add_widget(layout)

    # ========== MÉTODOS REDIRECTORES ==========
    def mostrar_nuevo_corte_activo(self):
        """Redirige según el rol"""
        if hasattr(self.manager, 'current_user') and self.manager.current_user.get('rol') == 'cliente':
            self.mostrar_tarjeta_fidelidad()
        else:
            self.mostrar_nuevo_corte_barbero()

    def mostrar_barberos(self):
        """Redirige según el rol"""
        if hasattr(self.manager, 'current_user') and self.manager.current_user.get('rol') == 'cliente':
            self.mostrar_filtros_barberos()
        else:
            self.mostrar_barberos_barbero()

    def mostrar_mi_qr(self, instance):
        """Genera y muestra el QR del cliente"""
        import qrcode
        from kivy.core.image import Image as CoreImage
        from kivy.uix.image import Image as KivyImage
        import io
        
        cliente_id = self.manager.current_user['id']
        cliente_nombre = self.manager.current_user['nombre']
        datos_qr = f"BARBERIA_POLAR|CLIENTE|{cliente_id}|{cliente_nombre}"
        
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(datos_qr)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(text='🎫 MI CÓDIGO QR', font_size=20))
        
        qr_image = KivyImage(texture=CoreImage(img_bytes, ext='png').texture, size_hint_y=None, height=200)
        content.add_widget(qr_image)
        
        content.add_widget(Label(text=f'Cliente: {cliente_nombre}', font_size=16))
        content.add_widget(Label(text='Presenta este QR al barbero', font_size=14))
        
        btn_cerrar = Button(text='CERRAR', size_hint_y=None, height=40)
        popup = Popup(title='Mi QR', content=content, size_hint=(0.8, 0.8), auto_dismiss=False)
        btn_cerrar.bind(on_press=popup.dismiss)
        content.add_widget(btn_cerrar)
        
        popup.open()

    def mostrar_cortes(self):
        """Redirige según el rol"""
        if hasattr(self.manager, 'current_user') and self.manager.current_user.get('rol') == 'cliente':
            self.mostrar_ranking_barberos()
        else:
            self.mostrar_cortes_barbero()

    # ========== MÉTODOS COMPARTIDOS ==========
    def buscar_por_filtro(self, filtro):
        """Busca barberos según el filtro seleccionado"""
        nombre_filtro = filtro.replace('✂️ ', '').replace('💈 ', '').replace('🪒 ', '').replace('🎨 ', '').replace('💇 ', '').replace('🧔 ', '').replace('✨ ', '').replace('💆 ', '')
        
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT b.nombre_completo, 
                    COUNT(c.id) as total_cortes,
                    AVG(c.tiempo_segundos) as tiempo_promedio
                FROM barberos b
                JOIN cortes c ON c.barbero_id = b.id
                WHERE c.nombre_corte LIKE ?
                GROUP BY b.id
                ORDER BY total_cortes DESC, tiempo_promedio ASC
                LIMIT 5
            ''', (f'%{nombre_filtro}%',))
            
            resultados = cursor.fetchall()
            conn.close()
            
            self.mostrar_resultados_barberos(filtro, resultados)
            
        except Exception as e:
            # Mostrar error en el área de resultados
            self.resultado_filtros.clear_widgets()
            self.resultado_filtros.add_widget(Label(
                text=f'Error: {str(e)}',
                color=(0.9, 0.2, 0.2, 1),
                size_hint_y=None,
                height=50
            ))

    def mostrar_resultados_barberos(self, filtro, resultados):
        """Muestra los resultados de búsqueda de forma bonita y presentable"""
        
        from kivy.uix.scrollview import ScrollView
        
        # Limpiar el contenedor de resultados
        self.resultado_filtros.clear_widgets()
        
        # Layout para los resultados
        resultados_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        resultados_layout.bind(minimum_height=resultados_layout.setter('height'))
        
        # Título del filtro seleccionado
        titulo_filtro = BoxLayout(size_hint_y=None, height=40, padding=[5, 5])
        titulo_filtro.add_widget(Label(
            text=f'🔍 {filtro}',
            font_size=18,
            bold=True,
            color=(0.9, 0.6, 0.2, 1),
            size_hint_x=0.8,
            halign='left'
        ))
        titulo_filtro.add_widget(Label(
            text=f'🎯 {len(resultados)} barberos',
            font_size=14,
            color=(0.7, 0.7, 0.7, 1),
            size_hint_x=0.2,
            halign='right'
        ))
        resultados_layout.add_widget(titulo_filtro)
        
        if resultados:
            for barbero, total_cortes, tiempo_promedio in resultados:
                # Tarjeta de barbero
                tarjeta = BoxLayout(orientation='vertical', size_hint_y=None, height=85, padding=[12, 8], spacing=5)
                
                # Fondo de la tarjeta
                with tarjeta.canvas.before:
                    Color(0.15, 0.15, 0.15, 1)
                    RoundedRectangle(pos=tarjeta.pos, size=tarjeta.size, radius=[12, 12, 12, 12])
                    Color(0.35, 0.35, 0.35, 1)
                    Line(rounded_rectangle=(tarjeta.x, tarjeta.y, tarjeta.width, tarjeta.height, 12), width=1)
                
                def actualizar_tarjeta(instance, value):
                    for instr in instance.canvas.before.children:
                        if isinstance(instr, RoundedRectangle):
                            instr.pos = instance.pos
                            instr.size = instance.size
                        elif isinstance(instr, Line):
                            instr.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 12)
                tarjeta.bind(pos=actualizar_tarjeta, size=actualizar_tarjeta)
                
                # Fila del nombre del barbero
                nombre_layout = BoxLayout(size_hint_y=None, height=32)
                nombre_layout.add_widget(Label(
                    text='👤',
                    font_size=18,
                    size_hint_x=0.1,
                    halign='center'
                ))
                nombre_layout.add_widget(Label(
                    text=barbero,
                    font_size=16,
                    bold=True,
                    color=(0.95, 0.9, 0.8, 1),
                    size_hint_x=0.9,
                    halign='left'
                ))
                tarjeta.add_widget(nombre_layout)
                
                # Fila de estadísticas
                stats_layout = BoxLayout(size_hint_y=None, height=28, spacing=15)
                
                # Cortes realizados
                cortes_layout = BoxLayout(size_hint_x=0.5)
                cortes_layout.add_widget(Label(
                    text='✂️',
                    font_size=14,
                    size_hint_x=0.2,
                    halign='center'
                ))
                cortes_layout.add_widget(Label(
                    text=f'{total_cortes} cortes',
                    font_size=12,
                    color=(0.8, 0.8, 0.8, 1),
                    size_hint_x=0.8,
                    halign='left'
                ))
                stats_layout.add_widget(cortes_layout)
                
                # Tiempo promedio
                if tiempo_promedio:
                    minutos = int(tiempo_promedio) // 60
                    segs = int(tiempo_promedio) % 60
                    tiempo_text = f'{minutos:02d}:{segs:02d}'
                    icono_tiempo = '⏱️'
                    color_tiempo = (0.9, 0.7, 0.3, 1) if minutos == 0 and segs < 10 else (0.7, 0.7, 0.7, 1)
                else:
                    tiempo_text = '--:--'
                    icono_tiempo = '⏱️'
                    color_tiempo = (0.6, 0.6, 0.6, 1)
                
                tiempo_layout = BoxLayout(size_hint_x=0.5)
                tiempo_layout.add_widget(Label(
                    text=icono_tiempo,
                    font_size=14,
                    size_hint_x=0.2,
                    halign='center'
                ))
                tiempo_layout.add_widget(Label(
                    text=f'{tiempo_text} promedio',
                    font_size=12,
                    color=color_tiempo,
                    size_hint_x=0.8,
                    halign='left'
                ))
                stats_layout.add_widget(tiempo_layout)
                
                tarjeta.add_widget(stats_layout)
                resultados_layout.add_widget(tarjeta)
        else:
            # Mensaje cuando no hay resultados
            vacio_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=90, padding=[15, 20])
            with vacio_layout.canvas.before:
                Color(0.12, 0.12, 0.12, 1)
                RoundedRectangle(pos=vacio_layout.pos, size=vacio_layout.size, radius=[12, 12, 12, 12])
            
            def actualizar_vacio(instance, value):
                for instr in instance.canvas.before.children:
                    if isinstance(instr, RoundedRectangle):
                        instr.pos = instance.pos
                        instr.size = instance.size
            vacio_layout.bind(pos=actualizar_vacio, size=actualizar_vacio)
            
            vacio_layout.add_widget(Label(
                text='😔 No hay barberos que realicen este servicio',
                font_size=13,
                color=(0.8, 0.6, 0.4, 1),
                halign='center'
            ))
            vacio_layout.add_widget(Label(
                text='Prueba con otro filtro',
                font_size=11,
                color=(0.6, 0.6, 0.6, 1),
                halign='center'
            ))
            resultados_layout.add_widget(vacio_layout)
        
        # ScrollView para los resultados
        scroll_resultados = ScrollView(size_hint_y=None, height=260)
        scroll_resultados.add_widget(resultados_layout)
        
        # Actualizar el contenedor de resultados
        self.resultado_filtros.add_widget(scroll_resultados)

# ---------- MENÚ NUEVO CORTE ----------
class MenuCorteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        if hasattr(self.manager, 'current_user'):
            self.ids.bienvenida.text = f'¡{self.manager.current_user["nombre"]}!'

    def volver_principal(self):
        self.manager.current = 'principal'

    def mostrar_popup_nombre_corte(self):
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        content.add_widget(Label(text='¿Qué corte harás?', font_size=20))

        self.corte_input = textinput.TextInput(
            multiline=False,
            hint_text='Ej: Degradado, Tijera, etc.'
        )
        content.add_widget(self.corte_input)

        btn_layout = BoxLayout(size_hint=(1, 0.3), spacing=10)
        btn_cancelar = Button(text='Cancelar', background_color=(0.8, 0.2, 0.2, 1))
        btn_aceptar = Button(text='Comenzar', background_color=(0.2, 0.8, 0.2, 1))
        btn_layout.add_widget(btn_cancelar)
        btn_layout.add_widget(btn_aceptar)
        content.add_widget(btn_layout)

        popup = Popup(title='Nuevo Corte', content=content, size_hint=(0.9, 0.5), auto_dismiss=False)
        btn_cancelar.bind(on_press=popup.dismiss)
        btn_aceptar.bind(on_press=lambda x: self.comenzar_corte(popup))
        popup.open()

    def comenzar_corte(self, popup):
        nombre_corte = self.corte_input.text.strip()
        if not nombre_corte:
            self.mostrar_mensaje('Error', 'Escribe el nombre del corte')
            return
        popup.dismiss()
        self.manager.nombre_corte_actual = nombre_corte
        self.manager.current = 'temporizador'

    def mostrar_mensaje(self, titulo, mensaje):
        popup = Popup(title=titulo, content=Label(text=mensaje), size_hint=(0.8, 0.3))
        popup.open()


# ---------- TEMPORIZADOR ----------
class TemporizadorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.segundos = 0
        self.temporizador_activo = False
        self.evento_tiempo = None

    def on_enter(self):
        if hasattr(self.manager, 'nombre_corte_actual'):
            self.ids.titulo_corte.text = f'Corte: {self.manager.nombre_corte_actual}'
        self.mostrar_confirmacion_inicio()

    def mostrar_confirmacion_inicio(self):
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(text='¿Estás listo para comenzar?\nEl contador iniciará.'))

        btn_layout = BoxLayout(size_hint=(1, 0.4), spacing=10)
        btn_cancelar = Button(text='Cancelar', background_color=(0.8, 0.2, 0.2, 1))
        btn_aceptar = Button(text='¡Sí, empezar!', background_color=(0.2, 0.8, 0.2, 1))
        btn_layout.add_widget(btn_cancelar)
        btn_layout.add_widget(btn_aceptar)
        content.add_widget(btn_layout)

        popup = Popup(title='Comenzar Corte', content=content, size_hint=(0.9, 0.4), auto_dismiss=False)
        btn_cancelar.bind(on_press=self.cancelar_corte)
        btn_aceptar.bind(on_press=lambda x: self.iniciar_temporizador(popup))
        popup.open()

    def cancelar_corte(self, instance):
        self.manager.current = 'principal'

    def iniciar_temporizador(self, popup):
        popup.dismiss()
        self.ids.btn_finalizar.disabled = False
        self.ids.btn_pausa.disabled = False
        self.ids.btn_pausa.text = '⏸️ Pausar'
        self.temporizador_activo = True
        self.evento_tiempo = Clock.schedule_interval(self.actualizar_tiempo, 1)

    def actualizar_tiempo(self, dt):
        if self.temporizador_activo:
            self.segundos += 1
            self.ids.contador_label.text = self.formatear_tiempo(self.segundos)

    def formatear_tiempo(self, segundos):
        minutos = segundos // 60
        segs = segundos % 60
        return f'{minutos:02d}:{segs:02d}'

    def pausar_temporizador(self):
        if self.temporizador_activo:
            self.temporizador_activo = False
            self.ids.btn_pausa.text = '▶️ Reanudar'
        else:
            self.temporizador_activo = True
            self.ids.btn_pausa.text = '⏸️ Pausar'

    def finalizar_corte(self):
        self.temporizador_activo = False
        if self.evento_tiempo:
            self.evento_tiempo.cancel()
        self.manager.tiempo_corte_actual = self.segundos
        self.mostrar_resumen_corte()

    def mostrar_resumen_corte(self):
        tiempo_formateado = self.formatear_tiempo(self.segundos)
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(text=f'¡Corte finalizado!\n\nTiempo: {tiempo_formateado}\n\nAhora grabaremos un video de 5 segundos.'))
        btn_siguiente = Button(text='Continuar a la cámara', size_hint=(1, 0.3))
        content.add_widget(btn_siguiente)
        popup = Popup(title='Resumen', content=content, size_hint=(0.9, 0.5), auto_dismiss=False)
        btn_siguiente.bind(on_press=lambda x: self.ir_a_camara(popup))
        popup.open()

    def ir_a_camara(self, popup):
        popup.dismiss()
        self.resetear_temporizador()
        self.manager.current = 'camara'

    def resetear_temporizador(self):
        self.segundos = 0
        self.ids.contador_label.text = '00:00'
        self.temporizador_activo = False
        self.ids.btn_finalizar.disabled = True
        self.ids.btn_pausa.disabled = True


# ---------- CÁMARA ----------
class CamaraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ruta_video = None
        self.grabando = False
        self.contador = 0
        self.evento_contador = None

    def on_enter(self):
        self.iniciar_proceso_camara()

    def iniciar_proceso_camara(self):
        self.ids.estado_label.text = 'Preparando cámara...'
        Clock.schedule_once(lambda dt: self.iniciar_grabacion(), 2)

    def iniciar_grabacion(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_corte = self.manager.nombre_corte_actual.replace(' ', '_')
            barbero_id = self.manager.current_user['id']
            try:
                carpeta_videos = storagepath.get_dcim_dir()
            except:
                carpeta_videos = './videos'
            os.makedirs(carpeta_videos, exist_ok=True)
            nombre_archivo = f"barbero{barbero_id}_{timestamp}_{nombre_corte}.mp4"
            self.ruta_video = os.path.join(carpeta_videos, nombre_archivo)
            self.ids.estado_label.text = 'Abriendo cámara...'
            camera.take_picture(filename=self.ruta_video, on_complete=self.grabacion_terminada)
            self.grabando = True
            self.contador = 5
            self.ids.contador_grabacion.text = str(self.contador)
            self.ids.estado_label.text = 'Grabando... 5 segundos'
            self.evento_contador = Clock.schedule_interval(self.actualizar_contador_grabacion, 1)
        except Exception as e:
            self.ids.estado_label.text = f'Error: {str(e)[:30]}...'
            self.mostrar_error_camara(str(e))

    def actualizar_contador_grabacion(self, dt):
        if self.grabando:
            self.contador -= 1
            self.ids.contador_grabacion.text = str(self.contador) if self.contador > 0 else '✅'
            self.ids.estado_label.text = f'Grabando... {self.contador} segundos'
            if self.contador <= 0:
                self.grabacion_terminada(self.ruta_video)

    def abrir_camara_manual(self):
        self.iniciar_grabacion()

    def grabacion_terminada(self, ruta):
        if self.evento_contador:
            self.evento_contador.cancel()
        self.grabando = False
        self.ids.contador_grabacion.text = '✅'
        self.ids.estado_label.text = '¡Video guardado!'
        self.manager.ruta_video_actual = self.ruta_video
        Clock.schedule_once(lambda dt: self.guardar_en_bd(), 2)

    def guardar_en_bd(self):
        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO cortes (barbero_id, nombre_corte, tiempo_segundos, ruta_video)
                VALUES (?, ?, ?, ?)
            ''', (
                self.manager.current_user['id'],
                self.manager.nombre_corte_actual,
                self.manager.tiempo_corte_actual,
                self.ruta_video
            ))
            conn.commit()
            conn.close()
            self.ids.estado_label.text = '✅ Guardado en ranking'
            Clock.schedule_once(lambda dt: self.volver_al_menu(), 2)
        except Exception as e:
            self.mostrar_error_camara(f'Error al guardar: {str(e)}')

    def volver_al_menu(self):
        self.manager.current = 'principal'

    def mostrar_error_camara(self, mensaje):
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(text=f'Error con la cámara:\n{mensaje}\n\nPuedes continuar sin video.'))
        btn_ok = Button(text='Continuar', size_hint=(1, 0.3))
        popup = Popup(title='Error', content=content, size_hint=(0.9, 0.5))
        btn_ok.bind(on_press=lambda x: self.continuar_sin_video(popup))
        content.add_widget(btn_ok)
        popup.open()

    def continuar_sin_video(self, popup):
        popup.dismiss()
        self.ruta_video = None
        self.guardar_en_bd()


# ---------- APLICACIÓN PRINCIPAL ----------
class BarberiaApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegistroScreen(name='registro'))
        sm.add_widget(PrincipalScreen(name='principal'))
        sm.add_widget(MenuCorteScreen(name='menu_corte'))
        sm.add_widget(TemporizadorScreen(name='temporizador'))
        sm.add_widget(CamaraScreen(name='camara'))
        sm.current = 'login'
        return sm


if __name__ == '__main__':
    BarberiaApp().run()