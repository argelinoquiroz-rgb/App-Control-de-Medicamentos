import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Control de Estado de Medicamentos",
    page_icon="💊",
    layout="wide"
)

# ---------------- CONFIGURACIÓN DE ARCHIVOS ----------------
BASE_DIR = os.getcwd()
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")

# ---------------- CREAR ARCHIVOS SI NO EXISTEN ----------------
if not os.path.exists(USUARIOS_FILE):
    pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USUARIOS_FILE, index=False)

if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=["Medicamento", "Estado", "Fecha", "Observaciones"]).to_csv(DATA_FILE, index=False)

# ---------------- FUNCIONES AUXILIARES ----------------
def cargar_usuarios():
    usuarios = pd.read_csv(USUARIOS_FILE)
    usuarios.columns = usuarios.columns.str.lower().str.strip().str.replace("ñ", "n")
    return usuarios

def guardar_usuario(nuevo_usuario, nueva_contrasena):
    usuarios = cargar_usuarios()
    if nuevo_usuario in usuarios["usuario"].values:
        st.warning("⚠️ El usuario ya existe.")
    else:
        nuevo = pd.DataFrame({"usuario": [nuevo_usuario], "contrasena": [nueva_contrasena]})
        usuarios = pd.concat([usuarios, nuevo], ignore_index=True)
        usuarios.to_csv(USUARIOS_FILE, index=False)
        st.success("✅ Usuario creado correctamente.")

def cargar_registros():
    return pd.read_csv(DATA_FILE)

def guardar_registro(medicamento, estado, observaciones):
    registros = cargar_registros()
    nuevo = pd.DataFrame({
        "Medicamento": [medicamento],
        "Estado": [estado],
        "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Observaciones": [observaciones]
    })
    registros = pd.concat([registros, nuevo], ignore_index=True)
    registros.to_csv(DATA_FILE, index=False)
    st.success("✅ Registro guardado correctamente.")

# ---------------- FUNCIÓN DE LOGIN ----------------
def login():
    st.markdown("<h2 style='text-align:center;'>💊 Control de Estado de Medicamentos</h2>", unsafe_allow_html=True)
    st.markdown("### 🔐 Iniciar sesión")

    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")
    btn_login = st.button("Ingresar", use_container_width=True)

    if btn_login:
        usuarios = cargar_usuarios()
        if ((usuarios["usuario"] == usuario) & (usuarios["contrasena"] == contrasena)).any():
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.success(f"✅ Bienvenido, {usuario}!")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos.")

# ---------------- PANEL PRINCIPAL ----------------
def panel_principal():
    with st.sidebar:
        st.image("assets/logo_empresa.png", width=180)
        st.markdown(f"👤 **Usuario:** {st.session_state['usuario']}")
        st.divider()
        menu = st.selectbox(
            "📋 Menú Principal",
            ["🏠 Inicio", "📦 Registrar Medicamento", "📁 Registros Guardados", "👥 Administración de Usuarios", "🚪 Cerrar Sesión"]
        )

    # ---- INICIO ----
    if menu == "🏠 Inicio":
        st.markdown("## 🏥 Bienvenido al Panel de Control")
        st.info("Desde aquí puedes registrar, visualizar y administrar el estado de los medicamentos.")

    # ---- REGISTRO DE MEDICAMENTOS ----
    elif menu == "📦 Registrar Medicamento":
        st.markdown("## 📦 Registrar nuevo medicamento")
        medicamento = st.text_input("Nombre del medicamento")
        estado = st.selectbox("Estado", ["Disponible", "Agotado", "Desabastecido", "Descontinuado"])
        observaciones = st.text_area("Observaciones adicionales")
        if st.button("Guardar registro"):
            if medicamento:
                guardar_registro(medicamento, estado, observaciones)
            else:
                st.warning("⚠️ Debes ingresar el nombre del medicamento.")

    # ---- REGISTROS GUARDADOS ----
    elif menu == "📁 Registros Guardados":
        st.markdown("## 📁 Registros Guardados")
        registros = cargar_registros()
        if registros.empty:
            st.info("No hay registros guardados aún.")
        else:
            st.dataframe(registros, use_container_width=True)

    # ---- ADMINISTRACIÓN DE USUARIOS ----
    elif menu == "👥 Administración de Usuarios":
        st.markdown("## 👥 Administración de Usuarios")
        nuevo_usuario = st.text_input("Nuevo usuario")
        nueva_contrasena = st.text_input("Nueva contraseña", type="password")
        if st.button("Crear usuario"):
            if nuevo_usuario and nueva_contrasena:
                guardar_usuario(nuevo_usuario, nueva_contrasena)
            else:
                st.warning("⚠️ Debes ingresar todos los campos.")
        st.divider()
        st.markdown("### Lista de usuarios registrados")
        st.dataframe(cargar_usuarios(), use_container_width=True)

    # ---- CERRAR SESIÓN ----
    elif menu == "🚪 Cerrar Sesión":
        st.session_state.clear()
        st.rerun()

# ---------------- FLUJO PRINCIPAL ----------------
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    login()
else:
    panel_principal()
