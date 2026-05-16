import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import pandas as pd  
import json          
import os
import datetime 
import calendar  
import shutil
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt 
from datetime import datetime as dt

# --- IMPORTACIÓN DESDE EL BACKEND ---
from backend import (
    Usuario, Cliente, Equino, Inventario, Bitacora_salud, 
    Finanzas_pension, Estadistica_reporte, Caballeriza, Alerta_sistema, 
    cargar_datos, guardar_datos, CARPETA_IMAGENES, IMAGEN_DEFAULT_PATH,
    CARPETA_RECETAS, CARPETA_REPORTES
)


# ========================================================================
# 1. CONFIGURACIÓN VISUAL Y DE RUTAS DEL SIGE
# ========================================================================

COLOR_FONDO = "#0f172a"          
COLOR_PANEL_LATERAL = "#1e293b"  
COLOR_ACENTO = "#10b981" # Verde - Acciones positivas / Trabajo realizado
COLOR_PROXIMA = "#06b6d4" # Cian - Sugerencia de próxima sesión

ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue")

# ========================================================================
# 2. UTILIDADES DEL SISTEMA (IMÁGENES Y VISTAS)
# ========================================================================

def buscar_equino_en_lista(nombre_buscado):
    """
    Busca un equino específico por su nombre en la base de datos.

    Args:
        nombre_buscado (str): Nombre del equino a localizar.

    Returns:
        dict/None: Diccionario con datos del equino o None si no se encuentra.
    """
    datos = cargar_datos()
    for e in datos["equinos"]:
        if e["nombre"].lower() == nombre_buscado.lower():
            return e
    return None

def limpiar_contenedor(contenedor):
    """
    Elimina todos los widgets hijos de un contenedor CTk.
    Se utiliza para realizar transiciones suaves entre vistas.

    Args:
        contenedor (ctk.CTkFrame): El contenedor a vaciar.
    """
    for widget in contenedor.winfo_children():
        widget.destroy()

def procesar_imagen_equino(ruta_origen, nombre_equino):
    """
    Copia una imagen externa a la carpeta del sistema y genera una miniatura.

    Args:
        ruta_origen (str): Ruta completa del archivo original.
        nombre_equino (str): Nombre del animal para renombrar el archivo.

    Returns:
        str/None: Nueva ruta de la imagen en el sistema o None en caso de error.
    """
    if not ruta_origen: return None
    try:
        ext = os.path.splitext(ruta_origen)[1]
        nuevo_nombre = f"{nombre_equino.replace(' ', '_').lower()}{ext}"
        ruta_destino = os.path.join(CARPETA_IMAGENES, nuevo_nombre)
        shutil.copy2(ruta_origen, ruta_destino) 
        
        with Image.open(ruta_destino) as img:
            # Redimensión optimizada para visualización fluida en la interfaz
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            img.save(ruta_destino)
        return ruta_destino
    except Exception as e:
        messagebox.showerror("Error", f"Fallo al procesar imagen:\n{e}")
        return None

def cargar_imagen_a_label(lbl_imagen, ruta_imagen=None):
    """
    Carga y muestra una imagen en un Label de CustomTkinter.

    Args:
        lbl_imagen (ctk.CTkLabel): El widget donde se mostrará la imagen.
        ruta_imagen (str, optional): Ruta del archivo. Si es None, carga la imagen por defecto.
    """
    try:
        if ruta_imagen and os.path.exists(ruta_imagen):
            pil_image = Image.open(ruta_imagen)
        else:
            # Fallback a imagen por defecto si la ruta es inválida
            if os.path.exists(IMAGEN_DEFAULT_PATH): 
                pil_image = Image.open(IMAGEN_DEFAULT_PATH)
            else: 
                pil_image = Image.new('RGB', (200, 200), color = '#374151') 
        
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(200, 200))
        lbl_imagen.configure(image=ctk_image, text="") 
        lbl_imagen.image = ctk_image 
    except:
        lbl_imagen.configure(text="Sin Imagen")

def marcar_como_realizado(eq_data, tipo_proc, fecha_prog, callback_refresh=None, fecha_realizacion=None):
    """
    Registra un procedimiento médico como realizado, actualiza el historial y agenda el siguiente.
    
    Args:
        eq_data (dict): Datos del equino.
        tipo_proc (str): Nombre del procedimiento (Herraje, Vacuna, etc).
        fecha_prog (str): Fecha en la que estaba programado (DD/MM/AAAA).
        callback_refresh (function, optional): Función para refrescar la UI tras el cambio.
        fecha_realizacion (str, optional): Fecha de realización efectiva (DD/MM/AAAA). Si es None, usa hoy.
    """
    if messagebox.askyesno("Confirmar", f"¿Confirmas que se ha realizado el procedimiento de '{tipo_proc}' programado para el {fecha_prog}?"):
        # 1. Mover al historial
        # Convertir fecha_realizacion a formato ISO (AAAA-MM-DD) para el historial
        if fecha_realizacion:
            try:
                f_iso = datetime.datetime.strptime(fecha_realizacion, "%d/%m/%Y").strftime("%Y-%m-%d")
            except:
                f_iso = datetime.date.today().strftime("%Y-%m-%d")
        else:
            f_iso = datetime.date.today().strftime("%Y-%m-%d")

        nuevo_registro = {
            "fecha": f_iso,
            "tipo": tipo_proc,
            "desc": f"Tratamiento programado ({fecha_prog}) realizado exitosamente."
        }
        historial = eq_data.get("historial_medico", [])
        historial.append(nuevo_registro)

        # 2. Calcular la siguiente fecha automática (Agenda)
        fechas = eq_data.get("fechas_medicas", {})
        dias_sumar = 0
        if tipo_proc == "Herraje": dias_sumar = 45
        elif tipo_proc == "Desparasitación": dias_sumar = 90
        elif tipo_proc == "Vacuna": dias_sumar = 365
        elif tipo_proc == "Odontología": dias_sumar = 180
        
        if dias_sumar > 0:
            nueva_fecha_obj = datetime.date.today() + datetime.timedelta(days=dias_sumar)
            fechas[tipo_proc] = nueva_fecha_obj.strftime("%d/%m/%Y")
        else:
            if tipo_proc in fechas: del fechas[tipo_proc]

        # 3. Guardar en backend
        eq_temp = Equino(id_equino=eq_data["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
        exito, msj = eq_temp.actualizar_salud_y_dieta(historial, fechas, eq_data.get("alimentacion", ""))
        
        if exito:
            messagebox.showinfo("Éxito", "¡Tratamiento completado! Se ha movido al historial y se ha agendado la próxima cita automáticamente.")
            if callback_refresh: callback_refresh()
        else:
            messagebox.showerror("Error", msj)

# ========================================================================
# 3. MÓDULOS DE INTERFAZ (VISTAS PRINCIPALES)
# ========================================================================

def vista_dashboard(frame_contenido, rol, nombre):
    """
    Renderiza la pantalla de bienvenida y el resumen estadístico principal.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal de la aplicación.
        rol (str): Rol del usuario actual para personalizar la vista.
        nombre (str): Nombre del usuario logueado.
    """
    limpiar_contenedor(frame_contenido)
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=30, padx=40, fill="x")
    
    ctk.CTkLabel(f_header, text=f"¡Bienvenido, {nombre}!", font=("Roboto", 32, "bold")).pack(anchor="w")
    ctk.CTkLabel(f_header, text=f"Resumen de {rol} - {datetime.date.today().strftime('%d/%m/%Y')}", 
                 font=("Roboto", 14), text_color="gray").pack(anchor="w")

    f_cards = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_cards.pack(fill="both", expand=True, padx=40)

    # Inyección de métricas desde el motor de reportes del backend
    m = Estadistica_reporte.obtener_metricas_dashboard()

    # Generación dinámica de tarjetas informativas (Quick Stats)
    for i, (txt, val, col, icon) in enumerate([
        ("Equinos Registrados", m["total_equinos"], "#3b82f6", "🐎"),
        (f"Ocupación ({ (m['ocupadas']/m['total_stables']*100) if m['total_stables']>0 else 0 :.0f}%)", f"{m['ocupadas']}/{m['total_stables']}", COLOR_ACENTO, "🏠"),
        ("Alertas de Stock", m["alertas_inventario"], "#ef4444" if m["alertas_inventario"]>0 else "#f59e0b", "🌾")
    ]):
        # Card Container
        card = ctk.CTkFrame(f_cards, fg_color="#1e293b", corner_radius=20, border_width=1, border_color="#334155")
        card.grid(row=0, column=i, padx=15, pady=10, sticky="nsew")
        
        # Glow effect or accent line at the top
        accent_bar = ctk.CTkFrame(card, fg_color=col, height=4, corner_radius=2)
        accent_bar.pack(fill="x", padx=30, pady=(0, 10))

        # Icon and Label
        f_top = ctk.CTkFrame(card, fg_color="transparent")
        f_top.pack(pady=(10, 0), padx=20, fill="x")
        
        ctk.CTkLabel(f_top, text=icon, font=("Roboto", 24)).pack(side="left")
        ctk.CTkLabel(f_top, text=txt.upper(), font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(side="left", padx=10)
        
        # Main Value (Huge and bold)
        ctk.CTkLabel(card, text=str(val), font=("Roboto", 48, "bold"), text_color="white").pack(pady=(10, 20))
        
        # Trend or sub-text
        sub_text = "Estado: Estable" if i != 2 else (f"{val} artículos bajos" if val > 0 else "Stock Completo")
        ctk.CTkLabel(card, text=sub_text, font=("Roboto", 12), text_color=col).pack(pady=(0, 20))

    f_cards.grid_columnconfigure((0, 1, 2), weight=1)

    # Contenedor para Alertas y Accesos Rápidos
    f_inferior = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_inferior.pack(fill="both", expand=True, padx=40, pady=(20, 20))
    
    # --- PANEL IZQUIERDO: Alertas ---
    f_col_alertas = ctk.CTkFrame(f_inferior, fg_color="transparent")
    f_col_alertas.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    ctk.CTkLabel(f_col_alertas, text="Alertas del Sistema", font=("Roboto", 18, "bold")).pack(pady=(10, 10), anchor="w")
    f_alertas = ctk.CTkScrollableFrame(f_col_alertas, fg_color="transparent", height=250)
    f_alertas.pack(fill="both", expand=True)
    
    # --- PANEL DERECHO: Accesos Rápidos (NUEVO) ---
    f_col_accesos = ctk.CTkFrame(f_inferior, fg_color=COLOR_PANEL_LATERAL, corner_radius=15, width=300)
    f_col_accesos.pack(side="right", fill="both", padx=(10, 0))
    f_col_accesos.pack_propagate(False)

    ctk.CTkLabel(f_col_accesos, text="ACCESOS RÁPIDOS", font=("Roboto", 13, "bold"), text_color=COLOR_ACENTO).pack(pady=20)
    
    def add_quick_link(icon, text, cmd):
        btn = ctk.CTkButton(f_col_accesos, text=f"{icon}  {text}", anchor="w", fg_color="transparent", 
                            hover_color="#334155", height=40, font=("Roboto", 13), command=cmd)
        btn.pack(fill="x", padx=20, pady=5)

    if rol != "Recepcionista":
        add_quick_link("🍎", "Dar de Comer Hoy", lambda: vista_bitacora(frame_contenido, vista_inicial="alimentacion"))
        add_quick_link("📅", "Agenda Médica", lambda: vista_bitacora(frame_contenido, vista_inicial="ficha"))
    
    add_quick_link("📦", "Revisar Stock Bajo", lambda: vista_inventario(frame_contenido))
    
    if rol != "Personal Operativo":
        add_quick_link("👥", "Directorio Clientes", lambda: vista_clientes(frame_contenido))

    # Obtenemos las alertas en tiempo real
    alertas_pendientes = Alerta_sistema.obtener_alertas_dinamicas()
    
    if not alertas_pendientes:
        f_vacio = ctk.CTkFrame(f_alertas, fg_color="#1e293b", corner_radius=10)
        f_vacio.pack(fill="x", pady=5)
        ctk.CTkLabel(f_vacio, text="✅ Todo está al corriente.", font=("Roboto", 14), text_color="#10b981").pack(pady=20)
    else:
        for alerta in alertas_pendientes:
            f_alerta = ctk.CTkFrame(f_alertas, fg_color="#1e293b", corner_radius=8, border_width=1, border_color=alerta["color"])
            f_alerta.pack(fill="x", pady=5)
            icono = "💊" if alerta["tipo"] == "Médica" else "🌾"
            ctk.CTkLabel(f_alerta, text=f"{icono} {alerta['mensaje']}", font=("Roboto", 14), wraplength=400, justify="left").pack(side="left", padx=15, pady=15)

# ========================================================================
# 4. BITÁCORA (INTEGRACIÓN TOTAL MÉDICA Y NUTRICIONAL)
# ========================================================================

def vista_bitacora(frame_contenido, vista_inicial="ficha"):
    """
    Controlador de la Bitácora. Gestiona la salud, historial y 
    alimentación diaria de los equinos.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal.
        vista_inicial (str): Sub-vista a mostrar por defecto ("ficha", "alimentacion", "historial").
    """
    limpiar_contenedor(frame_contenido)
    # Header de la vista
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Bitácora Médica y Nutricional", font=("Roboto", 28, "bold")).pack(side="left")

    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # --- PANEL IZQUIERDO: Listado de Equinos ---
    panel_izq = ctk.CTkFrame(frame_principal, width=280, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_izq.pack(side="left", fill="y", padx=(0, 20))
    
    ctk.CTkLabel(panel_izq, text="SELECCIONAR PACIENTE", font=("Roboto", 13, "bold"), text_color="#9ca3af").pack(pady=(20, 10))
    
    lista_scroll = ctk.CTkScrollableFrame(panel_izq, fg_color="transparent")
    lista_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    # --- PANEL DERECHO: Contenido Principal ---
    panel_der = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_der.pack(side="right", fill="both", expand=True)

    contenedor_vistas = ctk.CTkFrame(panel_der, fg_color="transparent")
    contenedor_vistas.pack(fill="both", expand=True, pady=10)

    frame_botones = ctk.CTkFrame(panel_der, fg_color="transparent")
    frame_botones.pack(side="bottom", fill="x", pady=20, padx=20)

    # El estado ahora persiste la sub-vista seleccionada
    estado = {"equino_actual_id": None, "sub_vista": vista_inicial}

    def seleccionar_equino(id_eq):
        """Actualiza el animal seleccionado y renderiza la sub-vista actual."""
        estado["equino_actual_id"] = id_eq
        if estado["sub_vista"] == "alimentacion":
            vista_alimentacion()
        elif estado["sub_vista"] == "historial":
            vista_historial()
        elif estado["sub_vista"] == "agendar":
            vista_registrar()
        else:
            mostrar_ficha()

    datos_bd = cargar_datos()
    for eq in datos_bd["equinos"]:
        btn = ctk.CTkButton(lista_scroll, text=eq["nombre"], 
                            fg_color="transparent", text_color="white", anchor="w",
                            hover_color="#334155", height=35,
                            command=lambda eid=eq["id_equino"]: seleccionar_equino(eid))
        btn.pack(pady=2, fill="x")

    def obtener_equipo_actual():
        eid = estado["equino_actual_id"]
        if not eid: return None
        datos = cargar_datos()
        return next((e for e in datos["equinos"] if e["id_equino"] == eid), None)

    def mostrar_ficha():
        limpiar_contenedor(contenedor_vistas)
        eq = obtener_equipo_actual()
        if not eq: return

        f_top = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        f_top.pack(fill="x", padx=20, pady=10)
        
        lbl_img = ctk.CTkLabel(f_top, text="", corner_radius=10, fg_color="#1f2937")
        lbl_img.pack(side="left", padx=(0, 20))
        cargar_imagen_a_label(lbl_img, eq.get("ruta_imagen"))

        f_info = ctk.CTkFrame(f_top, fg_color="transparent")
        f_info.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(f_info, text=f"Ficha Médica: {eq['nombre']}", font=("Roboto", 24, "bold")).pack(anchor="w", pady=(10, 5))
        
        # ==========================================================
        # ANÁLISIS DE ESTADO (SEMÁFORO)
        # ==========================================================
        fechas = eq.get("fechas_medicas", {})
        hoy = datetime.date.today()
        alertas_activas = []
        casi_vencido = []

        for proc, f_str in fechas.items():
            try:
                f_obj = datetime.datetime.strptime(f_str, "%d/%m/%Y").date()
                dias_restantes = (f_obj - hoy).days
                if dias_restantes < 0:
                    alertas_activas.append(f"• {proc} VENCIDO (hace {abs(dias_restantes)} días)")
                elif dias_restantes <= 7:
                    casi_vencido.append(f"• {proc} próximo a vencer ({dias_restantes} días)")
            except: pass

        if alertas_activas:
            status_color = "#ef4444" # Rojo
            status_text = "⚠️ ESTADO: REQUIERE ATENCIÓN URGENTE"
            detalles = "\n".join(alertas_activas)
        elif casi_vencido:
            status_color = "#f59e0b" # Naranja
            status_text = "⏳ ESTADO: PRÓXIMAS CITAS CERCANAS"
            detalles = "\n".join(casi_vencido)
        else:
            status_color = "#10b981" # Verde
            status_text = "✅ ESTADO: ÓPTIMO (Protocolos al día)"
            detalles = "Todos los procedimientos médicos están al corriente."

        banner = ctk.CTkFrame(f_info, fg_color="transparent", border_width=1, border_color=status_color, corner_radius=10)
        banner.pack(fill="x", pady=5)
        ctk.CTkLabel(banner, text=status_text, font=("Roboto", 14, "bold"), text_color=status_color).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(banner, text=detalles, font=("Roboto", 12), text_color="#9ca3af", justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        # ==========================================================

        btn_cal = ctk.CTkButton(f_info, text="🗓️ VER AGENDA MÉDICA", fg_color="#3b82f6", font=("Roboto", 13, "bold"), 
                                height=35, command=lambda: mostrar_calendario_medico(eq, on_refresh=mostrar_ficha))
        btn_cal.pack(anchor="w", pady=(15, 10))

        # --- Listado de Citas Agendadas ---
        ctk.CTkLabel(contenedor_vistas, text="CITAS AGENDADAS (PENDIENTES)", font=("Roboto", 16, "bold")).pack(anchor="w", padx=30, pady=(20, 5))
        
        tabla = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        tabla.pack(fill="x", padx=30, pady=10)
        
        # Header de tabla
        h_table = ctk.CTkFrame(tabla, fg_color="#1e293b", height=35)
        h_table.pack(fill="x", pady=2)
        ctk.CTkLabel(h_table, text="PROCEDIMIENTO", font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(side="left", padx=20)
        ctk.CTkLabel(h_table, text="FECHA PROGRAMADA", font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(side="right", padx=140)

        for proc, fecha in eq.get("fechas_medicas", {}).items():
            f_row = ctk.CTkFrame(tabla, fg_color="#0f172a", height=45, corner_radius=8)
            f_row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(f_row, text=proc, font=("Roboto", 14, "bold")).pack(side="left", padx=20)
            
            # Botón para marcar como realizado
            btn_done = ctk.CTkButton(f_row, text="MARCAR COMO REALIZADO", width=180, height=28, fg_color=COLOR_ACENTO,
                                     font=("Roboto", 11, "bold"), command=lambda p=proc, f=fecha: marcar_como_realizado(eq, p, f, callback_refresh=mostrar_ficha))
            btn_done.pack(side="right", padx=10)
            
            ctk.CTkLabel(f_row, text=fecha, font=("Roboto", 14, "bold"), text_color="#3b82f6").pack(side="right", padx=20)


    def vista_registrar():
        eq = obtener_equipo_actual()
        if not eq: return messagebox.showwarning("Aviso", "Selecciona un equino.")
        limpiar_contenedor(contenedor_vistas)
        
        ctk.CTkLabel(contenedor_vistas, text=f"Agendar Nuevo Tratamiento - {eq['nombre']}", font=("Roboto", 20, "bold")).pack(pady=20)
        
        f_reg = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        f_reg.pack(pady=10)

        def add_row(label, placeholder, width=350, values=None):
            ctk.CTkLabel(f_reg, text=label, font=("Roboto", 14, "bold")).pack(anchor="w", pady=(10, 0))
            if values: w = ctk.CTkComboBox(f_reg, values=values, width=width)
            else: w = ctk.CTkEntry(f_reg, placeholder_text=placeholder, width=width)
            w.pack(pady=(2, 10))
            return w

        c_tipo = add_row("Tipo de Procedimiento:", "", values=["Herraje", "Desparasitación", "Vacuna", "Curación", "Odontología"])
        e_fecha_prog = add_row("Fecha Programada (Agenda):", "DD/MM/AAAA")
        e_fecha_prog.insert(0, datetime.date.today().strftime("%d/%m/%Y"))
        
        e_trato = add_row("Tratamiento / Dosis Sugerida:", "Ej: Dosis 5ml")
        e_notas = add_row("Notas Adicionales:", "Observaciones previas")

        def exportar_receta_txt():
            tipo = c_tipo.get()
            trato = e_trato.get().strip()
            notas = e_notas.get().strip()
            fecha_prog = e_fecha_prog.get().strip()

            if not trato:
                return messagebox.showwarning("Atención", "Escribe el tratamiento para generar la receta.")

            nombre_sugerido = f"Receta_{eq['nombre']}_{datetime.date.today().strftime('%Y%m%d')}.txt"
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialdir=CARPETA_RECETAS,
                initialfile=nombre_sugerido,
                title="Guardar Receta Médica",
                filetypes=[("Archivos de texto", "*.txt")]
            )
            if not ruta_guardado: return

            try:
                with open(ruta_guardado, 'w', encoding='utf-8') as f:
                    f.write("="*50 + "\n")
                    f.write("      SISTEMA INTEGRAL DE GESTIÓN ECUESTRE (SIGE)      \n")
                    f.write("              RECETA MÉDICA VETERINARIA                \n")
                    f.write("="*50 + "\n\n")
                    f.write(f"PACIENTE (EQUINO): {eq['nombre']}\n")
                    f.write(f"PROPIETARIO: {next((c['nom_completo'] for c in cargar_datos()['clientes'] if c['id_cliente'] == eq['id_cliente']), 'N/A')}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(f"PROCEDIMIENTO: {tipo}\n")
                    f.write(f"FECHA PROGRAMADA: {fecha_prog}\n")
                    f.write(f"INDICACIONES / DOSIS:\n   {trato}\n\n")
                    if notas: f.write(f"OBSERVACIONES:\n   {notas}\n\n")
                    f.write("\n\n" + " "*15 + "__________________________\n")
                    f.write(" "*18 + "Firma del Responsable\n")
                messagebox.showinfo("Éxito", f"Receta guardada exitosamente.")
            except Exception as e: messagebox.showerror("Error", f"No se pudo generar: {e}")

        def agendar_en_sistema():
            tipo = c_tipo.get()
            fecha_str = e_fecha_prog.get().strip()
            try:
                datetime.datetime.strptime(fecha_str, "%d/%m/%Y")
            except ValueError:
                return messagebox.showwarning("Formato", "La fecha debe ser DD/MM/AAAA.")

            fechas = eq.get("fechas_medicas", {})
            fechas[tipo] = fecha_str
            eq_temp = Equino(id_equino=eq["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
            exito, msj = eq_temp.actualizar_salud_y_dieta(eq.get("historial_medico", []), fechas, eq.get("alimentacion", ""))
            
            if exito:
                messagebox.showinfo("Éxito", f"'{tipo}' agendado para el {fecha_str}.")
                mostrar_ficha()
            else: messagebox.showerror("Error", msj)

        # --- BOTONES DE ACCIÓN ---
        f_btns = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        f_btns.pack(pady=30)

        ctk.CTkButton(f_btns, text="AGENDAR EN BITÁCORA", fg_color=COLOR_ACENTO, hover_color="#059669", 
                       font=("Roboto", 14, "bold"), height=40, width=200, command=agendar_en_sistema).pack(side="left", padx=10)
        
        ctk.CTkButton(f_btns, text="📄 EXPORTAR RECETA", fg_color="#3b82f6", hover_color="#2563eb", 
                       font=("Roboto", 14, "bold"), height=40, width=200, command=exportar_receta_txt).pack(side="left", padx=10)

    def vista_historial():
        eq = obtener_equipo_actual()
        if not eq: return
        limpiar_contenedor(contenedor_vistas)
        
        f_head = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        f_head.pack(fill="x", padx=30, pady=20)
        ctk.CTkLabel(f_head, text=f"Historial Médico - {eq['nombre']}", font=("Roboto", 20, "bold")).pack(side="left")
        
        def exportar_receta_global():
            # NUEVO: Te abre una ventana para que elijas dónde guardarlo
            nombre_sugerido = f"Receta_{eq['nombre']}_{datetime.date.today().strftime('%Y%m%d')}.txt"
            ruta_guardado = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialdir=CARPETA_RECETAS,
                initialfile=nombre_sugerido,
                title="Exportar Reporte Médico / Receta",
                filetypes=[("Archivos de texto", "*.txt")]
            )
            if not ruta_guardado: return

            try:
                with open(ruta_guardado, 'w', encoding='utf-8') as f:
                    f.write("="*50 + "\n")
                    f.write("      SISTEMA INTEGRAL DE GESTIÓN ECUESTRE (SIGE)      \n")
                    f.write("              REPORTE MÉDICO COMPLETO                  \n")
                    f.write("="*50 + "\n\n")
                    f.write(f"PACIENTE (EQUINO): {eq['nombre']}\n")
                    f.write(f"RAZA: {eq['raza']}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write("HISTORIAL DE TRATAMIENTOS:\n")
                    for reg in eq.get("historial_medico", []):
                        f.write(f"- {reg['fecha']} | {reg['tipo']}: {reg['desc']}\n")
                    f.write("\n\n" + " "*15 + "__________________________\n")
                    f.write(" "*18 + "Firma del Responsable\n")
                messagebox.showinfo("Éxito", f"Reporte exportado en:\n{ruta_guardado}")
            except Exception as e: messagebox.showerror("Error", f"Fallo al exportar: {e}")

        ctk.CTkButton(f_head, text="📥 EXPORTAR TXT", fg_color="#3b82f6", width=120, command=exportar_receta_global).pack(side="right")
        
        historial = eq.get("historial_medico", [])
        if not historial: 
            ctk.CTkLabel(contenedor_vistas, text="No hay registros médicos aún.", text_color="gray").pack(pady=40)
        else:
            for reg in reversed(historial):
                f_reg = ctk.CTkFrame(contenedor_vistas, fg_color="#1e293b", corner_radius=12, border_width=1, border_color="#334155")
                f_reg.pack(fill="x", padx=40, pady=8)
                
                f_h = ctk.CTkFrame(f_reg, fg_color="transparent")
                f_h.pack(fill="x", padx=15, pady=(10, 5))
                ctk.CTkLabel(f_h, text=f"📅 {reg['fecha']}", font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(side="left")
                ctk.CTkLabel(f_h, text=reg['tipo'].upper(), font=("Roboto", 13, "bold"), text_color=COLOR_ACENTO).pack(side="right")
                
                ctk.CTkLabel(f_reg, text=reg['desc'], font=("Roboto", 14), justify="left", wraplength=600).pack(anchor="w", padx=15, pady=(0, 15))

    def vista_alimentacion():
        eq = obtener_equipo_actual()
        if not eq: return
        limpiar_contenedor(contenedor_vistas)
        f_split = ctk.CTkFrame(contenedor_vistas, fg_color="transparent")
        f_split.pack(fill="both", expand=True, padx=20, pady=10)
        
        f_dieta = ctk.CTkFrame(f_split)
        f_dieta.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(f_dieta, text=f"Dieta Sugerida: {eq['nombre']}", font=("Roboto", 18, "bold")).pack(pady=(10, 5))
        caja_dieta = ctk.CTkTextbox(f_dieta, height=60); caja_dieta.pack(padx=20, pady=(0, 10), fill="x")
        caja_dieta.insert("1.0", eq.get("alimentacion", ""))

        def guardar_dieta():
            nueva_dieta = caja_dieta.get("1.0", "end").strip()
            eq_temp = Equino(id_equino=eq["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
            exito, msj = eq_temp.actualizar_salud_y_dieta(eq.get("historial_medico", []), eq.get("fechas_medicas", {}), nueva_dieta)
            if exito: messagebox.showinfo("Éxito", "Dieta actualizada en la base de datos.")

        ctk.CTkButton(f_dieta, text="Guardar Cambios", fg_color="#3b82f6", command=guardar_dieta).pack()
        
        ctk.CTkLabel(f_dieta, text="Armar Ración Manual:", font=("Roboto", 16, "bold"), text_color=COLOR_ACENTO).pack(pady=(15, 5))
        
        datos = cargar_datos()
        inventario = datos.get("inventario", [])
        seleccion_actual = {item["nombre"]: 0 for item in inventario}
        
        labels_cantidades = {}
        f_selectores = ctk.CTkScrollableFrame(f_dieta, fg_color="transparent", height=300)
        f_selectores.pack(fill="both", expand=True, padx=10, pady=5)

        def actualizar_cantidad(item_nombre, incremento):
            if seleccion_actual[item_nombre] + incremento >= 0:
                seleccion_actual[item_nombre] += incremento
                labels_cantidades[item_nombre].configure(text=str(seleccion_actual[item_nombre]))

        for item in inventario:
            f_row = ctk.CTkFrame(f_selectores, fg_color="transparent"); f_row.pack(fill="x", pady=2)
            ctk.CTkLabel(f_row, text=item["nombre"], font=("Roboto", 12)).pack(side="left")
            f_ctrl = ctk.CTkFrame(f_row, fg_color="transparent"); f_ctrl.pack(side="right")
            ctk.CTkButton(f_ctrl, text="-", width=30, fg_color="#374151", command=lambda i=item["nombre"]: actualizar_cantidad(i, -1)).pack(side="left", padx=5)
            lbl_num = ctk.CTkLabel(f_ctrl, text="0", font=("Roboto", 14, "bold"), width=20); lbl_num.pack(side="left")
            labels_cantidades[item["nombre"]] = lbl_num
            ctk.CTkButton(f_ctrl, text="+", width=30, fg_color="#374151", command=lambda i=item["nombre"]: actualizar_cantidad(i, 1)).pack(side="left", padx=5)

        def procesar_alimentacion():
            if all(cant == 0 for cant in seleccion_actual.values()):
                return messagebox.showwarning("Atención", "No has seleccionado alimento.")
            exito, msj = Inventario.descontar_inventario(seleccion_actual)
            if exito: 
                messagebox.showinfo("Éxito", msj)
                vista_alimentacion()
            else: messagebox.showwarning("Error", msj)

        ctk.CTkButton(f_dieta, text="Confirmar y Dar de Comer", fg_color=COLOR_ACENTO, height=45, 
                       font=("Roboto", 14, "bold"), command=procesar_alimentacion).pack(side="bottom", fill="x", pady=20, padx=20)

        f_stock = ctk.CTkFrame(f_split)
        f_stock.pack(side="right", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(f_stock, text="Inventario en Bodega", font=("Roboto", 18, "bold"), text_color="#f59e0b").pack(pady=15)
        
        datos = cargar_datos() # Refrescar por si se acaba de descontar
        for item in datos.get("inventario", []):
            f_item = ctk.CTkFrame(f_stock, fg_color="transparent"); f_item.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(f_item, text=item["nombre"], font=("Roboto", 13)).pack(side="left")
            color_cant = "#ef4444" if item["cantidad"] <= 5 else "white"
            ctk.CTkLabel(f_item, text=str(item["cantidad"]), font=("Roboto", 14, "bold"), text_color=color_cant).pack(side="right")

    def ir_registrar():
        estado["sub_vista"] = "agendar"
        vista_registrar()

    def ir_historial():
        estado["sub_vista"] = "historial"
        vista_historial()

    def ir_alimentacion():
        estado["sub_vista"] = "alimentacion"
        vista_alimentacion()

    ctk.CTkButton(frame_botones, text="➕ AGENDAR TRATAMIENTO", fg_color="black", hover_color="#334155", 
                   font=("Roboto", 13, "bold"), height=40, command=ir_registrar).pack(side="left", expand=True, padx=10)
    ctk.CTkButton(frame_botones, text="📜 VER HISTORIAL", fg_color="black", hover_color="#334155", 
                   font=("Roboto", 13, "bold"), height=40, command=ir_historial).pack(side="left", expand=True, padx=10)
    ctk.CTkButton(frame_botones, text="🍎 ALIMENTACIÓN", fg_color="black", hover_color="#334155", 
                   font=("Roboto", 13, "bold"), height=40, command=ir_alimentacion).pack(side="left", expand=True, padx=10)

    if datos_bd["equinos"]: seleccionar_equino(datos_bd["equinos"][0]["id_equino"])

def mostrar_calendario_medico(equino_dict, on_refresh=None):
    """
    Abre una ventana flotante con el calendario médico del equino.
    
    Args:
        equino_dict (dict): Datos del equino.
        on_refresh (function, optional): Callback para actualizar la vista principal.
    """
    top = ctk.CTkToplevel()
    top.title(f"Agenda Médica - {equino_dict['nombre']}")
    top.geometry("750x850") 
    top.attributes("-topmost", True)

    ahora = datetime.date.today(); vista_actual = [ahora.year, ahora.month] 
    
    # Navigation Header (Matching Training Style)
    frame_nav = ctk.CTkFrame(top, fg_color="transparent")
    frame_nav.pack(pady=20, fill="x")
    
    lbl_mes_anio = ctk.CTkLabel(frame_nav, text="", font=("Roboto", 24, "bold"), text_color=COLOR_ACENTO) 
    
    def cambiar_mes(delta):
        nuevo_mes = vista_actual[1] + delta
        if nuevo_mes > 12: vista_actual[1] = 1; vista_actual[0] += 1
        elif nuevo_mes < 1: vista_actual[1] = 12; vista_actual[0] -= 1
        else: vista_actual[1] = nuevo_mes
        refrescar_calendario()

    ctk.CTkButton(frame_nav, text="◀", width=50, command=lambda: cambiar_mes(-1)).pack(side="left", padx=50)
    lbl_mes_anio.pack(side="left", expand=True)
    ctk.CTkButton(frame_nav, text="▶", width=50, command=lambda: cambiar_mes(1)).pack(side="right", padx=50)

    frame_cal = ctk.CTkFrame(top, fg_color="transparent")
    frame_cal.pack(pady=10, padx=20, fill="both", expand=True)

    def refrescar_calendario():
        limpiar_contenedor(frame_cal)
        anio, mes = vista_actual
        meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        lbl_mes_anio.configure(text=f"{meses[mes]} {anio}")

        # Day Headers
        for i, d in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]):
            ctk.CTkLabel(frame_cal, text=d, font=("Roboto", 12, "bold"), text_color="#9ca3af").grid(row=0, column=i, pady=5)

        # Get fresh data for the horse
        datos = cargar_datos()
        eq_data = next((e for e in datos["equinos"] if e["id_equino"] == equino_dict["id_equino"]), equino_dict)

        # Agenda (Future)
        fechas_futuras = {}
        for proc, f_str in eq_data.get("fechas_medicas", {}).items():
            try: 
                f_obj = datetime.datetime.strptime(f_str, "%d/%m/%Y").date()
                fechas_futuras[f_obj] = proc
            except: pass

        # History (Done)
        fechas_previas = set()
        for reg in eq_data.get("historial_medico", []):
            try: 
                f_obj = datetime.datetime.strptime(reg['fecha'], "%Y-%m-%d").date()
                fechas_previas.add(f_obj)
            except: pass

        ini_sem, cant_dias = calendar.monthrange(anio, mes)
        fila, col = 1, ini_sem
        
        for dia in range(1, cant_dias + 1):
            f_actual = datetime.date(anio, mes, dia)
            color, txt = "#1e293b", ""
            
            if f_actual in fechas_previas:
                color, txt = COLOR_ACENTO, "\n[REALIZADO]"
            elif f_actual in fechas_futuras:
                color, txt = "#f59e0b", f"\n[{fechas_futuras[f_actual]}]"
            elif f_actual == datetime.date.today():
                color = "#334155" # Highlight Today

            btn = ctk.CTkButton(frame_cal, text=f"{dia}{txt}", fg_color=color, height=85, 
                                font=("Roboto", 12, "bold"), border_width=1, border_color="#334155",
                                command=lambda d=dia: click_dia(d))
            btn.grid(row=fila, column=col, padx=2, pady=2, sticky="nsew")
            
            col += 1
            if col > 6: col = 0; fila += 1

        for i in range(1, 7): frame_cal.grid_rowconfigure(i, weight=1)
        for j in range(7): frame_cal.grid_columnconfigure(j, weight=1)

    def click_dia(dia):
        anio, mes = vista_actual
        f_sel = datetime.date(anio, mes, dia)
        f_str = f_sel.strftime("%d/%m/%Y")
        
        # Deshabilitar topmost temporalmente para que los diálogos salgan adelante
        top.attributes("-topmost", False)

        datos = cargar_datos()
        eq_data = next((e for e in datos["equinos"] if e["id_equino"] == equino_dict["id_equino"]), equino_dict)
        fechas = eq_data.get("fechas_medicas", {})
        
        proc_en_fecha = next((p for p, f in fechas.items() if f == f_str), None)
        
        if proc_en_fecha:
            # Opción de Reagendar o Poner al Corriente
            opcion = messagebox.askyesnocancel("Acción", f"Procedimiento: {proc_en_fecha}\n\n¿Deseas marcarlo como REALIZADO (Poner al Corriente)?\n(Selecciona 'No' para Reagendar)", icon='question', parent=top)
            
            if opcion is True: # Poner al corriente (Sí)
                def dual_refresh():
                    refrescar_calendario()
                    if on_refresh: on_refresh()
                
                # Pasamos f_str (la fecha del día clickeado en el calendario) como fecha de realización
                marcar_como_realizado(eq_data, proc_en_fecha, f_str, callback_refresh=dual_refresh, fecha_realizacion=f_str)
            elif opcion is False: # Reagendar (No)
                dialog = ctk.CTkInputDialog(text=f"Nueva fecha para '{proc_en_fecha}':\n(DD/MM/AAAA)", title="Mover Cita")
                nueva_f = dialog.get_input()
                if nueva_f:
                    try:
                        datetime.datetime.strptime(nueva_f, "%d/%m/%Y")
                        fechas[proc_en_fecha] = nueva_f
                        eq_temp = Equino(id_equino=eq_data["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
                        eq_temp.actualizar_salud_y_dieta(eq_data.get("historial_medico", []), fechas, eq_data.get("alimentacion", ""))
                        messagebox.showinfo("Éxito", f"'{proc_en_fecha}' movido al {nueva_f}", parent=top)
                        refrescar_calendario()
                    except: messagebox.showerror("Error", "Formato inválido.", parent=top)
        else:
            if messagebox.askyesno("Agendar", f"¿Deseas agendar un tratamiento para el {f_str}?", parent=top):
                dialog = ctk.CTkInputDialog(text="Nombre del procedimiento:", title="Nuevo Agendamiento")
                tipo = dialog.get_input()
                if tipo:
                    fechas[tipo] = f_str
                    eq_temp = Equino(id_equino=eq_data["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
                    eq_temp.actualizar_salud_y_dieta(eq_data.get("historial_medico", []), fechas, eq_data.get("alimentacion", ""))
                    refrescar_calendario()
        
        top.attributes("-topmost", True)

    refrescar_calendario()

# ========================================================================
# 5. MÓDULO DE EQUINOS (GESTIÓN INTEGRAL)
# ========================================================================

def vista_equinos(frame_contenido):
    """
    Controlador principal de la vista de Equinos. Gestiona la navegación interna
    entre búsqueda, creación y caballerizas mediante un panel lateral secundario.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor donde se renderizarán las sub-vistas.
    """
    limpiar_contenedor(frame_contenido)
    
    # Cabecera de sección
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Gestión Integral de Equinos", font=("Roboto", 28, "bold")).pack(side="left")

    # Contenedor de arquitectura Sidebar-Content
    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # Navegación interna (Sidebar secundaria)
    panel_nav = ctk.CTkFrame(frame_principal, width=200, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_nav.pack(side="left", fill="y", padx=(0, 20))
    
    # Frame de destino para el intercambio de sub-vistas
    f_sub_content = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    f_sub_content.pack(side="right", fill="both", expand=True)

    def select_tab(tab_name, func):
        """Gestiona el estado visual de los botones de navegación interna."""
        for btn in btns_nav.values():
            btn.configure(fg_color="transparent", text_color="white")
        btns_nav[tab_name].configure(fg_color=COLOR_ACENTO, text_color="white")
        func(f_sub_content)

    btns_nav = {}
    for txt, func in [
        ("🔍 BUSCAR Y EDITAR", sub_vista_equinos_buscar),
        ("➕ CREAR REGISTRO", sub_vista_equinos_crear),
        ("🏠 CABALLERIZAS", sub_vista_caballerizas)
    ]:
        btn = ctk.CTkButton(panel_nav, text=txt, fg_color="transparent", anchor="w", 
                            height=45, font=("Roboto", 13, "bold"),
                            command=lambda t=txt, f=func: select_tab(t, f))
        btn.pack(fill="x", padx=10, pady=5)
        btns_nav[txt] = btn

    # Inicialización por defecto en la vista de búsqueda
    select_tab("🔍 BUSCAR Y EDITAR", sub_vista_equinos_buscar)

# Variable de estado para la carga de imágenes en sesión
ruta_imagen_temporal = None 

def sub_vista_equinos_crear(frame_contenido):
    """
    Renderiza el formulario de alta para nuevos ejemplares. Incluye lógica 
    dinámica de sugerencia de IDs y filtrado de razas por especie.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor de la sub-vista.
    """
    limpiar_contenedor(frame_contenido)
    global ruta_imagen_temporal; ruta_imagen_temporal = None 

    panel_fields = ctk.CTkScrollableFrame(frame_contenido, fg_color="transparent", label_text="Registro de Nuevo Equino")
    panel_fields.pack(side="left", fill="both", expand=True, padx=20)

    # Carga de catálogos desde el backend
    datos = cargar_datos()
    lista_propietarios = [c["nom_completo"] for c in datos["clientes"]]
    if not lista_propietarios: lista_propietarios = ["Sin clientes registrados"]
    
    # Diccionario maestro de especies para consistencia taxonómica
    MAPA_RAZAS = {
        "Caballo": ["Cuarto de Milla", "Pura Sangre", "Árabe", "Apaloosa", "Criollo", "Frisón", "Lusitano", "Otra"],
        "Burro": ["Zamorano-Leonés", "Andaluz", "Mammoth", "Otro"],
        "Mula": ["Mula de Carga", "Mula de Silla", "Otra"],
        "Poni": ["Shetland", "Welsh", "Falabella", "Otro"],
        "Otro": ["Sin especificar"]
    }
    lista_especies = list(MAPA_RAZAS.keys())

    ctk.CTkLabel(panel_fields, text="INFORMACIÓN BÁSICA", font=("Roboto", 16, "bold"), text_color=COLOR_ACENTO).pack(pady=(10, 15), anchor="w")
    
    f_grid = ctk.CTkFrame(panel_fields, fg_color="transparent")
    f_grid.pack(fill="x", anchor="w")

    def add_form_row(parent, row, label, widget_type, values=None, placeholder=""):
        """Utilidad interna para generar filas de formulario alineadas."""
        ctk.CTkLabel(parent, text=label, font=("Roboto", 14, "bold")).grid(row=row, column=0, pady=(10, 0), padx=(0, 20), sticky="w")
        if widget_type == "entry":
            w = ctk.CTkEntry(parent, width=350, placeholder_text=placeholder)
        elif widget_type == "combo":
            w = ctk.CTkComboBox(parent, values=values, width=350)
        w.grid(row=row+1, column=0, pady=(2, 10), sticky="w")
        return w

    entry_name = add_form_row(f_grid, 0, "Nombre del Equino:", "entry")
    combo_owner = add_form_row(f_grid, 2, "Propietario:", "combo", values=lista_propietarios)
    
    combo_spec = add_form_row(f_grid, 4, "Especie:", "combo", values=lista_especies)
    combo_breed = add_form_row(f_grid, 6, "Raza:", "combo", values=MAPA_RAZAS["Caballo"])
    
    def actualizar_datos_especie(choice):
        """Sincroniza el catálogo de razas y el prefijo del ID de registro al cambiar la especie."""
        # 1. Actualización de razas (Filtrado dinámico)
        combo_breed.configure(values=MAPA_RAZAS.get(choice, ["Otro"]))
        combo_breed.set(MAPA_RAZAS.get(choice, ["Otro"])[0])
        
        # 2. Lógica de Negocio: Sugerir ID de Registro basado en conteo actual por especie
        prefijos = {"Caballo": "CAB", "Burro": "BUR", "Mula": "MUL", "Poni": "PON", "Otro": "REG"}
        pre = prefijos.get(choice, "REG")
        datos_f = cargar_datos()
        conteo = sum(1 for e in datos_f["equinos"] if e.get("especie") == choice)
        entry_reg_id.delete(0, 'end')
        entry_reg_id.insert(0, f"{pre}-{conteo+1:03d}")
    
    combo_spec.configure(command=actualizar_datos_especie)

    # Atributos morfológicos y de identificación
    combo_sex = add_form_row(f_grid, 8, "Sexo:", "combo", values=["Caballo", "Yegua", "Castrado"])
    entry_coat = add_form_row(f_grid, 10, "Pelaje / Color:", "entry", placeholder="Ej. Alazán, Zaino...")
    entry_dob = add_form_row(f_grid, 12, "Fecha Nacimiento / Edad:", "entry", placeholder="DD/MM/AAAA o Edad")
    entry_chip = add_form_row(f_grid, 14, "Microchip:", "entry", placeholder="Poner 'Ninguno' si no tiene")
    entry_reg_id = add_form_row(f_grid, 16, "ID de Registro:", "entry", placeholder="Identificador oficial")
    
    ctk.CTkFrame(panel_fields, height=2, fg_color="#334155").pack(fill="x", pady=20)
    ctk.CTkLabel(panel_fields, text="ASIGNACIÓN Y ESTADO", font=("Roboto", 16, "bold"), text_color="#3b82f6").pack(pady=(0, 15), anchor="w")
    
    f_grid2 = ctk.CTkFrame(panel_fields, fg_color="transparent")
    f_grid2.pack(fill="x", anchor="w")
    entry_stable = add_form_row(f_grid2, 0, "Caballeriza Asignada:", "entry", placeholder="Ej. C-14")
    
    check_lease = ctk.CTkCheckBox(panel_fields, text="Bajo Arrendamiento (Entrenamiento)", font=("Roboto", 13))
    check_lease.pack(pady=(15, 10), anchor="w")

    def guardar_registro():
        """Valida y persiste el nuevo registro en el backend."""
        global ruta_imagen_temporal
        nombre = entry_name.get().strip()
        if not nombre: return messagebox.showerror("Error", "El nombre es obligatorio.")
        
        datos = cargar_datos()
        nom_prop = combo_owner.get()
        id_cliente = next((c["id_cliente"] for c in datos["clientes"] if c["nom_completo"] == nom_prop), "CL-000")
        
        # Generación de ID interno secuencial
        nuevo_id = f"EQ-{len(datos['equinos'])+1:03d}"
        etapa = "Iniciación" if check_lease.get() else "Ninguna"
        ruta_final = procesar_imagen_equino(ruta_imagen_temporal, nombre) if ruta_imagen_temporal else None
        
        eq_temp = Equino(
            id_equino=nuevo_id, id_cliente=id_cliente, nombre=nombre, 
            raza=combo_breed.get(), cab_asignada=entry_stable.get(), 
            etapa_arrendamiento=etapa, ruta_imagen=ruta_final,
            sexo=combo_sex.get(), pelaje=entry_coat.get(), 
            nacimiento=entry_dob.get(), microchip=entry_chip.get(),
            especie=combo_spec.get(), id_registro=entry_reg_id.get(),
            descripcion_equino=caja_desc.get("1.0", "end").strip()
        )
        exito, mensaje = eq_temp.registrar_equino()
        
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            # Limpieza del formulario tras guardado exitoso
            entry_name.delete(0, 'end'); entry_stable.delete(0, 'end'); check_lease.deselect() 
            entry_coat.delete(0, 'end'); entry_dob.delete(0, 'end'); entry_chip.delete(0, 'end'); entry_reg_id.delete(0, 'end')
            caja_desc.delete("1.0", "end")
            cargar_imagen_a_label(lbl_image_placeholder); ruta_imagen_temporal = None
        else: messagebox.showerror("Error", mensaje)

    ctk.CTkButton(panel_fields, text="GUARDAR REGISTRO", fg_color=COLOR_ACENTO, hover_color="#059669", 
                   font=("Roboto", 14, "bold"), height=40, width=350, command=guardar_registro).pack(pady=30)

    # --- PANEL DERECHO: MULTIMEDIA Y NOTAS ---
    panel_image = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    panel_image.pack(side="right", fill="both", padx=20, expand=True)
    
    lbl_image_placeholder = ctk.CTkLabel(panel_image, text="", corner_radius=10, fg_color="#1f2937", width=300, height=300)
    lbl_image_placeholder.pack(pady=20, anchor="center")
    cargar_imagen_a_label(lbl_image_placeholder)

    ctk.CTkLabel(panel_image, text="Descripción del Equino:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10)
    caja_desc = ctk.CTkTextbox(panel_image, height=150, width=300, fg_color="#1e293b", border_width=1, border_color="#334155")
    caja_desc.pack(pady=(5, 10), padx=10, fill="both", expand=True)

    def subir_imagen_pc():
        """Abre el explorador de archivos para cargar una fotografía local."""
        global ruta_imagen_temporal
        file_path = filedialog.askopenfilename(title="Seleccionar foto", filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if file_path:
            pil_img = Image.open(file_path); pil_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(200, 200))
            lbl_image_placeholder.configure(image=ctk_img, text=""); lbl_image_placeholder.image = ctk_img
            ruta_imagen_temporal = file_path 

    ctk.CTkButton(panel_image, text="Subir fotografía (PC)", fg_color="grey", command=subir_imagen_pc).pack(pady=10)

def sub_vista_equinos_buscar(frame_contenido):
    """
    Módulo de búsqueda y consulta de perfiles. Permite la edición de datos
    y el acceso al calendario de entrenamiento.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor de la sub-vista.
    """
    limpiar_contenedor(frame_contenido)
    
    # Barra de búsqueda superior
    frame_search = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_search.pack(pady=10)
    
    entry_search = ctk.CTkEntry(frame_search, placeholder_text="Buscar por nombre", width=300)
    entry_search.pack(side="left", padx=10)
    
    panel_results = ctk.CTkFrame(frame_contenido, fg_color="transparent")

    def intentar_buscar():
        busqueda = entry_search.get().lower().strip()
        datos = cargar_datos()
        # Buscamos en la lista de diccionarios
        equino_dict = next((e for e in datos["equinos"] if e["nombre"].lower() == busqueda), None)
        
        limpiar_contenedor(panel_results)
        if equino_dict: 
            panel_results.pack(pady=20, padx=20, fill="both", expand=True)
            cargar_perfil(equino_dict)
        else: messagebox.showinfo("Búsqueda", "Equino no encontrado en la base de datos.")

    ctk.CTkButton(frame_search, text="Buscar", command=intentar_buscar).pack(side="left", padx=10)

    def cargar_perfil(equino_dict):
        panel_form = ctk.CTkFrame(panel_results, fg_color="transparent")
        panel_form.pack(side="left", fill="both", expand=True, padx=20)
        
        datos = cargar_datos()
        nombre_propietario = next((c["nom_completo"] for c in datos["clientes"] if c["id_cliente"] == equino_dict["id_cliente"]), "Desconocido")
        lista_propietarios = [c["nom_completo"] for c in datos["clientes"]]
        if not lista_propietarios: lista_propietarios = ["Sin clientes registrados"]
        
        MAPA_RAZAS = {
            "Caballo": ["Cuarto de Milla", "Pura Sangre", "Árabe", "Apaloosa", "Criollo", "Frisón", "Lusitano", "Otra"],
            "Burro": ["Zamorano-Leonés", "Andaluz", "Mammoth", "Otro"],
            "Mula": ["Mula de Carga", "Mula de Silla", "Otra"],
            "Poni": ["Shetland", "Welsh", "Falabella", "Otro"],
            "Otro": ["Sin especificar"]
        }
        lista_especies = list(MAPA_RAZAS.keys())

        vars_campos = {}
        
        # Frame interno para alineación tipo Formulario
        f_grid = ctk.CTkFrame(panel_form, fg_color="transparent")
        f_grid.pack(fill="x", pady=10)

        def add_profile_row(row, label_text, value, key, widget_type="entry", values=None):
            # Etiqueta en columna 0
            lbl = ctk.CTkLabel(f_grid, text=label_text, font=("Roboto", 14, "bold"), width=120, anchor="w")
            lbl.grid(row=row, column=0, padx=(0, 20), pady=12, sticky="w")
            
            # Control en columna 1
            if widget_type == "entry":
                w = ctk.CTkEntry(f_grid, width=300)
                w.insert(0, value)
                w.configure(state="readonly")
            elif widget_type == "combo":
                w = ctk.CTkComboBox(f_grid, values=values, width=300)
                w.set(value)
                w.configure(state="disabled")
            
            w.grid(row=row, column=1, pady=12, sticky="w")
            vars_campos[key] = w

        # Agregamos las filas
        add_profile_row(0, "Nombre:", equino_dict["nombre"], 'nombre')
        add_profile_row(1, "Propietario:", nombre_propietario, 'propietario', "combo", lista_propietarios)
        add_profile_row(2, "Especie:", equino_dict.get("especie", "Caballo"), 'especie', "combo", lista_especies)
        
        # Obtener razas según la especie actual
        especie_actual = equino_dict.get("especie", "Caballo")
        razas_compatibles = MAPA_RAZAS.get(especie_actual, ["Otro"])
        add_profile_row(3, "Raza:", equino_dict["raza"], 'raza', "combo", razas_compatibles)
        
        def actualizar_razas_buscar(choice):
            vars_campos['raza'].configure(values=MAPA_RAZAS.get(choice, ["Otro"]))
            vars_campos['raza'].set(MAPA_RAZAS.get(choice, ["Otro"])[0])
        
        vars_campos['especie'].configure(command=actualizar_razas_buscar)

        add_profile_row(4, "Sexo:", equino_dict.get("sexo", "Caballo"), 'sexo', "combo", ["Caballo", "Yegua", "Castrado"])
        add_profile_row(5, "Pelaje:", equino_dict.get("pelaje", ""), 'pelaje')
        add_profile_row(6, "Nacimiento:", equino_dict.get("nacimiento", ""), 'nacimiento')
        add_profile_row(7, "Microchip:", equino_dict.get("microchip", ""), 'microchip')
        add_profile_row(8, "ID Registro:", equino_dict.get("id_registro", ""), 'id_registro')
        add_profile_row(9, "Caballeriza:", equino_dict["cab_asig"], 'caballeriza')
        
        es_arrendado = equino_dict["etapa"] != "Ninguna"
        ctk.CTkLabel(panel_form, text=f"Bajo Arrendamiento: {'Sí' if es_arrendado else 'No'}", font=("Roboto", 14, "bold"), text_color=COLOR_ACENTO).pack(pady=10, anchor="w")

        frame_btns = ctk.CTkFrame(panel_form, fg_color="transparent"); frame_btns.pack(pady=10, anchor="w")
        btn_edit = ctk.CTkButton(frame_btns, text="Editar Perfil", width=120, fg_color="#3b82f6"); btn_edit.pack(side="left", padx=5)
        
        btn_calendar = ctk.CTkButton(frame_btns, text="Calendario Entrenamiento", width=180, fg_color="#3b82f6", 
                                     state="normal" if es_arrendado else "disabled",
                                     command=lambda: mostrar_arrendamiento_progreso(equino_dict))
        btn_calendar.pack(side="left", padx=5)

        def toggle_edicion():
            if btn_edit.cget("text") == "Editar Perfil": 
                vars_campos['propietario'].configure(state="normal")
                vars_campos['especie'].configure(state="normal")
                vars_campos['raza'].configure(state="normal")
                vars_campos['sexo'].configure(state="normal")
                vars_campos['pelaje'].configure(state="normal")
                vars_campos['nacimiento'].configure(state="normal")
                vars_campos['microchip'].configure(state="normal")
                vars_campos['id_registro'].configure(state="normal")
                vars_campos['caballeriza'].configure(state="normal")
                caja_desc_ficha.configure(state="normal")
                btn_edit.configure(text="Guardar Cambios", fg_color=COLOR_ACENTO)
            else:
                # Obtener nuevos datos
                nueva_raza = vars_campos['raza'].get()
                nueva_cab = vars_campos['caballeriza'].get()
                nuevo_propietario_nom = vars_campos['propietario'].get()
                
                # Buscar ID del nuevo propietario
                datos_frescos = cargar_datos()
                id_nuevo_cliente = next((c["id_cliente"] for c in datos_frescos["clientes"] if c["nom_completo"] == nuevo_propietario_nom), equino_dict["id_cliente"])

                # Usar la clase Equino del backend con todos los campos
                eq_temp = Equino(
                    id_equino=equino_dict["id_equino"], id_cliente=equino_dict["id_cliente"], 
                    nombre=equino_dict["nombre"], raza=equino_dict["raza"], 
                    cab_asignada=equino_dict["cab_asig"], etapa_arrendamiento=equino_dict["etapa"],
                    sexo=vars_campos['sexo'].get(), pelaje=vars_campos['pelaje'].get(),
                    nacimiento=vars_campos['nacimiento'].get(), microchip=vars_campos['microchip'].get(),
                    especie=vars_campos['especie'].get(), id_registro=vars_campos['id_registro'].get(),
                    descripcion_equino=caja_desc_ficha.get("0.0", "end").strip()
                )
                exito, msj = eq_temp.actualizar_perfil(nueva_raza, nueva_cab, nuevo_id_cliente=id_nuevo_cliente, 
                                                     sexo=vars_campos['sexo'].get(), pelaje=vars_campos['pelaje'].get(),
                                                     nacimiento=vars_campos['nacimiento'].get(), microchip=vars_campos['microchip'].get(),
                                                     especie=vars_campos['especie'].get(), id_registro=vars_campos['id_registro'].get(),
                                                     descripcion_equino=caja_desc_ficha.get("0.0", "end").strip())
                
                if exito:
                    messagebox.showinfo("Éxito", msj)
                    # Actualizar objeto en memoria para la vista actual
                    equino_dict["raza"] = nueva_raza
                    equino_dict["cab_asig"] = nueva_cab
                    equino_dict["id_cliente"] = id_nuevo_cliente
                    
                    # Volver a modo lectura
                    vars_campos['propietario'].configure(state="disabled")
                    vars_campos['especie'].configure(state="disabled")
                    vars_campos['raza'].configure(state="disabled")
                    vars_campos['sexo'].configure(state="disabled")
                    vars_campos['pelaje'].configure(state="readonly")
                    vars_campos['nacimiento'].configure(state="readonly")
                    vars_campos['microchip'].configure(state="readonly")
                    vars_campos['id_registro'].configure(state="readonly")
                    vars_campos['caballeriza'].configure(state="readonly")
                    caja_desc_ficha.configure(state="disabled")
                    btn_edit.configure(text="Editar Perfil", fg_color="#3b82f6")
                    
                    # Sincronizar en memoria local
                    equino_dict["descripcion_equino"] = eq_temp.descripcion_equino
                    equino_dict["especie"] = eq_temp.especie
                    equino_dict["id_registro"] = eq_temp.id_registro
                else: 
                    messagebox.showerror("Error", msj)

        btn_edit.configure(command=toggle_edicion)

        # --- PANEL DE IMAGEN Y CAMBIO DE FOTO ---
        panel_image = ctk.CTkFrame(panel_results, fg_color="transparent")
        panel_image.pack(side="right", fill="both", padx=20, expand=True)
        
        lbl_img = ctk.CTkLabel(panel_image, text="", corner_radius=10, fg_color="#1f2937")
        lbl_img.pack(pady=10, anchor="center")
        
        # Carga de imagen con tamaño dinámico proporcional (ancho 300)
        def cargar_foto_proporcional(lbl, ruta):
            try:
                if ruta and os.path.exists(ruta):
                    pil_img = Image.open(ruta)
                    ancho = 300
                    alto = int(ancho * (pil_img.height / pil_img.width))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ancho, alto))
                    lbl.configure(image=ctk_img, text="")
                    lbl.image = ctk_img
                else:
                    lbl.configure(text="Sin Imagen", width=300, height=200)
            except:
                lbl.configure(text="Error Imagen")

        cargar_foto_proporcional(lbl_img, equino_dict.get("ruta_imagen"))

        ctk.CTkLabel(panel_image, text="Descripción / Notas:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10)
        caja_desc_ficha = ctk.CTkTextbox(panel_image, height=150, width=320, fg_color="#1e293b", border_width=1, border_color="#334155")
        caja_desc_ficha.pack(pady=(5, 5), padx=10, fill="both", expand=True)
        caja_desc_ficha.insert("1.0", equino_dict.get("descripcion_equino", ""))
        
        def guardar_nota_rapida():
            nueva_nota = caja_desc_ficha.get("1.0", "end").strip()
            eq_temp = Equino(id_equino=equino_dict["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
            exito, msj = eq_temp.actualizar_perfil(equino_dict["raza"], equino_dict["cab_asig"], descripcion_equino=nueva_nota)
            if exito:
                messagebox.showinfo("Éxito", "Nota del equino guardada.")
                equino_dict["descripcion_equino"] = nueva_nota
            else:
                messagebox.showerror("Error", msj)

        ctk.CTkButton(panel_image, text="💾 Guardar Nota", fg_color="#10b981", height=28, width=120, command=guardar_nota_rapida).pack(pady=(0, 10), anchor="e", padx=10)

        def cambiar_foto_desde_ficha():
            # 1. Seleccionar el nuevo archivo
            ruta_origen = filedialog.askopenfilename(title="Seleccionar nueva foto", filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
            
            if ruta_origen:
                # 2. Procesar, redimensionar y copiar a la carpeta del sistema
                ruta_final = procesar_imagen_equino(ruta_origen, equino_dict["nombre"])
                
                if ruta_final:
                    # 3. Guardar el cambio en el archivo JSON mediante el backend
                    eq_temp = Equino(id_equino=equino_dict["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
                    exito, msj = eq_temp.actualizar_imagen(ruta_final)
                    
                    if exito:
                        # 4. Actualizar la vista en tiempo real
                        equino_dict["ruta_imagen"] = ruta_final 
                        cargar_imagen_a_label(lbl_img, ruta_final)
                        messagebox.showinfo("Éxito", "La fotografía del equino ha sido actualizada.")
                    else:
                        messagebox.showerror("Error", msj)

        # Botón para cambiar la fotografía directamente en la ficha
        ctk.CTkButton(panel_image, text="Actualizar Foto", fg_color="grey", hover_color="#374151", 
                      command=cambiar_foto_desde_ficha).pack(pady=10)
        
        
        
def mostrar_arrendamiento_progreso(equino_dict):
    top = ctk.CTkToplevel()
    top.title(f"Control Entrenamiento - {equino_dict['nombre']}")
    top.geometry("700x850") 
    top.attributes("-topmost", True) # Asegurar que esté enfrente

    f_progreso = ctk.CTkFrame(top, fg_color="#1f2937", corner_radius=10)
    f_progreso.pack(pady=20, padx=20, fill="x", ipady=10)

    ctk.CTkLabel(f_progreso, text="Nivel de Adiestramiento Actual", font=("Roboto", 16, "bold")).pack(pady=(10, 5))
    
    f_stepper = ctk.CTkFrame(f_progreso, fg_color="transparent")
    f_stepper.pack(pady=10)

    etapas = ["Iniciación", "Intermedio", "Avanzado", "Terminado"]
    botones_etapa = {}

    def cambiar_etapa(nueva_etapa):
        if messagebox.askyesno("Confirmar Promoción", f"¿Promover a {equino_dict['nombre']} a la etapa: {nueva_etapa}?"):
            # Usamos la función que tu compañera ya tenía lista en el backend
            eq_temp = Equino(id_equino=equino_dict["id_equino"], id_cliente="", nombre="", raza="", cab_asignada="", etapa_arrendamiento="")
            exito, msj = eq_temp.modificar_etapa(nueva_etapa)
            
            if exito:
                equino_dict["etapa"] = nueva_etapa # Sincronizamos en la memoria visual
                pintar_stepper()
                messagebox.showinfo("Éxito", msj)
            else:
                messagebox.showerror("Error", msj)

    def pintar_stepper():
        etapa_actual = equino_dict.get("etapa", "Iniciación")
        encontrado_actual = False
        
        for et in etapas:
            if et == etapa_actual:
                # Etapa Actual (Verde brillante)
                botones_etapa[et].configure(fg_color=COLOR_ACENTO, text_color="white", hover_color="#059669")
                encontrado_actual = True
            elif not encontrado_actual:
                # Etapas ya superadas (Verde oscuro / apagado)
                botones_etapa[et].configure(fg_color="#064e3b", text_color="#9ca3af", hover_color="#064e3b") 
            else:
                # Etapas futuras (Gris oscuro)
                botones_etapa[et].configure(fg_color="#374151", text_color="gray", hover_color="#4b5563")

    for et in etapas:
        btn = ctk.CTkButton(f_stepper, text=et, width=130, height=35, font=("Roboto", 14, "bold"),
                            command=lambda e=et: cambiar_etapa(e))
        btn.pack(side="left", padx=5)
        botones_etapa[et] = btn

    pintar_stepper() # Pintamos los colores correctos al abrir la ventana
    # =========================================================

    # --- CALENDARIO DE ASISTENCIA ---
    ahora = datetime.date.today(); vista_actual = [ahora.year, ahora.month] 
    frame_nav = ctk.CTkFrame(top, fg_color="transparent"); frame_nav.pack(pady=10, fill="x")
    lbl_mes_anio = ctk.CTkLabel(frame_nav, text="", font=("Roboto", 24, "bold"), text_color=COLOR_ACENTO)
    
    def cambiar_mes(delta):
        nuevo_mes = vista_actual[1] + delta
        if nuevo_mes > 12: vista_actual[1] = 1; vista_actual[0] += 1
        elif nuevo_mes < 1: vista_actual[1] = 12; vista_actual[0] -= 1
        else: vista_actual[1] = nuevo_mes
        refrescar_calendario()

    ctk.CTkButton(frame_nav, text="◀", width=50, command=lambda: cambiar_mes(-1)).pack(side="left", padx=50)
    lbl_mes_anio.pack(side="left", expand=True)
    ctk.CTkButton(frame_nav, text="▶", width=50, command=lambda: cambiar_mes(1)).pack(side="right", padx=50)

    frame_cal = ctk.CTkFrame(top, fg_color="transparent"); frame_cal.pack(pady=10, padx=20, fill="both", expand=True)

    def refrescar_calendario():
        limpiar_contenedor(frame_cal)
        anio, mes = vista_actual
        meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        lbl_mes_anio.configure(text=f"{meses[mes]} {anio}")

        for i, d in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]):
            ctk.CTkLabel(frame_cal, text=d, font=("Roboto", 12, "bold")).grid(row=0, column=i, pady=5)

        # Convertir strings del JSON a objetos de fecha
        dias_trabajados_set = set()
        for d_str in equino_dict.get("dias_trabajados", []):
            try: dias_trabajados_set.add(datetime.datetime.strptime(d_str, "%Y-%m-%d").date())
            except: pass

        proxima = max(dias_trabajados_set) + datetime.timedelta(days=2) if dias_trabajados_set else None
        ini_sem, cant_dias = calendar.monthrange(anio, mes)
        fila, col = 1, ini_sem
        
        for dia in range(1, cant_dias + 1):
            f_actual = datetime.date(anio, mes, dia); color, txt = "gray", ""
            if f_actual in dias_trabajados_set: color, txt = COLOR_ACENTO, "\n[TRABAJADO]"
            elif f_actual == proxima: color, txt = COLOR_PROXIMA, "\n[SESIÓN]"

            btn = ctk.CTkButton(frame_cal, text=f"{dia}{txt}", fg_color=color, height=80, command=lambda d=f_actual: toggle_dia(d))
            btn.grid(row=fila, column=col, padx=2, pady=2, sticky="nsew")
            col += 1
            if col > 6: col = 0; fila += 1

        for i in range(1, 7): frame_cal.grid_rowconfigure(i, weight=1)
        for j in range(7): frame_cal.grid_columnconfigure(j, weight=1)

    def toggle_dia(dia_obj):
        dia_str = dia_obj.strftime("%Y-%m-%d")
        datos = cargar_datos()
        
        for e in datos["equinos"]:
            if e["id_equino"] == equino_dict["id_equino"]:
                if "dias_trabajados" not in e: e["dias_trabajados"] = []
                
                if dia_str in e["dias_trabajados"]: e["dias_trabajados"].remove(dia_str)
                else: e["dias_trabajados"].append(dia_str)
                
                guardar_datos(datos)
                equino_dict["dias_trabajados"] = e["dias_trabajados"] # Sincronizar diccionario visual
                break
                
        refrescar_calendario()

    refrescar_calendario()

def sub_vista_caballerizas(frame_contenido):
    """
    Gestiona el mapa visual de ocupación de las caballerizas (boxes).
    Permite el movimiento dinámico de animales y la redimensión física del mapa.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor de la sub-vista.
    """
    limpiar_contenedor(frame_contenido)
    
    # --- Controles de Redimensionamiento Administrativo ---
    f_controles = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_controles.pack(pady=10, fill="x", padx=20)
    
    ctk.CTkLabel(f_controles, text="Dimensiones del Mapa:", font=("Roboto", 14, "bold")).pack(side="left", padx=(0, 10))
    
    def modificar_mapa(accion):
        """Llama al backend para alterar las dimensiones de la matriz de caballerizas."""
        exito, msj = Caballeriza.modificar_dimensiones(accion)
        if exito: 
            create_grid_visual()
        else: 
            messagebox.showwarning("Atención", msj)

    ctk.CTkButton(f_controles, text="+ Fila", width=70, command=lambda: modificar_mapa("agregar_fila")).pack(side="left", padx=5)
    ctk.CTkButton(f_controles, text="- Fila", width=70, fg_color="#ef4444", hover_color="#b91c1c", command=lambda: modificar_mapa("quitar_fila")).pack(side="left", padx=5)
    ctk.CTkButton(f_controles, text="+ Columna", width=80, command=lambda: modificar_mapa("agregar_col")).pack(side="left", padx=5)
    ctk.CTkButton(f_controles, text="- Columna", width=80, fg_color="#ef4444", hover_color="#b91c1c", command=lambda: modificar_mapa("quitar_col")).pack(side="left", padx=5)

    # --- Contenedor del Mapa (Grid Dinámico) ---
    frame_grid_container = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_grid_container.pack(pady=10, padx=20, fill="both", expand=True)

    def create_grid_visual():
        """
        Genera dinámicamente la cuadrícula de botones basada en el estado real 
        de ocupación guardado en el JSON.
        """
        limpiar_contenedor(frame_grid_container)
        datos = cargar_datos()
        grid_data = datos["mapa_caballerizas"]
        
        filas = len(grid_data)
        columnas = len(grid_data[0]) if filas > 0 else 0
        
        for i in range(filas):
            for j in range(columnas):
                stable_id = f"C-{i+1}{j+1}"
                occupied = grid_data[i][j]
                texto_boton = f"{stable_id}\n(Libre)"
                id_eq = None 

                # Si está ocupada, buscamos el nombre del inquilino actual
                if occupied:
                    nombre_caballo = "Desconocido"
                    for eq in datos["equinos"]:
                        if eq.get("cab_asig") == stable_id:
                            nombre_caballo = eq["nombre"]
                            id_eq = eq["id_equino"] 
                            break
                    texto_boton = f"{stable_id}\n{nombre_caballo}"

                # Creación del botón interactivo por box
                btn = ctk.CTkButton(frame_grid_container, text=texto_boton)
                btn.configure(fg_color="#ef4444" if occupied else "#10b981", text_color="white")
                btn.configure(command=lambda b=stable_id, o=occupied, eid=id_eq: define_click(b, o, eid))
                btn.grid(row=i, column=j, padx=5, pady=5, sticky="nsew")
                
        # Asegura que el grid se expanda uniformemente
        for i in range(filas): frame_grid_container.grid_rowconfigure(i, weight=1)
        for j in range(columnas): frame_grid_container.grid_columnconfigure(j, weight=1)

    def define_click(b_id, occ, eid):
        """Gestiona la lógica de clic: Liberar si está ocupado o Asignar si está libre."""
        if occ:
            if messagebox.askyesno("Opciones", f"La caballeriza {b_id} está ocupada.\n\n¿Deseas LIBERARLA?"):
                eq_temp = Equino(id_equino=eid, id_cliente="", nombre="", raza="", cab_asignada=b_id, etapa_arrendamiento="")
                exito, msj = eq_temp.liberar_caballeriza()
                if exito: create_grid_visual()
                else: messagebox.showerror("Error", msj)
        else:
            asignar_caballo_a_caballeriza(b_id)
            
    def asignar_caballo_a_caballeriza(nueva_cab):
        """
        Abre un diálogo modal para seleccionar qué caballo trasladar a 
        la caballeriza seleccionada.
        """
        datos = cargar_datos()
        lista_caballos = [f"{eq['nombre']} (ID: {eq['id_equino']})" for eq in datos["equinos"]]
        
        if not lista_caballos:
            return messagebox.showinfo("Sin caballos", "No hay caballos registrados en el sistema.")
        
        top = ctk.CTkToplevel()
        top.title(f"Mover Caballo")
        top.geometry("400x250")
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text=f"Mover un caballo a {nueva_cab}", font=("Roboto", 18, "bold")).pack(pady=20)
        combo_caballos = ctk.CTkComboBox(top, values=lista_caballos, width=300)
        combo_caballos.pack(pady=10)
        
        def confirmar_movimiento():
            seleccion = combo_caballos.get()
            if not seleccion: return
            try:
                # Extracción del ID del formato descriptivo para el backend
                eid = seleccion.split("ID: ")[1].replace(")", "")
                datos_frescos = cargar_datos()
                caballo_real = next((e for e in datos_frescos["equinos"] if e["id_equino"] == eid), None)
                
                if not caballo_real: return
                
                eq_temp = Equino(
                    id_equino=caballo_real["id_equino"], 
                    id_cliente=caballo_real["id_cliente"], 
                    nombre=caballo_real["nombre"], 
                    raza=caballo_real["raza"], 
                    cab_asignada=caballo_real["cab_asig"], 
                    etapa_arrendamiento=caballo_real["etapa"]
                )
                
                exito, msj = eq_temp.actualizar_ubicacion(nueva_cab)
                if exito:
                    messagebox.showinfo("Éxito", msj)
                    create_grid_visual()
                    top.destroy()
                else:
                    messagebox.showerror("Error", msj)
                    top.attributes("-topmost", True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo procesar: {e}")

        ctk.CTkButton(top, text="Confirmar Traslado", fg_color=COLOR_ACENTO, hover_color="#059669", command=confirmar_movimiento).pack(pady=20)

    create_grid_visual()

# ========================================================================
# 6. DIRECTORIO DE CLIENTES (GESTIÓN DE PROPIETARIOS)
# ========================================================================

def vista_clientes(frame_contenido):
    """
    Controlador de la vista de Directorio. Permite gestionar el catálogo de 
    propietarios y sus términos de pensión.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal.
    """
    limpiar_contenedor(frame_contenido)
    
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Directorio de Clientes", font=("Roboto", 28, "bold")).pack(side="left")
    
    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # --- PANEL IZQUIERDO: Directorio Listado ---
    panel_izq = ctk.CTkFrame(frame_principal, width=280, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_izq.pack(side="left", fill="y", padx=(0, 20))
    
    ctk.CTkLabel(panel_izq, text="CLIENTES REGISTRADOS", font=("Roboto", 13, "bold"), text_color="#9ca3af").pack(pady=(20, 10))
    
    lista_scroll = ctk.CTkScrollableFrame(panel_izq, fg_color="transparent")
    lista_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    # --- PANEL DERECHO: Detalles y Edición ---
    panel_der = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_der.pack(side="right", fill="both", expand=True)
    
    # --- FOOTER CON BOTONES DE ACCIÓN (Se empaca primero al fondo) ---
    f_botones = ctk.CTkFrame(panel_der, fg_color="transparent")
    f_botones.pack(side="bottom", fill="x", pady=20, padx=30)

    # --- DISTRIBUCIÓN EN COLUMNAS (SIDE-BY-SIDE) ---
    f_split_container = ctk.CTkFrame(panel_der, fg_color="transparent")
    f_split_container.pack(fill="both", expand=True, padx=30, pady=10)
    
    # COLUMNA DERECHA: Panel CRM (Se empaca a la derecha primero)
    f_col_der_crm = ctk.CTkFrame(f_split_container, fg_color="#111827", corner_radius=15, border_width=1, border_color="#334155", width=340)
    f_col_der_crm.pack(side="right", fill="y", padx=(10, 0))
    f_col_der_crm.pack_propagate(False) # Mantener ancho fijo para el CRM

    ctk.CTkLabel(f_col_der_crm, text="RESUMEN DEL CLIENTE", font=("Roboto", 13, "bold"), text_color=COLOR_ACENTO).pack(pady=(20, 10))
    
    # Métricas Financieras
    f_fin = ctk.CTkFrame(f_col_der_crm, fg_color="transparent")
    f_fin.pack(fill="x", padx=20)
    
    lbl_total_pagado = ctk.CTkLabel(f_fin, text="$0.00", font=("Roboto", 24, "bold"), text_color=COLOR_ACENTO)
    lbl_total_pagado.pack()
    ctk.CTkLabel(f_fin, text="Total Pagado", font=("Roboto", 10), text_color="#9ca3af").pack(pady=(0, 10))
    
    lbl_adeudo = ctk.CTkLabel(f_fin, text="$0.00", font=("Roboto", 24, "bold"), text_color="#ef4444")
    lbl_adeudo.pack()
    ctk.CTkLabel(f_fin, text="Adeudo Pendiente", font=("Roboto", 10), text_color="#9ca3af").pack(pady=(0, 15))

    ctk.CTkFrame(f_col_der_crm, height=1, fg_color="#334155").pack(fill="x", padx=20, pady=10)
    
    ctk.CTkLabel(f_col_der_crm, text="🐴 CABALLOS ASOCIADOS", font=("Roboto", 12, "bold"), text_color="white").pack(anchor="w", padx=20)
    lbl_caballos = ctk.CTkLabel(f_col_der_crm, text="Ninguno", font=("Roboto", 13, "italic"), text_color="#3b82f6", justify="left", wraplength=300)
    lbl_caballos.pack(anchor="w", pady=(2, 10), padx=20)
    
    ctk.CTkLabel(f_col_der_crm, text="📝 NOTAS / SEGUIMIENTO CRM", font=("Roboto", 12, "bold"), text_color="white").pack(anchor="w", padx=20)
    txt_notas = ctk.CTkTextbox(f_col_der_crm, height=180, corner_radius=10, border_width=1, border_color="#334155", fg_color="#0f172a", font=("Roboto", 12))
    txt_notas.pack(fill="both", expand=True, pady=10, padx=20)

    # COLUMNA IZQUIERDA: Formulario de Datos (Toma el resto del espacio)
    f_col_izq = ctk.CTkFrame(f_split_container, fg_color="transparent")
    f_col_izq.pack(side="left", fill="both", expand=True, padx=(0, 20))
    
    ctk.CTkLabel(f_col_izq, text="PERFIL DEL CLIENTE", font=("Roboto", 16, "bold"), text_color=COLOR_ACENTO).pack(pady=(0, 10), anchor="w")
    
    f_formulario = ctk.CTkFrame(f_col_izq, fg_color="transparent")
    f_formulario.pack(fill="x", pady=5)
    
    def crear_campo(parent, row, label, placeholder=""):
        ctk.CTkLabel(parent, text=label, font=("Roboto", 14, "bold")).grid(row=row, column=0, pady=(10, 0), padx=(0, 20), sticky="w")
        entry = ctk.CTkEntry(parent, width=400, height=35, placeholder_text=placeholder, corner_radius=8)
        entry.grid(row=row+1, column=0, pady=(5, 10), sticky="w")
        return entry

    e_nombre = crear_campo(f_formulario, 0, "Nombre Completo:", "Ej. Juan Pérez")
    e_contacto = crear_campo(f_formulario, 2, "Información de Contacto:", "Teléfono, Email o Dirección")
    
    ctk.CTkFrame(f_col_izq, height=1, fg_color="#334155").pack(fill="x", pady=15)
    ctk.CTkLabel(f_col_izq, text="CONDICIONES COMERCIALES", font=("Roboto", 16, "bold"), text_color="#3b82f6").pack(pady=(0, 10), anchor="w")
    
    f_form_2 = ctk.CTkFrame(f_col_izq, fg_color="transparent")
    f_form_2.pack(fill="x", pady=5)
    e_terminos = crear_campo(f_form_2, 0, "Términos de Pensión / Contrato:", "Ej. Pago mensual los días 05")

    # El estado ahora rastreará el ID real del cliente
    estado = {"cliente_actual_id": None}

    # --- LÓGICA DE INTERFAZ ---
    def cargar_lista():
        limpiar_contenedor(lista_scroll)
        datos = cargar_datos()
        for c in datos["clientes"]:
            btn = ctk.CTkButton(lista_scroll, text=c["nom_completo"], 
                                fg_color="transparent", text_color="white", anchor="w",
                                hover_color="#334155", height=35,
                                command=lambda cid=c["id_cliente"]: seleccionar_cliente(cid))
            btn.pack(pady=2, fill="x")

    def seleccionar_cliente(cid):
        estado["cliente_actual_id"] = cid
        datos = cargar_datos()
        cliente = next((c for c in datos["clientes"] if c["id_cliente"] == cid), None)
        if not cliente: return
        
        e_nombre.delete(0, 'end'); e_nombre.insert(0, cliente["nom_completo"])
        e_contacto.delete(0, 'end'); e_contacto.insert(0, cliente["contacto"])
        e_terminos.delete(0, 'end'); e_terminos.insert(0, cliente["term_pension"])
        
        # Cargar Notas CRM
        txt_notas.delete("1.0", "end")
        txt_notas.insert("1.0", cliente.get("notas", ""))
        
        # Cálculo Financiero Express
        finanzas = datos.get("finanzas", [])
        total_p = sum(p["monto"] for p in finanzas if p["id_cliente"] == cid and p["estado"] == "Pagado")
        total_a = sum(p["monto"] for p in finanzas if p["id_cliente"] == cid and p["estado"] == "Pendiente")
        
        lbl_total_pagado.configure(text=f"${total_p:,.2f}")
        lbl_adeudo.configure(text=f"${total_a:,.2f}")
        
        # Lista de Caballos Asociados
        mis_caballos = [eq["nombre"] for eq in datos.get("equinos", []) if eq["id_cliente"] == cid]
        if mis_caballos:
            lbl_caballos.configure(text=", ".join(mis_caballos), font=("Roboto", 13, "bold"))
        else:
            lbl_caballos.configure(text="Sin caballos registrados", font=("Roboto", 12, "italic"))

    def nuevo_cliente():
        estado["cliente_actual_id"] = None
        e_nombre.delete(0, 'end'); e_contacto.delete(0, 'end'); e_terminos.delete(0, 'end')
        txt_notas.delete("1.0", "end")
        lbl_total_pagado.configure(text="$0.00")
        lbl_adeudo.configure(text="$0.00")
        lbl_caballos.configure(text="Ninguno")
        e_nombre.focus()

    def guardar_actualizar():
        nombre = e_nombre.get().strip()
        if not nombre: return messagebox.showwarning("Atención", "El nombre es obligatorio.")

        cid = estado["cliente_actual_id"]
        
        if cid is None: # Si es un cliente nuevo
            datos = cargar_datos()
            nuevo_id = f"CL-{len(datos['clientes']) + 1:03d}"
            cli_temp = Cliente(id_cliente=nuevo_id, nom_completo=nombre, contacto=e_contacto.get(), term_pension=e_terminos.get(), notas=txt_notas.get("1.0", "end").strip())
            exito, msj = cli_temp.registrar_cliente()
            if exito: estado["cliente_actual_id"] = nuevo_id
        else: # Si estamos actualizando uno existente
            cli_temp = Cliente(id_cliente=cid, nom_completo=nombre, contacto=e_contacto.get(), term_pension=e_terminos.get(), notas=txt_notas.get("1.0", "end").strip())
            exito, msj = cli_temp.actualizar_cliente()

        cargar_lista()
        if exito: messagebox.showinfo("Éxito", msj)
        else: messagebox.showerror("Error", msj)

    def eliminar_cliente_ui():
        cid = estado["cliente_actual_id"]
        if not cid: return messagebox.showwarning("Atención", "Selecciona un cliente de la lista.")

        if messagebox.askyesno("Confirmar", f"¿Seguro que deseas eliminar este perfil?\nEsta acción no se puede deshacer."):
            cli_temp = Cliente("", "", "", "")
            exito, msj = cli_temp.eliminar_cliente(cid)
            if exito:
                nuevo_cliente()
                cargar_lista()
                messagebox.showinfo("Eliminado", msj)
            else: messagebox.showerror("Error", msj)

    def buscar_cliente():
        dialog = ctk.CTkInputDialog(text="Ingresa el nombre del cliente:", title="Buscar Cliente")
        busqueda = dialog.get_input()
        if busqueda:
            datos = cargar_datos()
            for c in datos["clientes"]:
                if busqueda.lower() in c["nom_completo"].lower():
                    seleccionar_cliente(c["id_cliente"])
                    return
            messagebox.showinfo("Búsqueda", "Cliente no encontrado.")

    def ver_caballos():
        cid = estado["cliente_actual_id"]
        if not cid: return messagebox.showwarning("Atención", "Selecciona un cliente de la lista.")
        
        datos = cargar_datos()
        caballos = [eq["nombre"] for eq in datos["equinos"] if eq["id_cliente"] == cid]
        
        if caballos:
            msj = f"Caballos asociados a {e_nombre.get()}:\n\n" + "\n".join(f"• {c}" for c in caballos)
            messagebox.showinfo("Caballos Asociados", msj)
        else:
            messagebox.showinfo("Caballos Asociados", "Este cliente no tiene caballos registrados en el sistema.")

    
    def crear_btn_accion(text, color, cmd, icon=""):
        return ctk.CTkButton(f_botones, text=text, fg_color=color, hover_color="#374151" if color=="black" else None, 
                              font=("Roboto", 13, "bold"), height=40, command=cmd)

    crear_btn_accion("🔍 BUSCAR", "black", buscar_cliente).pack(side="left", expand=True, padx=5)
    crear_btn_accion("➕ NUEVO", "black", nuevo_cliente).pack(side="left", expand=True, padx=5)
    crear_btn_accion("💾 GUARDAR", COLOR_ACENTO, guardar_actualizar).pack(side="left", expand=True, padx=5)
    crear_btn_accion("🐎 CABALLOS", "#3b82f6", ver_caballos).pack(side="left", expand=True, padx=5)
    crear_btn_accion("🗑️ ELIMINAR", "#ef4444", eliminar_cliente_ui).pack(side="left", expand=True, padx=5)

    # Cargar datos al iniciar
    cargar_lista()
    datos_iniciales = cargar_datos()
    if datos_iniciales["clientes"]:
        seleccionar_cliente(datos_iniciales["clientes"][0]["id_cliente"])
        
# ========================================================================
# 7. FINANZAS (GESTIÓN FINANCIERA Y COBRANZA)
# ========================================================================

def vista_finanzas(frame_contenido):
    """
    Controlador del módulo de Finanzas. Gestiona ingresos, adeudos y 
    reportes de estados de cuenta para clientes.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal.
    """
    limpiar_contenedor(frame_contenido)
    
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Gestión Financiera y Cobranza", font=("Roboto", 28, "bold")).pack(side="left")

    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # Sidebar: Navegación Financiera
    panel_nav = ctk.CTkFrame(frame_principal, width=200, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_nav.pack(side="left", fill="y", padx=(0, 20))
    
    f_sub_vistas = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    f_sub_vistas.pack(side="right", fill="both", expand=True)

    def sub_vista_resumen(parent):
        """Muestra indicadores clave (KPIs) y gráfica de evolución de ingresos."""
        limpiar_contenedor(parent)
        datos = cargar_datos()
        finanzas = datos.get("finanzas", [])

        # Cálculo de métricas financieras (Aritmética de negocio)
        total_recaudado = sum(p["monto"] for p in finanzas if p["estado"] == "Pagado")
        cuentas_por_cobrar = sum(p["monto"] for p in finanzas if p["estado"] == "Pendiente")
        
        #Cálculo por métricas generales
        servicios_stars={}
        for p in finanzas:
            if p["estado"]=="Pagado":
                tipo=p.get("servicio", "General")
                servicios_stars[tipo]=servicios_stars.get(tipo,0)+p["monto"]

        f_cards = ctk.CTkFrame(parent, fg_color="transparent")
        f_cards.pack(pady=20, fill="x")

        # Tarjetas de resumen ejecutivo
        for i, (tit, val, col, icon) in enumerate([
            ("TOTAL RECAUDADO", f"${total_recaudado:,.2f}", COLOR_ACENTO, "💰"),
            ("CUENTAS POR COBRAR", f"${cuentas_por_cobrar:,.2f}", "#ef4444", "⏳")
        ]):
            card = ctk.CTkFrame(f_cards, fg_color=COLOR_FONDO, corner_radius=15, border_width=1, border_color="#334155")
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            ctk.CTkLabel(card, text=f"{icon} {tit}", font=("Roboto", 13, "bold"), text_color=col).pack(pady=(15, 5))
            ctk.CTkLabel(card, text=val, font=("Roboto", 32, "bold")).pack(pady=(0, 15))
        
        f_cards.columnconfigure((0, 1), weight=1)

        #Bloque visual de ingresos por servicio
        if servicios_stars:
            f_servicios=ctk.CTkFrame(parent, fg_color=COLOR_FONDO, corner_radius=15, border_width=1, border_color="#334155")
            f_servicios.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(f_servicios, text="INGRESOS POR SERVICIO", font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(pady=5)

            f_grid_serv = ctk.CTkFrame(f_servicios, fg_color="transparent")
            f_grid_serv.pack(pady=(0, 10))
            
            for i, (serv, monto) in enumerate(servicios_stars.items()):
                lbl = ctk.CTkLabel(f_grid_serv, text=f"{serv}: ${monto:,.2f}", font=("Roboto", 12, "bold"), 
                                   fg_color="#1e293b", corner_radius=10, padx=15, pady=5)
                lbl.grid(row=0, column=i, padx=10)

        # Renderización de gráfica mediante Matplotlib integrado en Tkinter
        f_grafica = ctk.CTkFrame(parent, fg_color=COLOR_FONDO, corner_radius=15, border_width=1, border_color="#334155")
        f_grafica.pack(fill="both", expand=True, pady=10, padx=20)
        ctk.CTkLabel(f_grafica, text="EVOLUCIÓN DE INGRESOS", font=("Roboto", 14, "bold"), text_color="#9ca3af").pack(pady=10)
        
        try:
            if finanzas:
                df = pd.DataFrame(finanzas)
                if not df.empty and "estado" in df.columns:
                    df_pagados = df[df['estado'] == 'Pagado'].copy()
                    if not df_pagados.empty:
                        df_pagados['fecha_pago'] = pd.to_datetime(df_pagados['fecha_pago'])
                        ingresos_por_fecha = df_pagados.groupby('fecha_pago')['monto'].sum().sort_index()
                        
                        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
                        fig.patch.set_facecolor('#0f172a'); ax.set_facecolor('#0f172a')
                        ax.plot(ingresos_por_fecha.index.strftime('%d/%m'), ingresos_por_fecha.values, 'o-', color=COLOR_ACENTO)
                        ax.tick_params(axis='both', colors='white', labelsize=8)
                        
                        canvas = FigureCanvasTkAgg(fig, master=f_grafica)
                        canvas.draw(); canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
                        plt.close(fig)
        except: 
            pass

    def subvista_registrar_pago(parent):
        """Formulario para la captura de nuevos movimientos financieros."""
        limpiar_contenedor(parent)
        ctk.CTkLabel(parent, text="Registrar Nuevo Movimiento", font=("Roboto", 20, "bold")).pack(pady=20)
        datos = cargar_datos(); nombres_clientes = [c["nom_completo"] for c in datos.get("clientes", [])]
        f_form = ctk.CTkFrame(parent, fg_color="transparent"); f_form.pack(pady=10, padx=50, fill="x")
        
        def add_field(label, values=None, entry=False):
            """Helper de formulario para consistencia visual."""
            ctk.CTkLabel(f_form, text=label, font=("Roboto", 14, "bold")).pack(anchor="w", pady=(10, 0))
            if entry: w = ctk.CTkEntry(f_form, width=400)
            else: w = ctk.CTkComboBox(f_form, values=values, width=400)
            w.pack(pady=(5, 10)); return w

        cb_cliente = add_field("Seleccionar Cliente:", values=nombres_clientes if nombres_clientes else ["Sin clientes"])
        cb_servicio = add_field("Tipo de Servicio:", values=["Pensión", "Entrenamiento", "Clases", "Venta de Insumos", "Otros"])
        en_monto = add_field("Monto ($):", entry=True)
        cb_estado = add_field("Estado del Pago:", values=["Pagado", "Pendiente"])

        def guardar_pago():
            """Valida y persiste el pago en el backend."""
            try:
                monto = float(en_monto.get())
                id_cli = next((c["id_cliente"] for c in datos["clientes"] if c["nom_completo"] == cb_cliente.get()), "CL-000")
                pago = Finanzas_pension(f"PAG-{datetime.datetime.now().strftime('%M%S')}", id_cli, monto, datetime.datetime.now().strftime("%Y-%m-%d"), cb_estado.get(), cb_servicio.get())
                exito, msj = pago.registrar_pago()
                if exito: 
                    messagebox.showinfo("Éxito", msj); select_finance_tab("📈 RESUMEN", sub_vista_resumen)
                else: 
                    messagebox.showerror("Error", msj)
            except: 
                messagebox.showerror("Error", "Monto inválido.")

        ctk.CTkButton(parent, text="CONFIRMAR Y GUARDAR", fg_color=COLOR_ACENTO, height=40, width=250, command=guardar_pago).pack(pady=20)

    def subvista_reportes(parent):
        limpiar_contenedor(parent)
        ctk.CTkLabel(parent, text="Historial y Estados de Cuenta", font=("Roboto", 20, "bold")).pack(pady=20)
        datos=cargar_datos(); nombres_clientes=[c["nom_completo"] for c in datos.get("clientes", [])]
        f_filtro = ctk.CTkFrame(parent, fg_color="transparent"); f_filtro.pack(pady=10, padx=40, fill="x")
        cb_cliente_rep = ctk.CTkComboBox(f_filtro, values=nombres_clientes, width=300); cb_cliente_rep.pack(side="left", padx=10)
        
        f_tabla = ctk.CTkScrollableFrame(parent, fg_color=COLOR_FONDO, height=350); f_tabla.pack(fill="both", expand=True, padx=40, pady=10)

        def actualizar_tabla():
            limpiar_contenedor(f_tabla)
            datos_f = cargar_datos() # Cargar datos frescos
            cliente_sel = cb_cliente_rep.get()
            cliente_obj = next((c for c in datos_f["clientes"] if c["nom_completo"] == cliente_sel), None)
            if not cliente_obj: return
            
            pagos = [p for p in datos_f.get("finanzas", []) if p["id_cliente"] == cliente_obj["id_cliente"]]
            
            def saldar_pago(id_pago):
                if messagebox.askyesno("Confirmar", "¿Deseas marcar este adeudo como PAGADO?"):
                    p_temp = Finanzas_pension(id_pago, "", 0, "", "")
                    exito, msj = p_temp.saldar_deuda_pendiente()
                    if exito:
                        messagebox.showinfo("Éxito", msj)
                        actualizar_tabla()
                    else: messagebox.showerror("Error", msj)

            for p in pagos:
                f_row = ctk.CTkFrame(f_tabla, fg_color="#1e293b", corner_radius=8); f_row.pack(fill="x", pady=3, padx=5)
                ctk.CTkLabel(f_row, text=p["fecha_pago"], width=100).pack(side="left", padx=10)
                ctk.CTkLabel(f_row, text=f"${p['monto']:,.2f}", font=("Roboto", 13, "bold"), width=120).pack(side="left", padx=10)
                ctk.CTkLabel(f_row, text=p.get("servicio", "General"), font=("Roboto", 11), text_color="#9ca3af", width=120).pack(side="left", padx=10)
                
                if p["estado"] == "Pendiente":
                    ctk.CTkButton(f_row, text="COBRAR ADEUDO", width=140, height=28, fg_color="#f59e0b", hover_color="#d97706", 
                                   font=("Roboto", 11, "bold"), command=lambda idp=p["id_pago"]: saldar_pago(idp)).pack(side="right", padx=10)
                else:
                    ctk.CTkLabel(f_row, text="✅ PAGADO", text_color=COLOR_ACENTO, font=("Roboto", 11, "bold")).pack(side="right", padx=20)

        ctk.CTkButton(f_filtro, text="VER HISTORIAL", command=actualizar_tabla).pack(side="left", padx=10)
        def exportar():
            cliente_sel = cb_cliente_rep.get()
            datos_exp = cargar_datos()
            c_obj = next((c for c in datos_exp["clientes"] if c["nom_completo"] == cliente_sel), None)
            if c_obj:
                Estadistica_reporte(0,0,0).exportar_estado_cuenta(c_obj["id_cliente"])
                messagebox.showinfo("Éxito", f"Estado de cuenta exportado para {cliente_sel}")
            else: messagebox.showwarning("Atención", "Selecciona un cliente válido.")

        ctk.CTkButton(parent, text="📥 EXPORTAR TXT", fg_color="#3b82f6", command=exportar).pack(pady=10)

    def select_finance_tab(tab_name, func):
        for btn in btns_fin.values(): btn.configure(fg_color="transparent", text_color="white")
        btns_fin[tab_name].configure(fg_color=COLOR_ACENTO, text_color="white")
        func(f_sub_vistas)

    btns_fin = {}
    for txt, func in [("📈 RESUMEN", sub_vista_resumen), ("💰 REGISTRAR PAGO", subvista_registrar_pago), ("📄 REPORTES", subvista_reportes)]:
        btn = ctk.CTkButton(panel_nav, text=txt, fg_color="transparent", anchor="w", height=45, font=("Roboto", 13, "bold"), command=lambda t=txt, f=func: select_finance_tab(t, f))
        btn.pack(fill="x", padx=10, pady=5); btns_fin[txt] = btn

    select_finance_tab("📈 RESUMEN", sub_vista_resumen)


# ========================================================================
# 8. INVENTARIO (CONTROL DE SUMINISTROS)
# ========================================================================

def vista_inventario(frame_contenido):
    """
    Controlador de la vista de Inventario. Gestiona el stock de medicamentos,
    alimento y equipos mediante un sistema de alertas por bajo stock.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal.
    """
    limpiar_contenedor(frame_contenido)
    
    # Header de sección
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Control de Inventario y Suministros", font=("Roboto", 28, "bold")).pack(side="left")

    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # Sidebar interna: Catálogo de Productos
    panel_izq = ctk.CTkFrame(frame_principal, width=320, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_izq.pack(side="left", fill="y", padx=(0, 20))
    panel_izq.pack_propagate(False) 
    
    ctk.CTkLabel(panel_izq, text="SUMINISTROS", font=("Roboto", 13, "bold"), text_color="#9ca3af").pack(pady=(20, 10))

    lista_scroll = ctk.CTkScrollableFrame(panel_izq, fg_color="transparent")
    lista_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    # Panel de detalle (Derecha)
    panel_der = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_der.pack(side="right", fill="both", expand=True)

    estado = {"item_actual": None}

    def cargar_lista():
        """Refresca el listado de suministros, resaltando en rojo los items críticos."""
        limpiar_contenedor(lista_scroll)
        datos = cargar_datos()
        for item in datos["inventario"]:
            # Lógica de Negocio: Stock bajo definido como <= 5 unidades
            color_txt = "#ef4444" if item["cantidad"] <= 5 else "white"
            f_item = ctk.CTkFrame(lista_scroll, fg_color="transparent", corner_radius=8, cursor="hand2")
            f_item.pack(pady=2, fill="x", padx=5)
            
            lbl = ctk.CTkLabel(f_item, text=f"{item['nombre']} ({item['cantidad']})", 
                                text_color=color_txt, font=("Roboto", 13),
                                justify="left", wraplength=260, anchor="w")
            lbl.pack(pady=5, padx=10, fill="x")
            
            for widget in [f_item, lbl]:
                widget.bind("<Button-1>", lambda e, n=item['nombre']: seleccionar_item(n))
                widget.bind("<Enter>", lambda e, f=f_item: f.configure(fg_color="#334155"))
                widget.bind("<Leave>", lambda e, f=f_item: f.configure(fg_color="transparent"))

    def seleccionar_item(nombre):
        """Carga la ficha técnica detallada del producto seleccionado."""
        estado["item_actual"] = nombre
        limpiar_contenedor(panel_der)
        datos = cargar_datos()
        obj = next((i for i in datos["inventario"] if i["nombre"] == nombre), None)
        if not obj: return

        ctk.CTkLabel(panel_der, text="DETALLE DEL PRODUCTO", font=("Roboto", 16, "bold"), text_color=COLOR_ACENTO).pack(pady=(20, 10), padx=30, anchor="w")
        
        # Widget de Stock Crítico
        f_metric = ctk.CTkFrame(panel_der, fg_color=COLOR_FONDO, corner_radius=15, border_width=1, border_color="#334155")
        f_metric.pack(padx=30, pady=10, fill="x")
        ctk.CTkLabel(f_metric, text="STOCK ACTUAL", font=("Roboto", 12, "bold"), text_color="#9ca3af").pack(pady=(15, 0))
        ctk.CTkLabel(f_metric, text=str(obj["cantidad"]), font=("Roboto", 48, "bold"), text_color="#ef4444" if obj["cantidad"] <= 5 else "white").pack(pady=(0, 15))

        f_fields = ctk.CTkFrame(panel_der, fg_color="transparent"); f_fields.pack(padx=30, pady=10, fill="x")
        ctk.CTkLabel(f_fields, text="Próxima Caducidad:", font=("Roboto", 14, "bold")).pack(anchor="w")
        e_cad = ctk.CTkEntry(f_fields, width=350); e_cad.insert(0, obj.get("caducidad", "N/A")); e_cad.pack(anchor="w", pady=(5, 15))
        ctk.CTkLabel(f_fields, text="Último Abastecimiento:", font=("Roboto", 14, "bold")).pack(anchor="w")
        e_aba = ctk.CTkEntry(f_fields, width=350); e_aba.insert(0, obj.get("ultimo_abastecimiento", "N/A")); e_aba.pack(anchor="w", pady=(5, 15))

        ctk.CTkLabel(panel_der, text="Descripción / Indicaciones de Uso:", font=("Roboto", 14, "bold")).pack(anchor="w", padx=30, pady=(10, 5))
        caja_desc = ctk.CTkTextbox(panel_der, height=150, fg_color=COLOR_FONDO, border_width=1, border_color="#334155")
        caja_desc.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        caja_desc.insert("1.0", obj.get("descripcion", ""))

        f_btns = ctk.CTkFrame(panel_der, fg_color="transparent"); f_btns.pack(side="bottom", fill="x", pady=30, padx=30)
        
        def guardar_cambios():
            """Persiste las ediciones de texto (descripción/fechas) sin alterar el stock."""
            desc = caja_desc.get("1.0", "end").strip()
            cad = e_cad.get(); aba = e_aba.get()
            if Inventario(nombre, obj["cantidad"], cad, aba, descripcion=desc).actualizar_producto()[0]:
                messagebox.showinfo("Éxito", "Datos del producto guardados correctamente.")
                cargar_lista()

        def mod(delta):
            """Gestiona el incremento o decremento de existencias mediante input modal."""
            d = ctk.CTkInputDialog(text=f"Cantidad a {'sumar' if delta>0 else 'restar'}:", title="Stock"); v = d.get_input()
            if v and v.isdigit():
                nc = obj["cantidad"] + (int(v) * delta)
                if nc < 0: return messagebox.showerror("Error", "Stock insuficiente.")
                desc = caja_desc.get("1.0", "end").strip()
                if Inventario(nombre, nc, e_cad.get(), e_aba.get(), descripcion=desc).actualizar_producto()[0]:
                    cargar_lista(); seleccionar_item(nombre)

        ctk.CTkButton(f_btns, text="➕ ABASTECER", fg_color=COLOR_ACENTO, height=40, command=lambda: mod(1)).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(f_btns, text="➖ RETIRAR", fg_color="#ef4444", height=40, command=lambda: mod(-1)).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(f_btns, text="💾 GUARDAR CAMBIOS", fg_color="#3b82f6", height=40, command=guardar_cambios).pack(side="left", expand=True, padx=5)

    def nuevo():
        """Registra un nuevo producto en el catálogo base."""
        d = ctk.CTkInputDialog(text="Nombre:", title="Nuevo"); n = d.get_input()
        if n and Inventario(n.strip()).agregar_producto()[0]: 
            cargar_lista(); seleccionar_item(n.strip())

    ctk.CTkButton(panel_izq, text="➕ NUEVO PRODUCTO", fg_color="black", height=40, command=nuevo).pack(side="bottom", pady=20, padx=15, fill="x")
    
    # Inicialización del listado
    cargar_lista()
    if cargar_datos()["inventario"]: 
        seleccionar_item(cargar_datos()["inventario"][0]["nombre"])

# ========================================================================
# 9. USUARIOS (ADMINISTRACIÓN DE ACCESO)
# ========================================================================

def vista_usuarios(frame_contenido):
    """
    Gestiona las cuentas de acceso, roles y seguridad del sistema.
    Vista restringida exclusivamente al Administrador Principal.

    Args:
        frame_contenido (ctk.CTkFrame): Contenedor principal.
    """
    limpiar_contenedor(frame_contenido)
    
    f_header = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    f_header.pack(pady=(20, 20), padx=40, fill="x")
    ctk.CTkLabel(f_header, text="Administración de Usuarios", font=("Roboto", 28, "bold")).pack(side="left")

    frame_principal = ctk.CTkFrame(frame_contenido, fg_color="transparent")
    frame_principal.pack(fill="both", expand=True, padx=40, pady=10)

    # Sidebar: Listado de Cuentas
    panel_izq = ctk.CTkFrame(frame_principal, width=280, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_izq.pack(side="left", fill="y", padx=(0, 20))
    
    ctk.CTkLabel(panel_izq, text="CUENTAS DE ACCESO", font=("Roboto", 13, "bold"), text_color="#9ca3af").pack(pady=(20, 10))
    lista_scroll = ctk.CTkScrollableFrame(panel_izq, fg_color="transparent")
    lista_scroll.pack(fill="both", expand=True, padx=10, pady=5)

    f_btns_izq = ctk.CTkFrame(panel_izq, fg_color="transparent")
    f_btns_izq.pack(side="bottom", fill="x", pady=20, padx=10)

    # Detalles del Perfil (Derecha)
    panel_der = ctk.CTkFrame(frame_principal, fg_color=COLOR_PANEL_LATERAL, corner_radius=15)
    panel_der.pack(side="right", fill="both", expand=True)

    ctk.CTkLabel(panel_der, text="INFORMACIÓN DE USUARIO", font=("Roboto", 16, "bold"), text_color=COLOR_ACENTO).pack(pady=(20, 10), padx=30, anchor="w")

    f_formulario = ctk.CTkFrame(panel_der, fg_color="transparent")
    f_formulario.pack(fill="x", pady=10, padx=30)

    estado = {"user_actual": None}

    def crear_campo_usuario(parent, row, label, widget_type="entry", values=None):
        """Generador de filas alineadas para el formulario de usuarios."""
        ctk.CTkLabel(parent, text=label, font=("Roboto", 14, "bold")).grid(row=row, column=0, pady=(15, 0), padx=(0, 20), sticky="w")
        if widget_type == "entry":
            w = ctk.CTkEntry(parent, width=400, height=35, corner_radius=8)
        elif widget_type == "combo":
            w = ctk.CTkComboBox(parent, values=values, width=400, height=35, corner_radius=8)
        w.grid(row=row+1, column=0, pady=(5, 10), sticky="w")
        return w

    e_id = crear_campo_usuario(f_formulario, 0, "ID de Ingreso (Login):")
    e_nombre = crear_campo_usuario(f_formulario, 2, "Nombre Completo:")
    c_rol = crear_campo_usuario(f_formulario, 4, "Rol del Sistema:", "combo", ["Administrador Principal", "Personal Operativo", "Recepcionista"])
    
    ctk.CTkFrame(panel_der, height=1, fg_color="#334155").pack(fill="x", padx=30, pady=20)
    ctk.CTkLabel(panel_der, text="SEGURIDAD Y CONTACTO", font=("Roboto", 16, "bold"), text_color="#3b82f6").pack(pady=(0, 10), padx=30, anchor="w")
    
    f_form_2 = ctk.CTkFrame(panel_der, fg_color="transparent")
    f_form_2.pack(fill="x", pady=10, padx=30)
    
    e_contacto = crear_campo_usuario(f_form_2, 0, "Contacto (Email/Tel):")
    e_pass = crear_campo_usuario(f_form_2, 2, "Contraseña:")

    f_botones_der = ctk.CTkFrame(panel_der, fg_color="transparent")
    f_botones_der.pack(side="bottom", fill="x", pady=30, padx=30)

    btn_accion_principal = ctk.CTkButton(f_botones_der, text="Editar Perfil", font=("Roboto", 13, "bold"), height=40)
    btn_accion_principal.pack(side="left", expand=True, padx=5)

    btn_eliminar = ctk.CTkButton(f_botones_der, text="ELIMINAR", fg_color="#ef4444", hover_color="#b91c1c", font=("Roboto", 13, "bold"), height=40)
    btn_eliminar.pack(side="right", expand=True, padx=5)

    def cambiar_estado_campos(estado_tk):
        """Conmuta entre modo lectura ('disabled') y modo edición ('normal')."""
        for widget in [e_nombre, c_rol, e_contacto, e_pass]:
            widget.configure(state=estado_tk)

    def cargar_lista():
        limpiar_contenedor(lista_scroll)
        datos = cargar_datos()
        for u in datos["usuarios"]:
            btn = ctk.CTkButton(lista_scroll, text=u["nombre"], 
                                 fg_color="transparent", text_color="white", anchor="w",
                                 hover_color="#334155", height=35,
                                 command=lambda uid=u["id_usuario"]: seleccionar_usuario(uid))
            btn.pack(pady=2, fill="x")

    def seleccionar_usuario(username):
        """Carga los datos del usuario en el formulario y bloquea la edición por defecto."""
        estado["user_actual"] = username
        datos = cargar_datos()
        u = next((user for user in datos["usuarios"] if user["id_usuario"] == username), None)
        if not u: return

        cambiar_estado_campos("normal")
        e_id.configure(state="normal")
        e_id.delete(0, 'end'); e_id.insert(0, u["id_usuario"])
        e_id.configure(state="disabled")
        
        e_nombre.delete(0, 'end'); e_nombre.insert(0, u["nombre"])
        c_rol.set(u["rol"])
        e_contacto.delete(0, 'end'); e_contacto.insert(0, u.get("contacto", ""))
        e_pass.delete(0, 'end'); e_pass.insert(0, u["contraseña"])
        
        cambiar_estado_campos("disabled")
        btn_accion_principal.configure(text="EDITAR PERFIL", fg_color="#3b82f6", command=habilitar_edicion)
        btn_eliminar.configure(state="normal", command=eliminar)

    def habilitar_edicion():
        cambiar_estado_campos("normal")
        btn_accion_principal.configure(text="ACTUALIZAR DATOS", fg_color=COLOR_ACENTO, hover_color="#059669", command=procesar_actualizacion)

    def procesar_actualizacion():
        """Llama al backend para persistir los cambios en el perfil de usuario."""
        uid = e_id.get().strip().lower()
        if not e_nombre.get().strip() or not e_pass.get().strip(): 
            return messagebox.showwarning("Atención", "Nombre y Contraseña son obligatorios.")

        if messagebox.askyesno("Confirmar", "¿Confirmas cambiar los datos de este usuario?"):
            usuario_temp = Usuario(id_usuario=uid, nombre=e_nombre.get(), contraseña=e_pass.get(), rol=c_rol.get(), contacto=e_contacto.get())
            exito, msj = usuario_temp.actualizar_usuario()
            
            if exito: 
                cargar_lista(); seleccionar_usuario(uid) 
                messagebox.showinfo("Éxito", msj)
            else: messagebox.showerror("Error", msj)

    def preparar_nuevo():
        """Limpia el formulario para la creación de una cuenta nueva."""
        estado["user_actual"] = None
        e_id.configure(state="normal")
        cambiar_estado_campos("normal")
        e_id.delete(0, 'end'); e_nombre.delete(0, 'end')
        c_rol.set("Personal Operativo")
        e_contacto.delete(0, 'end'); e_pass.delete(0, 'end')
        e_id.focus()
        btn_accion_principal.configure(text="GUARDAR NUEVO", fg_color=COLOR_ACENTO, hover_color="#059669", command=procesar_creacion)
        btn_eliminar.configure(state="disabled")

    def procesar_creacion():
        uid = e_id.get().strip().lower()
        if not uid or not e_nombre.get().strip() or not e_pass.get().strip(): 
            return messagebox.showwarning("Atención", "Faltan datos obligatorios.")
            
        usuario_temp = Usuario(id_usuario=uid, nombre=e_nombre.get(), contraseña=e_pass.get(), rol=c_rol.get(), contacto=e_contacto.get())
        exito, msj = usuario_temp.registrar_usuario()
        
        if exito: 
            cargar_lista(); seleccionar_usuario(uid)
            messagebox.showinfo("Éxito", msj)
        else: messagebox.showerror("Error", msj)

    def buscar():
        """Diálogo de búsqueda rápida por ID o Nombre."""
        dialog = ctk.CTkInputDialog(text="Ingresa el nombre o ID del usuario:", title="Buscar")
        busq = dialog.get_input()
        if busq:
            busq = busq.lower(); datos = cargar_datos()
            for u in datos["usuarios"]:
                if busq in u["id_usuario"].lower() or busq in u["nombre"].lower():
                    seleccionar_usuario(u["id_usuario"])
                    return
            messagebox.showinfo("Búsqueda", "Usuario no encontrado.")

    def eliminar():
        uid = estado["user_actual"]
        if not uid: return
        
        if messagebox.askyesno("Confirmar", f"¿Deseas eliminar a {uid}?\nAcción irreversible."):
            usuario_temp = Usuario(id_usuario="", nombre="", contraseña="", rol="")
            exito, msj = usuario_temp.eliminar_usuario(uid)
            if exito: 
                messagebox.showinfo("Eliminado", msj)
                preparar_nuevo(); cargar_lista()
            else: messagebox.showerror("Error", msj)

    ctk.CTkButton(f_btns_izq, text="🔍 BUSCAR", fg_color="black", height=35, command=buscar).pack(pady=5, fill="x")
    ctk.CTkButton(f_btns_izq, text="➕ CREAR NUEVO", fg_color="black", height=35, command=preparar_nuevo).pack(pady=5, fill="x")

    # Carga inicial del primer usuario
    cargar_lista()
    datos_iniciales = cargar_datos()
    if datos_iniciales["usuarios"]: 
        seleccionar_usuario(datos_iniciales["usuarios"][0]["id_usuario"])
    else:
        preparar_nuevo()

# ========================================================================
# 10. INICIALIZACIÓN: DASHBOARD PRINCIPAL Y LOGIN
# ========================================================================

def iniciar_dashboard(ventana, rol_usuario, nombre_usuario):
    """
    Construye la arquitectura base del sistema una vez autenticado el usuario.
    Configura el menú lateral dinámico según los permisos del Rol.

    Args:
        ventana (ctk.CTk): Ventana raíz de la aplicación.
        rol_usuario (str): Nivel de privilegios.
        nombre_usuario (str): Nombre real para el saludo de bienvenida.
    """
    limpiar_contenedor(ventana)
    
    # Estructura de layout: Sidebar fija + Contenido variable
    frame_lateral = ctk.CTkFrame(ventana, width=220, corner_radius=0, fg_color=COLOR_PANEL_LATERAL)
    frame_lateral.pack(side="left", fill="y")
    frame_contenido = ctk.CTkFrame(ventana, corner_radius=0, fg_color=COLOR_FONDO)
    frame_contenido.pack(side="right", fill="both", expand=True)
    
    ctk.CTkLabel(frame_lateral, text="S I G E", font=("Roboto", 22, "bold"), text_color=COLOR_ACENTO).pack(pady=(20, 5))
    ctk.CTkLabel(frame_lateral, text="Menú Principal", font=("Roboto", 12)).pack(pady=(0, 20))
    
    def select_menu(btn_name, func):
        """Gestiona el estado visual de los botones del menú lateral principal."""
        for name, b in btns_side.items():
            # Estilo especial para el botón de admin
            if name == "Administrar usuarios":
                b.configure(fg_color="#3b82f6", border_width=0)
            else:
                b.configure(fg_color="transparent", border_width=1, border_color="#334155")
        
        btns_side[btn_name].configure(fg_color=COLOR_ACENTO, border_width=0)
        func()

    btns_side = {}
    def add_menu_btn(text, func):
        """Helper para agregar botones al menú lateral con formato uniforme."""
        btn = ctk.CTkButton(frame_lateral, text=text, fg_color="transparent", border_width=1, border_color="#334155",
                            height=40, font=("Roboto", 13), command=lambda t=text, f=func: select_menu(t, f))
        btn.pack(pady=5, padx=15, fill="x")
        btns_side[text] = btn

    # Acceso universal a Inicio
    add_menu_btn("Inicio", lambda: vista_dashboard(frame_contenido, rol_usuario, nombre_usuario))

    # Control de Accesos por Rol (RBAC - Role Based Access Control)
    if rol_usuario in ["Administrador Principal", "Personal Operativo"]:
        add_menu_btn("Bitácora Médica", lambda: vista_bitacora(frame_contenido))
        add_menu_btn("Equinos", lambda: vista_equinos(frame_contenido))

    if rol_usuario in ["Administrador Principal", "Recepcionista"]:
        add_menu_btn("Directorio de clientes", lambda: vista_clientes(frame_contenido))
        add_menu_btn("Finanzas", lambda: vista_finanzas(frame_contenido))

    if rol_usuario in ["Administrador Principal", "Recepcionista", "Personal Operativo"]:
        add_menu_btn("Inventario", lambda: vista_inventario(frame_contenido))
    ctk.CTkLabel(frame_lateral, text="").pack(expand=True)

    # Botón exclusivo de administración técnica
    if rol_usuario == "Administrador Principal":
        add_menu_btn("Administrar usuarios", lambda: vista_usuarios(frame_contenido))
        btns_side["Administrar usuarios"].configure(fg_color="#3b82f6", border_width=0, hover_color="#2563eb", font=("Roboto", 13, "bold"))
    
    ctk.CTkButton(frame_lateral, text="Cerrar Sesión", fg_color="#ef4444", hover_color="#b91c1c", height=40, font=("Roboto", 13, "bold"),
                  command=lambda: mostrar_login(ventana)).pack(pady=(5, 20), padx=15, fill="x")

    # Carga de vista inicial
    select_menu("Inicio", lambda: vista_dashboard(frame_contenido, rol_usuario, nombre_usuario))

def mostrar_login(ventana):
    """
    Renderiza la pantalla de autenticación.
    Centraliza la validación de credenciales y la seguridad inicial.

    Args:
        ventana (ctk.CTk): Ventana raíz.
    """
    limpiar_contenedor(ventana)
    ventana.title("SIGE - Iniciar Sesión")
    
    # Estética premium para el login (Uniformidad con el logotipo)
    COLOR_LOGIN = "#1a1c2c" 
    
    frame_login = ctk.CTkFrame(ventana, corner_radius=15, fg_color=COLOR_LOGIN)
    frame_login.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

    ctk.CTkLabel(frame_login, text="S I G E", font=("Roboto", 42, "bold"), text_color=COLOR_ACENTO).pack(pady=(40, 5), padx=80)
    
    # Carga de branding corporativo
    try:
        ruta_logo = os.path.join(CARPETA_IMAGENES, "caballo_logo.png")
        if os.path.exists(ruta_logo):
            pil_logo = Image.open(ruta_logo)
            ancho_final = 280
            alto_final = int(ancho_final * (pil_logo.height / pil_logo.width))
            
            ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(ancho_final, alto_final))
            lbl_logo = ctk.CTkLabel(frame_login, image=ctk_logo, text="", fg_color="transparent")
            lbl_logo.pack(pady=(5, 15))
    except Exception as e:
        print(f"Error al cargar el logo en login: {e}")

    ctk.CTkLabel(frame_login, text="Gestión Ecuestre", font=("Roboto", 18, "italic"), text_color="#9ca3af").pack(pady=(0, 30), padx=80)

    entry_usuario = ctk.CTkEntry(frame_login, placeholder_text="Nombre completo", width=220)
    entry_usuario.pack(pady=10, padx=40)

    entry_password = ctk.CTkEntry(frame_login, placeholder_text="Contraseña", show="*", width=220)
    entry_password.pack(pady=10, padx=40)

    def intentar_login():
        """Valida las credenciales contra el backend y gestiona el flujo de error/éxito."""
        n_ingreso = entry_usuario.get().strip(); p_ingreso = entry_password.get()
        user_temp = Usuario(id_usuario="", nombre="", contraseña="", rol="")
        
        exito, rol, nombre_real = user_temp.iniciar_sesion(n_ingreso, p_ingreso)
        
        if exito: 
            iniciar_dashboard(ventana, rol, nombre_real) 
        else: 
            messagebox.showerror("Error", rol)

    ctk.CTkButton(frame_login, text="Entrar", fg_color=COLOR_ACENTO, hover_color="#059669", command=intentar_login, width=220).pack(pady=(20, 30))

def app():
    ventana = ctk.CTk()
    ventana.title("SIGE")
    
    # Abrir en pantalla completa (Maximizado)
    ventana.after(0, lambda: ventana.state('zoomed'))
    
    mostrar_login(ventana)
    ventana.mainloop()

if __name__ == "__main__":
    app()
