import streamlit as st
import pandas as pd
import os

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Ruta base (ajusta solo si cambias de carpeta)
BASE_DIR = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Documentos\Reportes\01_Informes Power BI\01_Analisis de Solicitudes y Ordenes de Compras\Actualiza Informes Phyton\control_estado_medicamentos"
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
LOGO_FILE = os.path.join(BASE_DIR, "logo_empresa.png")

# ==============================
# FUNCIÓN LOGIN
# ==============================
def login():
    st.sidebar.image(LOGO_FILE, use_container_width=True)
    st.sidebar.title("💊 Control de Medicamentos")
    st.sidebar.markdown("---")

    st.sidebar.subheader("🔐 Inicio de sesión")

    usuario = st.sidebar.text_input("Usuario")
    contraseña = st.sidebar.text_input("Contraseña", type="password")

    # Cargar archivo de usuarios
    try:
        usuarios = pd.read_csv(USUARIOS_FILE, dtype=str)
        usuarios.columns = usuarios.columns.str.strip().str.lower()
    except Exception as e:
        st.error(f"⚠️ No se pudo leer el archivo de usuarios: {e}")
        return False

    # Verificar autenticación
    if st.sidebar.button("Iniciar sesión", use_container_width=True):
        if ((usuarios["usuario"] == usuario) & (usuarios["contraseña"] == contraseña)).any():
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.sidebar.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.sidebar.error("❌ Usuario o contraseña incorrectos.")

# ==============================
# FUNCIÓN PRINCIPAL
# ==============================
def main():
    # Panel lateral (solo visible si está autenticado)
    with st.sidebar:
        st.image(LOGO_FILE, use_container_width=True)
        st.title("📋 Menú Principal")
        st.markdown(f"👤 **Usuario:** {st.session_state['usuario']}")
        st.markdown("---")

        # Botón de cerrar sesión
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["usuario"] = ""
            st.rerun()

    # Contenido principal
    st.title("📊 Panel de Control - Estado de Medicamentos")
    st.success(f"Bienvenido, **{st.session_state['usuario']}** 👋")
    st.markdown("---")

    st.write("Aquí irá el contenido de tu aplicación después del login...")

# ==============================
# CONTROL DE SESIÓN
# ==============================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""

if not st.session_state["autenticado"]:
    login()
else:
    main()
