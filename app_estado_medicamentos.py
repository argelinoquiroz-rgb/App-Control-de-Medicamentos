import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Control de Estado de Medicamentos",
    page_icon="💊",
    layout="wide"
)

# ---------------- CONFIGURACIÓN DE RUTAS ----------------
BASE_DIR = os.getcwd()
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_empresa.png")

# Crear carpetas necesarias
os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "soportes"), exist_ok=True)

# ---------------- VALIDACIÓN ARCHIVO DE USUARIOS ----------------
if not os.path.exists(USUARIOS_FILE):
    pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USUARIOS_FILE, index=False)

usuarios = pd.read_csv(USUARIOS_FILE, dtype=str)
usuarios.columns = usuarios.columns.str.lower().str.strip().str.replace("ñ", "n")

# Asegurar columnas correctas
if "usuario" not in usuarios.columns or "contrasena" not in usuarios.columns:
    st.warning("⚠️ El archivo de usuarios tenía formato incorrecto, se ha regenerado automáticamente.")
    pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USUARIOS_FILE, index=False)
    usuarios = pd.read_csv(USUARIOS_FILE, dtype=str)
    usuarios.columns = usuarios.columns.str.lower().str.strip().str.replace("ñ", "n")

# ---------------- FUNCIÓN LOGIN ----------------
def login():
    st.markdown("<h2 style='text-align:center; color:#1B4965;'>💊 Control de Estado de Medicamentos</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # Logo
    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH)
            st.image(logo, width=180)
        except Exception:
            st.warning("⚠️ No se pudo mostrar el logo.")
    else:
        st.info("🏥 Logo no encontrado en la carpeta 'assets'.")

    usuario = st.text_input("👤 Usuario")
    contrasena = st.text_input("🔑 Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if ((usuarios["usuario"] == usuario) & (usuarios["contrasena"] == contrasena)).any():
            st.session_state["usuario_autenticado"] = usuario
            st.success("✅ Inicio de sesión exitoso.")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos.")

# ---------------- FUNCIÓN PRINCIPAL ----------------
def app_principal():
    st.sidebar.title(f"👋 Bienvenido, {st.session_state['usuario_autenticado']}")
    if st.sidebar.button("🔒 Cerrar sesión"):
        del st.session_state["usuario_autenticado"]
        st.rerun()

    st.markdown("<h2 style='color:#1B4965;'>Panel Principal</h2>", unsafe_allow_html=True)
    st.write("Aquí irá el contenido principal de tu aplicación para gestionar el estado de medicamentos (agotados, desabastecidos, descontinuados, etc).")

    # Ejemplo de sección de registro
    with st.expander("➕ Registrar nuevo medicamento"):
        col1, col2, col3 = st.columns(3)
        nombre = col1.text_input("Nombre del medicamento")
        estado = col2.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"])
        fecha = col3.date_input("Fecha de registro", datetime.today())
        if st.button("Guardar registro"):
            st.success(f"💾 Medicamento '{nombre}' registrado correctamente como '{estado}' el {fecha}.")

# ---------------- CONTROL DE SESIÓN ----------------
if "usuario_autenticado" not in st.session_state:
    login()
else:
    app_principal()

