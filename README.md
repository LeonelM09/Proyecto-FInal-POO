# SIGE: Sistema Integral de Gestión Ecuestre 🐎

SIGE es una solución tecnológica desarrollada en Python diseñada para automatizar y centralizar la administración operativa, clínica y financiera de instalaciones ecuestres. El sistema permite pasar de registros manuales a una gestión digital eficiente, facilitando la toma de decisiones estratégicas mediante el análisis de datos.

---

## 🎯 Alcance de la Herramienta

### 🏥 Gestión Clínica
*   **Bitácora Médica:** Seguimiento de protocolos preventivos como herrajes y vacunas con historial clínico persistente.
*   **Sistema de Semáforo:** Indicadores visuales inteligentes sobre el estado de salud y alertas automáticas de vencimientos.
*   **Generación de Recetas:** Exportación de raciones, tratamientos e indicaciones médicas en archivos de texto (.txt).
*   **Calendario Interactivo:** Visualización de la agenda médica con capacidad de reagendar o completar citas con un clic.

### 🐴 Control Operativo y de Inventario
*   **Mapa de Caballerizas:** Grid dinámico para la asignación, monitoreo y gestión física de boxes (Mapa de Caballerizas).
*   **Gestión de Stock:** Control riguroso de suministros con alertas automáticas de existencias críticas (≤ 5 unidades).
*   **Seguimiento de Entrenamiento:** Registro de asistencia y progreso por etapas (de Iniciación a Avanzado) y nivel de arrendamiento.
*   **Gestión de Alimentación:** Descuento automático de inventario al suministrar raciones diarias.

### 👥 CRM y Gestión de Clientes
*   **Directorio Profesional:** Gestión de propietarios y visualización de caballos asociados.
*   **Panel CRM Integrado:** Seguimiento de notas de operación, estados de cuenta individuales y términos de pensión.

---

## 🏗️ Arquitectura Técnica

El sistema ha sido diseñado bajo estándares de **Clean Code** y **Programación Orientada a Objetos (POO)** para garantizar escalabilidad:

*   **Interfaz (Frontend):** Desarrollada con `CustomTkinter` para una experiencia de usuario moderna, fluida y con soporte nativo para modo oscuro.
*   **Lógica de Negocio (Backend):** Implementación robusta de POO que separa la gestión de datos de la interfaz gráfica.
*   **Análisis de Datos:** Uso de `Pandas` y `Matplotlib` para el procesamiento estadístico y visualización de la evolución financiera.
*   **Persistencia:** Almacenamiento local mediante estructuras `JSON`, lo que permite un sistema ligero sin dependencias de bases de datos externas pesadas.

---

## 🔐 Control de Accesos (Roles - RBAC)

SIGE garantiza la integridad de los datos mediante un sistema de Roles basado en Permisos:

1.  **Administrador Principal:** Acceso total al sistema, gestión de usuarios técnicos y configuración global.
2.  **Recepcionista:** Especializado en la gestión de clientes, finanzas corporativas, reportes e inventario.
3.  **Personal Operativo:** Enfocado en la operatividad clínica, bitácora médica, equinos y control de suministros.

---

## 📁 Estructura del Proyecto

*   `frontend.py`: Controlador de la interfaz gráfica y flujo de navegación.
*   `backend.py`: Motor del sistema, definiciones de clases y persistencia.
*   `database_sige.json`: Base de datos centralizada.
*   `imagenes_equinos/`: Repositorio local de archivos multimedia.
*   `Recetas_Medicas/` & `Reportes_Financieros/`: Directorios de exportación automática de documentos.

---

## ⚙️ Instalación y Uso

1. **Requisitos:** Python 3.10 o superior.
2. **Dependencias:**
   ```bash
   pip install customtkinter pillow pandas matplotlib
   ```
3. **Ejecución:**
   ```bash
   python frontend.py
   ```

---
**SIGE - Transformando la tradición ecuestre con tecnología de vanguardia.**
