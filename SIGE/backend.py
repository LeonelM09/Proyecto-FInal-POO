import json
from datetime import datetime, timedelta, date
import pandas as pd
import matplotlib.pyplot as plt
import os

# ========================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y GESTIÓN DE RUTAS
# ========================================================================

# Configuración de rutas para persistencia de datos e imágenes
CARPETA_PRINCIPAL = os.path.dirname(os.path.abspath(__file__))
CARPETA_IMAGENES = os.path.join(CARPETA_PRINCIPAL, "imagenes_equinos")
CARPETA_RECETAS = os.path.join(CARPETA_PRINCIPAL, "Recetas_Medicas")
CARPETA_REPORTES = os.path.join(CARPETA_PRINCIPAL, "Reportes_Financieros")
IMAGEN_DEFAULT_PATH = os.path.join(CARPETA_IMAGENES, "default_horse.png")
RUTA_BD = os.path.join(CARPETA_PRINCIPAL, 'database_sige.json')

# Asegura que los directorios del sistema existan para evitar errores de escritura
for carpeta in [CARPETA_IMAGENES, CARPETA_RECETAS, CARPETA_REPORTES]:
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

# Caché en memoria para optimizar lecturas frecuentes al JSON
_datos_en_memoria = None

def cargar_datos():
    """
    Carga la base de datos completa desde el archivo JSON o devuelve la caché en memoria.

    Returns:
        dict: Diccionario con toda la estructura de datos del SIGE (usuarios, equinos, etc.).
    """
    global _datos_en_memoria
    if _datos_en_memoria is not None:
        return _datos_en_memoria
    
    try:
        with open(RUTA_BD, 'r', encoding='utf-8') as f:
            _datos_en_memoria = json.load(f)
    except FileNotFoundError:
        # Estructura inicial por defecto si el archivo no existe (Primer inicio)
        _datos_en_memoria = {
            "usuarios": [],
            "clientes": [],
            "equinos": [],
            "bitacoras": [],
            "finanzas": [],
            "alertas": [],
            "caballerizas": [],
            "inventario": [], 
            "mapa_caballerizas": [[False for _ in range(4)] for _ in range(4)]
        }

    return _datos_en_memoria

def guardar_datos(datos):
    """
    Persiste el estado actual de los datos en el archivo físico JSON.

    Args:
        datos (dict): El diccionario completo de datos a guardar.
    """
    global _datos_en_memoria
    _datos_en_memoria = datos
    
    with open(RUTA_BD, 'w', encoding='utf-8') as f:
        json.dump(_datos_en_memoria, f, indent=4)

# ========================================================================
# 2. MODELADO DE DATOS (CLASES ORIENTADAS A OBJETOS)
# ========================================================================

class Usuario():
    """
    Representa un usuario del sistema con permisos y credenciales.
    """
    
    # Límite administrativo para control de licencias o seguridad
    LIMITE_USUARIOS = 5

    def __init__(self, id_usuario, nombre, contraseña, rol, contacto=""):
        """
        Inicializa una nueva instancia de Usuario.

        Args:
            id_usuario (str): Identificador único (login).
            nombre (str): Nombre completo del empleado/usuario.
            contraseña (str): Clave de acceso.
            rol (str): Nivel de permisos (Ej. Administrador, Personal).
            contacto (str, optional): Información de contacto.
        """
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.contraseña = contraseña
        self.rol = rol
        self.contacto = contacto
        self.sesion_activa = False
    
    def iniciar_sesion(self, nombre_ingreso, contr_ing):
        """
        Valida las credenciales contra la base de datos.

        Args:
            nombre_ingreso (str): Nombre de usuario introducido.
            contr_ing (str): Contraseña introducida.

        Returns:
            tuple: (bool: éxito, str: rol_o_error, str: nombre_real)
        """
        datos = cargar_datos()
        for u in datos["usuarios"]:
            # Normalización a minúsculas para evitar errores tipográficos en el login
            if u["nombre"].lower() == nombre_ingreso.lower() and u["contraseña"] == contr_ing:
                self.sesion_activa = True
                self.rol = u["rol"]
                return True, u["rol"], u["nombre"]
        return False, "Credenciales incorrectas", None
        
    def registrar_usuario(self):
        """
        Guarda el nuevo usuario en la persistencia si cumple las validaciones.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        
        # Validación de seguridad: Evitar creación infinita de cuentas
        if len(datos["usuarios"]) >= self.LIMITE_USUARIOS:
            return False, f"Se ha alcanzado el límite de {self.LIMITE_USUARIOS} usuarios."
            
        for u in datos["usuarios"]:
            if u["id_usuario"] == self.id_usuario:
                return False, "El ID de usuario ya existe. Elige otro."

        nuevo_u = {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "contraseña": self.contraseña,
            "rol": self.rol,
            "contacto": self.contacto
        }
        datos["usuarios"].append(nuevo_u)
        guardar_datos(datos)
        return True, "Usuario creado exitosamente."
    
    def actualizar_usuario(self):
        """
        Actualiza los datos del usuario actual buscando por ID.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        for u in datos["usuarios"]:
            if u["id_usuario"] == self.id_usuario:
                u["nombre"] = self.nombre
                u["contraseña"] = self.contraseña
                u["rol"] = self.rol
                u["contacto"] = self.contacto
                guardar_datos(datos)
                return True, "Datos actualizados correctamente."
        return False, "Usuario no encontrado."

    def eliminar_usuario(self, id_borrar):
        """
        Elimina un usuario del sistema, protegiendo cuentas críticas.

        Args:
            id_borrar (str): ID del usuario a eliminar.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        # Restricción de negocio: El admin principal no puede auto-eliminarse para evitar orfandad del sistema
        if id_borrar.lower() == "leonel" or id_borrar.lower() == "admin": 
            return False, "Por seguridad, el Administrador Principal no puede ser eliminado."
            
        datos = cargar_datos()
        for i, u in enumerate(datos["usuarios"]):
            if u["id_usuario"] == id_borrar:
                del datos["usuarios"][i]
                guardar_datos(datos)
                return True, "Se eliminó el perfil."
        return False, "Usuario no encontrado."

class Cliente():
    """
    Gestiona la información de contacto y contractual de los propietarios.
    """
    
    def __init__(self, id_cliente, nom_completo, contacto, term_pension, notas=""):
        """
        Inicializa una instancia de Cliente.

        Args:
            id_cliente (str): ID único.
            nom_completo (str): Nombre del dueño.
            contacto (str): Teléfono o email.
            term_pension (str): Detalles del contrato.
            notas (str, optional): Observaciones internas o CRM.
        """
        self.id_cliente = id_cliente
        self.nom_completo = nom_completo
        self.contacto = contacto
        self.term_pension = term_pension
        self.notas = notas

    def registrar_cliente(self):
        """Persiste un nuevo cliente en la base de datos."""
        datos = cargar_datos()
        nuevo_cli = {
            "id_cliente": self.id_cliente,
            "nom_completo": self.nom_completo,
            "contacto": self.contacto,
            "term_pension": self.term_pension,
            "notas": self.notas
        }
        datos["clientes"].append(nuevo_cli)
        guardar_datos(datos)
        return True, f"Cliente {self.nom_completo} registrado con éxito."

    def actualizar_cliente(self):
        """Actualiza los datos de un cliente existente."""
        datos = cargar_datos()
        for c in datos["clientes"]:
            if c["id_cliente"] == self.id_cliente:
                c["nom_completo"] = self.nom_completo
                c["contacto"] = self.contacto
                c["term_pension"] = self.term_pension
                c["notas"] = self.notas
                guardar_datos(datos)
                return True, "Datos del cliente actualizados."
        return False, "No se encontró el cliente."

    def actualizar_contacto(self, nuevo_contacto):
        """
        Actualiza específicamente el medio de contacto de un cliente.

        Args:
            nuevo_contacto (str): Nuevo valor de contacto.

        Returns:
            bool/tuple: True si tiene éxito, o tuple con error si falla.
        """
        datos = cargar_datos()

        for c in datos["clientes"]:
            if c["id_cliente"] == self.id_cliente:
                c["contacto"] = nuevo_contacto
                self.contacto = nuevo_contacto
                guardar_datos(datos)
                return True
            
        return False, "Cliente no encontrado en la base de datos."
    
    def actualizar_cliente(self):
        """
        Actualiza todos los campos del perfil del cliente.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        for c in datos["clientes"]:
            if c["id_cliente"] == self.id_cliente:
                c["nom_completo"] = self.nom_completo
                c["contacto"] = self.contacto
                c["term_pension"] = self.term_pension
                guardar_datos(datos)
                return True, "Datos del cliente actualizados correctamente."
        return False, "Cliente no encontrado en la base de datos."

    def eliminar_cliente(self, id_borrar):
        """
        Elimina un cliente de la persistencia.

        Args:
            id_borrar (str): ID del cliente a borrar.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        for i, c in enumerate(datos["clientes"]):
            if c["id_cliente"] == id_borrar:
                del datos["clientes"][i]
                guardar_datos(datos)
                return True, "Cliente eliminado exitosamente."
        return False, "Cliente no encontrado."

class Equino():
    """
    Clase central para la gestión de animales (Caballos, Burros, etc.).
    """

    def __init__(self, id_equino, id_cliente, nombre, raza, cab_asignada, etapa_arrendamiento, ruta_imagen=None, **kwargs):
        """
        Inicializa un equino con sus atributos base y opcionales.

        Args:
            id_equino (str): ID único del animal.
            id_cliente (str): ID del propietario asociado.
            nombre (str): Nombre del animal.
            raza (str): Raza específica.
            cab_asignada (str): Identificador de la caballeriza (box).
            etapa_arrendamiento (str): Nivel de entrenamiento.
            ruta_imagen (str, optional): Ruta al archivo de fotografía.
            **kwargs: Atributos adicionales (sexo, pelaje, nacimiento, etc.).
        """
        self.id_equino = id_equino
        self.id_cliente = id_cliente
        self.nombre = nombre
        self.raza = raza
        self.cab_asig = cab_asignada
        self.etapa_arrendamiento = etapa_arrendamiento
        self.ruta_imagen = ruta_imagen
        self.sexo = kwargs.get("sexo", "Caballo")
        self.pelaje = kwargs.get("pelaje", "")
        self.nacimiento = kwargs.get("nacimiento", "")
        self.microchip = kwargs.get("microchip", "")
        self.especie = kwargs.get("especie", "Caballo")
        self.id_registro = kwargs.get("id_registro", "")
        self.descripcion_equino = kwargs.get("descripcion_equino", "")
        self.dias_trabajados = []
        self.alimentacion = "Pasto (Mañana/Tarde) y 2kg de grano estándar."
        self.historial_medico = []

        # Generación de fechas preventivas por defecto (estándares de salud equina)
        hoy = date.today()
        self.fechas_medicas = {
            "Herraje": (hoy + timedelta(days=12)).strftime("%d/%m/%Y"),
            "Desparasitación": (hoy + timedelta(days=35)).strftime("%d/%m/%Y"),
            "Odontología": (hoy + timedelta(days=180)).strftime("%d/%m/%Y")
        }

    def registrar_equino(self):
        """
        Registra un nuevo ejemplar y ocupa su caballeriza en el mapa físico.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()

        # Validación de unicidad para evitar duplicados en el registro
        for e in datos["equinos"]:
            if e["nombre"].lower() == self.nombre.lower() or e["id_equino"] == self.id_equino:
                return False, "El equino ya existe en la base de datos."

        # Gestión del mapa de caballerizas (matriz de ocupación)
        if self.cab_asig != "Sin Asignar":
            try:
                # Decodificación del formato 'C-XY' a coordenadas de matriz [X-1][Y-1]
                r_c = self.cab_asig.split("-")[1]
                r, c = int(r_c[0])-1, int(r_c[1])-1
                
                if datos["mapa_caballerizas"][r][c]:
                    return False, "La caballeriza seleccionada ya está ocupada."
                
                datos["mapa_caballerizas"][r][c] = True 
            except Exception as e:
                return False, "Formato de caballeriza inválido. Usa el formato C-11, C-12, etc."

        nuevo_equino = {
            "id_equino": self.id_equino,
            "id_cliente": self.id_cliente,
            "nombre": self.nombre,
            "raza": self.raza,
            "cab_asig": self.cab_asig,
            "etapa": self.etapa_arrendamiento,
            "ruta_imagen": self.ruta_imagen,
            "sexo": self.sexo,
            "pelaje": self.pelaje,
            "nacimiento": self.nacimiento,
            "microchip": self.microchip,
            "especie": self.especie,
            "id_registro": self.id_registro,
            "descripcion_equino": self.descripcion_equino,
            "dias_trabajados": self.dias_trabajados,
            "alimentacion": self.alimentacion,
            "historial_medico": self.historial_medico,
            "fechas_medicas": self.fechas_medicas
        }

        datos["equinos"].append(nuevo_equino)
        guardar_datos(datos)
        return True, "Registro de equino guardado exitosamente."
    
    def liberar_caballeriza(self):
        """
        Libera el espacio físico ocupado por el animal en el mapa de caballerizas.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        if self.cab_asig != "Sin Asignar":
            try:
                r_c = self.cab_asig.split("-")[1]
                r, c = int(r_c[0])-1, int(r_c[1])-1
                datos["mapa_caballerizas"][r][c] = False

                for e in datos["equinos"]:
                    if e["id_equino"] == self.id_equino:
                        e["cab_asig"] = "Sin Asignar"
                        self.cab_asig = "Sin Asignar"
                        break

                guardar_datos(datos)
                return True, "Caballeriza liberada correctamente."
            except:
                return False, "Error al procesar la ubicación."
        return False, "El caballo no tiene caballeriza asignada."

    def actualizar_ubicacion(self, nueva_caballeriza):
        """
        Traslada al animal de una caballeriza a otra, gestionando la disponibilidad del mapa.

        Args:
            nueva_caballeriza (str): Nuevo código de ubicación (Ej. 'C-22').

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()

        # Liberación de la ubicación previa antes de ocupar la nueva
        if self.cab_asig != "Sin Asignar":
            try:
                r_c_vieja = self.cab_asig.split("-")[1]
                r_vieja, c_vieja = int(r_c_vieja[0])-1, int(r_c_vieja[1])-1
                datos["mapa_caballerizas"][r_vieja][c_vieja] = False
            except:
                pass
        
        # Validación y ocupación de la nueva ubicación
        if nueva_caballeriza != "Sin Asignar":
            try:
                r_c_nueva = nueva_caballeriza.split("-")[1]
                r_nueva, c_nueva = int(r_c_nueva[0])-1, int(r_c_nueva[1])-1

                if datos["mapa_caballerizas"][r_nueva][c_nueva]:
                    # Rollback: Si la nueva está ocupada, devolvemos el estado a la anterior
                    if self.cab_asig != "Sin Asignar":
                        datos["mapa_caballerizas"][r_vieja][c_vieja] = True 
                    return False, f"La caballeriza {nueva_caballeriza} ya está ocupada."
                
                datos["mapa_caballerizas"][r_nueva][c_nueva] = True
            except:
                return False, "Formato de nueva caballeriza inválido."

        for e in datos["equinos"]:
            if e["id_equino"] == self.id_equino:
                e["cab_asig"] = nueva_caballeriza
                self.cab_asig = nueva_caballeriza 
                guardar_datos(datos) 
                return True, f"Ubicación actualizada: El caballo {self.nombre} ahora está en {nueva_caballeriza}."
                
        return False, "Error: No se encontró el caballo en la base de datos."

    def modificar_etapa(self, nueva_etapa):
        """
        Actualiza la fase de entrenamiento o arrendamiento del animal.

        Args:
            nueva_etapa (str): Nombre de la nueva etapa.

        Returns:
            tuple: (bool: éxito, str: mensaje)
        """
        datos = cargar_datos()
        for e in datos["equinos"]:
            if e["id_equino"] == self.id_equino:
                e["etapa"] = nueva_etapa
                self.etapa_arrendamiento = nueva_etapa
                guardar_datos(datos)
                return True, f"Etapa de {self.nombre} actualizada a {nueva_etapa}."
        return False, "Equino no encontrado."
    
    def actualizar_perfil(self, nueva_raza, nueva_caballeriza, nuevo_id_cliente=None, **kwargs):
        datos = cargar_datos()
        
        # 1. Validación: Actualizar el mapa de caballerizas si lo movimos de lugar
        if self.cab_asig != nueva_caballeriza:
            # Liberar la caballeriza vieja
            if self.cab_asig != "Sin Asignar":
                try:
                    r_v, c_v = int(self.cab_asig.split("-")[1][0])-1, int(self.cab_asig.split("-")[1][1])-1
                    datos["mapa_caballerizas"][r_v][c_v] = False
                except: pass
            
            # Ocupar la caballeriza nueva
            if nueva_caballeriza != "Sin Asignar":
                try:
                    r_n, c_n = int(nueva_caballeriza.split("-")[1][0])-1, int(nueva_caballeriza.split("-")[1][1])-1
                    if datos["mapa_caballerizas"][r_n][c_n]:
                        if self.cab_asig != "Sin Asignar": datos["mapa_caballerizas"][r_v][c_v] = True
                        return False, "La caballeriza nueva ya está ocupada."
                    datos["mapa_caballerizas"][r_n][c_n] = True
                except:
                    if self.cab_asig != "Sin Asignar": datos["mapa_caballerizas"][r_v][c_v] = True
                    return False, "Formato de caballeriza inválido (Ej. C-11)."

        # 2. Guardar los nuevos datos en el JSON
        for e in datos["equinos"]:
            if e["id_equino"] == self.id_equino:
                e["raza"] = nueva_raza
                e["cab_asig"] = nueva_caballeriza
                self.cab_asig = nueva_caballeriza
                
                if nuevo_id_cliente:
                    e["id_cliente"] = nuevo_id_cliente
                    self.id_cliente = nuevo_id_cliente
                
                # Actualizar nuevos campos si vienen en kwargs
                if "sexo" in kwargs: e["sexo"] = self.sexo = kwargs["sexo"]
                if "pelaje" in kwargs: e["pelaje"] = self.pelaje = kwargs["pelaje"]
                if "nacimiento" in kwargs: e["nacimiento"] = self.nacimiento = kwargs["nacimiento"]
                if "microchip" in kwargs: e["microchip"] = self.microchip = kwargs["microchip"]
                if "especie" in kwargs: e["especie"] = self.especie = kwargs["especie"]
                if "id_registro" in kwargs: e["id_registro"] = self.id_registro = kwargs["id_registro"]
                if "descripcion_equino" in kwargs: e["descripcion_equino"] = self.descripcion_equino = kwargs["descripcion_equino"]
                
                guardar_datos(datos)
                return True, "Perfil del equino actualizado correctamente."
                
        return False, "Equino no encontrado en la base de datos."
    
    def actualizar_salud_y_dieta(self, historial_medico, fechas_medicas, alimentacion):
        datos = cargar_datos()
        for e in datos["equinos"]:
            if e["id_equino"] == self.id_equino:
                e["historial_medico"] = historial_medico
                e["fechas_medicas"] = fechas_medicas
                e["alimentacion"] = alimentacion
                self.historial_medico = historial_medico
                self.fechas_medicas = fechas_medicas
                self.alimentacion = alimentacion
                guardar_datos(datos)
                return True, "Registro médico actualizado exitosamente."
        return False, "Equino no encontrado en la base de datos."
    
    def actualizar_imagen(self, nueva_ruta):
        datos = cargar_datos()
        for e in datos["equinos"]:
            if e["id_equino"] == self.id_equino:
                e["ruta_imagen"] = nueva_ruta
                self.ruta_imagen = nueva_ruta
                guardar_datos(datos)
                return True, "Imagen actualizada correctamente."
        return False, "Equino no encontrado en la base de datos."

class Inventario():
    def __init__(self, nombre, cantidad=0, caducidad="N/A", ultimo_abastecimiento=None, descripcion=""):
        self.nombre=nombre
        self.cantidad=cantidad
        self.caducidad=caducidad
        self.ultimo_abastecimiento=ultimo_abastecimiento if ultimo_abastecimiento else date.today().strftime("%d/%m/%Y")
        self.descripcion = descripcion

    def agregar_producto(self):
        datos = cargar_datos()
        
        for item in datos["inventario"]:
            if item["nombre"].lower() == self.nombre.lower():
                return False, "Ese producto ya existe en la bodega."
                
        nuevo_item = {
            "nombre": self.nombre,
            "cantidad": self.cantidad,
            "caducidad": self.caducidad,
            "ultimo_abastecimiento": self.ultimo_abastecimiento,
            "descripcion": self.descripcion
        }
        datos["inventario"].append(nuevo_item)
        guardar_datos(datos)
        return True, "Producto agregado exitosamente."
    
    @staticmethod
    def descontar_inventario(cantidades_seleccionadas):
        datos=cargar_datos()
        mensajes_error=[]

        for nombre_item, cant_pedida in cantidades_seleccionadas.items():
            if cant_pedida > 0:
                item_encontrado = next((i for i in datos["inventario"] if i["nombre"] == nombre_item), None)
                if not item_encontrado:
                    mensajes_error.append(f"Producto no encontrado: {nombre_item}")
                elif item_encontrado["cantidad"] < cant_pedida:
                    mensajes_error.append(f"Stock insuficiente de: {nombre_item}")

        if mensajes_error:
            return False, "\n".join(mensajes_error)

        for nombre_item, cant_pedida in cantidades_seleccionadas.items():
            if cant_pedida > 0:
                for i in datos["inventario"]:
                    if i["nombre"] == nombre_item:
                        i["cantidad"] -= cant_pedida
                        
        guardar_datos(datos)
        return True, "Ración registrada y descontada correctamente de la base de datos."
    
    def actualizar_producto(self):
        datos = cargar_datos()
        for item in datos["inventario"]:
            if item["nombre"].lower() == self.nombre.lower():
                item["cantidad"] = self.cantidad
                item["caducidad"] = self.caducidad
                item["ultimo_abastecimiento"] = self.ultimo_abastecimiento
                item["descripcion"] = self.descripcion
                guardar_datos(datos)
                return True, "Inventario actualizado correctamente."
        return False, "Producto no encontrado en la base de datos."

class Bitacora_salud():
    def __init__(self,id_registro, id_equino, fecha_herraje, fecha_desp, fecha_vacun,dieta_espec):
        self.id_registro=id_registro
        self.id_equino=id_equino
        self.fecha_herraje=fecha_herraje
        self.fecha_desp=fecha_desp
        self.fecha_vacun=fecha_vacun
        self.dieta_espec=dieta_espec

    def registrar_cuidado(self):
        datos=cargar_datos()
        nuevo_registro={
            "id_registro":self.id_registro,
            "id_equino": self.id_equino,
            "fecha_herraje":self.fecha_herraje,
            "fecha_desp":self.fecha_desp,
            "fecha_vacun":self.fecha_vacun,
            "dieta_espec":self.dieta_espec
        }
        datos["bitacoras"].append(nuevo_registro)
        guardar_datos(datos)
        return True, f"Cuidados registrados para el equino: {self.id_equino}"

    def generar_alerta(self, tipo_cuidado):
        reglas={
            "vacuna_anual":365,
            "vacuna_refuerzo":180,
            "herraje": 45,
            "desparasitacion":90 
        }

        if tipo_cuidado not in reglas:
            return False, "Tipo de cuidado no genera alerta o no existe."

        try:
            if "vacuna" in tipo_cuidado:
                fecha_str = self.fecha_vacun
            elif tipo_cuidado == "herraje":
                fecha_str = self.fecha_herraje
            elif tipo_cuidado == "desparasitacion":
                fecha_str = self.fecha_desp
            else:
                return False, "Tipo de cuidado no reconocido."

            ultima_fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            hoy = datetime.now()

            dias_pasados = (hoy - ultima_fecha).days
            plazo = reglas[tipo_cuidado]

            if dias_pasados >= plazo:
                mensaje = f"URGENTE: {tipo_cuidado} vencida hace {dias_pasados - plazo} días"
                return True, mensaje 
            
            return False, f"El cuidado de {tipo_cuidado} está al corriente."
        
        except Exception as e:
            return False, f"Error: Revisa el formato de la fecha: {e}"
        
    @staticmethod
    def validar_todos_los_cuidados():
        datos = cargar_datos()
        alertas_formales = []
        
        for eq in datos.get("equinos", []):
            # Usamos la lógica de tu compañera: crear un objeto Bitacora temporal
            # para usar su función 'generar_alerta'
            f = eq.get("fechas_medicas", {})
            b_temp = Bitacora_salud(
                id_registro=f"REG-{eq['id_equino']}",
                id_equino=eq['nombre'],
                fecha_herraje=datetime.strptime(f.get("Herraje", "01/01/2000"), "%d/%m/%Y").strftime("%Y-%m-%d"),
                fecha_desp=datetime.strptime(f.get("Desparasitación", "01/01/2000"), "%d/%m/%Y").strftime("%Y-%m-%d"),
                fecha_vacun=datetime.strptime(f.get("Vacuna", "01/01/2000"), "%d/%m/%Y").strftime("%Y-%m-%d") if "Vacuna" in f else "2000-01-01",
                dieta_espec=eq.get("alimentacion", "")
            )
            
            # Ejecutamos las reglas de negocio de tu compañera
            for tipo in ["herraje", "desparasitacion"]:
                hay_alerta, mensaje = b_temp.generar_alerta(tipo)
                if hay_alerta:
                    alertas_formales.append({"mensaje": mensaje, "equino": eq['nombre']})
        
        return alertas_formales

class Finanzas_pension():
    def __init__(self, id_pago,id_cliente, monto,fecha_pago, estado, servicio="General"):
        self.id_pago=id_pago
        self.id_cliente=id_cliente
        self.monto=monto
        self.fecha_pago=fecha_pago
        self.estado=estado
        self.servicio=servicio

    def registrar_pago(self):
        datos=cargar_datos()
        nuevo_pago={
            "id_pago":self.id_pago,
            "id_cliente":self.id_cliente,
            "monto":self.monto,
            "fecha_pago":self.fecha_pago,
            "estado":self.estado,
            "servicio": self.servicio
        }

        datos["finanzas"].append(nuevo_pago)
        guardar_datos(datos)
        return True, f"Pago de ${self.monto} registrado para el cliente {self.id_cliente}."

    def generar_estado_cuenta(self, id_cliente_buscado):
        datos=cargar_datos()
        historial=[p for p in datos["finanzas"] if p["id_cliente"]==id_cliente_buscado]

        total_pagado = sum(p["monto"] for p in historial if p["estado"] == "Pagado")
        pendiente = sum(p["monto"] for p in historial if p["estado"] == "Pendiente")

        return {
            "historial": historial,
            "total_pagado": total_pagado,
            "adeudo_total":pendiente
        }

    def saldar_deuda_pendiente(self):
        datos = cargar_datos()
        for p in datos["finanzas"]:
            if p["id_pago"] == self.id_pago:
                p["estado"] = "Pagado"
                p["fecha_pago"] = datetime.now().strftime("%Y-%m-%d") # Actualiza la fecha a hoy
                guardar_datos(datos)
                return True, f"El adeudo ha sido cobrado y registrado el día de hoy."
        return False, "No se encontró el registro del pago."

class Caballeriza():
    def __init__(self, id_caballeriza, estado,id_equino,dimensiones):
        self.id_caballeriza=id_caballeriza
        self.estado=estado
        self.id_equino=id_equino
        self.dimensiones=dimensiones

    def asignar_equino(self, id_nuevo_equino):
        datos=cargar_datos()
        for c in datos["caballerizas"]:
            if c["id_caballeriza"] == self.id_caballeriza:
                if c["estado"] == "Disponible":
                    c["estado"] = "Ocupada"
                    c["id_equino"] = id_nuevo_equino
                    self.estado = "Ocupada"
                    self.id_equino = id_nuevo_equino
                    guardar_datos(datos)
                    return True, f"Caballeriza {self.id_caballeriza} asignada al equino {id_nuevo_equino}."
                else:
                    return False, "La caballeriza no está disponible."
        return False, "Caballeriza no encontrada en la base de datos."
    
    def liberar_espacio(self):
        datos=cargar_datos()
        for c in datos["caballerizas"]:
            if c["id_caballeriza"] == self.id_caballeriza:
                c["estado"] = "Disponible"
                c["id_equino"] = None
                self.estado = "Disponible"
                self.id_equino = None
                guardar_datos(datos)
                return True, f"Caballeriza {self.id_caballeriza} ahora está libre."
        return False, "Caballeriza no encontrada en la base de datos."
    
    @staticmethod
    def modificar_dimensiones(accion):
        datos = cargar_datos()
        mapa = datos["mapa_caballerizas"]
        
        filas = len(mapa)
        columnas = len(mapa[0]) if filas > 0 else 0

        if accion == "agregar_fila":
            mapa.append([False] * columnas)
        
        elif accion == "quitar_fila":
            if filas <= 1: return False, "No puedes tener menos de 1 fila."
            # Validar que la última fila esté vacía antes de borrarla
            if any(mapa[-1]): return False, "Hay caballos en la última fila. Libera esas caballerizas primero."
            mapa.pop()

        elif accion == "agregar_col":
            for fila in mapa: fila.append(False)

        elif accion == "quitar_col":
            if columnas <= 1: return False, "No puedes tener menos de 1 columna."
            # Validar que la última columna esté vacía antes de borrarla
            if any(fila[-1] for fila in mapa): return False, "Hay caballos en la última columna. Libera esas caballerizas primero."
            for fila in mapa: fila.pop()

        guardar_datos(datos)
        return True, "Mapa redimensionado correctamente."

class Alerta_sistema():
    def __init__(self,id_alerta, tipo, mensaje, fecha_emision, estado):
        self.id_alerta=id_alerta
        self.tipo=tipo
        self.mensaje=mensaje
        self.fecha_emision=fecha_emision
        self.estado=estado

    def generar_alerta_medica(self,mensaje_salud):
        datos=cargar_datos()
        nueva_alerta={
            "id_alerta":self.id_alerta,
            "tipo":"Médica",
            "mensaje":mensaje_salud,
            "fecha_emision":datetime.now().strftime("%Y-%m-%d"),
            "estado":"Pendiente"
        }
        datos["alertas"].append(nueva_alerta)
        guardar_datos(datos)
        return True, "Nueva alerta médica registrada en el sistema."

    def generar_alerta_cobro(self, id_cliente):
        datos=cargar_datos()

        pendientes=[p for p in datos["finanzas"] if p["id_cliente"] == id_cliente and p["estado"] == "Pendiente"]

        if pendientes:
            total_adeudo=sum(p["monto"] for p in pendientes)
            self.mensaje=f"El cliente {id_cliente} tiene un adeudo de ${total_adeudo}."
            self.tipo="Finanzas"

            nueva_alerta={
                "id_alerta": self.id_alerta,
                "tipo": self.tipo,
                "mensaje": self.mensaje,
                "fecha_emision": datetime.now().strftime("%Y-%m-%d"),
                "estado": "Pendiente"
            }

            datos["alertas"].append(nueva_alerta)
            guardar_datos(datos)
            return True, self.mensaje
        
        return False, "El cliente no tiene adeudos pendientes."

    def marcar_atendida(self):
        datos=cargar_datos()
        encontrado=False

        for a in datos["alertas"]:
            if a["id_alerta"]==self.id_alerta:
                #cambio de pendiente a atendida
                a["estado"]="Atendida"
                self.estado="Atendida"
                encontrado=True
                break

        if encontrado:
            guardar_datos(datos)
            print(f"Alerta {self.id_alerta} marcada como atendida.")
            return True, f"Alerta {self.id_alerta} marcada como atendida."
        else:
            return False, "No se encontró la alerta en la base de datos."
        
    @staticmethod
    def obtener_alertas_dinamicas():
        datos = cargar_datos()
        alertas = []
        hoy = datetime.now()

        # 1. Escanear Salud de Equinos
        for eq in datos.get("equinos", []):
            fechas = eq.get("fechas_medicas", {})
            for proc, fecha_str in fechas.items():
                try:
                    fecha_proc = datetime.strptime(fecha_str, "%d/%m/%Y")
                    # Si la fecha ya pasó o es hoy
                    if hoy >= fecha_proc:
                        dias_retraso = (hoy - fecha_proc).days
                        if dias_retraso > 0:
                            alertas.append({"tipo": "Médica", "mensaje": f"URGENTE: '{proc}' vencido para el caballo {eq['nombre']} hace {dias_retraso} días.", "color": "#ef4444"})
                        else:
                            alertas.append({"tipo": "Médica", "mensaje": f"HOY: '{proc}' programado para el caballo {eq['nombre']}.", "color": "#f59e0b"})
                except: pass
        
        # 2. Escanear Inventario Bajo
        for item in datos.get("inventario", []):
            if item["cantidad"] <= 5:
                alertas.append({"tipo": "Inventario", "mensaje": f"STOCK BAJO: Quedan solo {item['cantidad']} unidades de '{item['nombre']}'.", "color": "#f59e0b"})

        return alertas

class Estadistica_reporte():

    def __init__(self, total_equinos, ingresos_mes, tasa_ocupacion):
        self.total_equinos=total_equinos
        self.ingresos_mes=ingresos_mes
        self.tasa_ocupacion=tasa_ocupacion

    def graficar_tendencias(self):
        datos=cargar_datos()

        df=pd.DataFrame(datos["finanzas"])

        if df.empty:
            return False, "No hay datos financieros para graficar."
        
        df['fecha_pago']=pd.to_datetime(df['fecha_pago']) #agrupacion de las fechas por mes
        #suma de montos registrados como "Pagado"
        ingresos_por_fecha=df[df['estado'] == 'Pagado'].groupby('fecha_pago')['monto'].sum()

        if ingresos_por_fecha.empty:
            return False, "No hay ingresos pagados registrados para graficar."

        plt.figure(figsize=(8, 4))
        ingresos_por_fecha.plot(kind='bar', color='skyblue')
        plt.title('Reporte de Ingresos Mensuales')
        plt.xlabel('Fecha')
        plt.ylabel('Total Recaudado ($)')
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.show()
        return True, "Gráfica generada exitosamente."

    def exportar_estado_cuenta(self, id_cliente):
        datos=cargar_datos()

        cliente = next((c for c in datos["clientes"] if c["id_cliente"] == id_cliente), None)
        historial = [p for p in datos["finanzas"] if p["id_cliente"] == id_cliente]

        if not cliente:
            return False, "Cliente no encontrado."
        
        nombre_archivo = f"Estado_Cuenta_{id_cliente}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        ruta_completa = os.path.join(CARPETA_REPORTES, nombre_archivo)

        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(f"SISTEMA INTEGRAL DE GESTIÓN ECUESTRE (SIGE)\n")
            f.write(f"ESTADO DE CUENTA: {cliente['nom_completo']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"{'Fecha':<12} | {'Monto':<10} | {'Estado':<10}\n")

            total_adeudo = 0
            for pago in historial:
                f.write(f"{pago['fecha_pago']:<12} | ${pago['monto']:<9} | {pago['estado']}\n")
                if pago['estado'] == 'Pendiente':
                    total_adeudo += pago['monto']

            f.write("-" * 40 + "\n")
            f.write(f"TOTAL PENDIENTE DE PAGO: ${total_adeudo}\n")
            f.write(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y')}\n")

        return True, ruta_completa
    
    def calcular_ingresos(self):
        datos=cargar_datos()
        df = pd.DataFrame(datos["finanzas"])
        if df.empty:
            return 0
        
        self.ingresos_mes = df[df['estado'] == 'Pagado']['monto'].sum()
        return self.ingresos_mes
    
    @staticmethod
    def obtener_metricas_dashboard():
        datos = cargar_datos()
        
        # 1. Total de Equinos
        total_eq = len(datos.get("equinos", []))
        
        # 2. Ocupación de Caballerizas
        mapa = datos.get("mapa_caballerizas", [])
        total_stables = 0
        ocupadas = 0
        if mapa:
            total_stables = len(mapa) * len(mapa[0])
            for fila in mapa:
                ocupadas += sum(1 for c in fila if c is True)
        
        # 3. Alertas de Inventario (Stock <= 5)
        alertas_inv = sum(1 for item in datos.get("inventario", []) if item["cantidad"] <= 5)
        
        return {
            "total_equinos": total_eq,
            "ocupadas": ocupadas,
            "total_stables": total_stables,
            "alertas_inventario": alertas_inv
        }
