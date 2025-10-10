import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO
import base64

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Control de Estado de Medicamentos",
    page_icon="💊",
    layout="wide"
)

# Crear carpetas necesarias
os.makedirs("soportes", exist_ok=True)
os.makedirs("assets", exist_ok=True)

# ==============================
# BASE DE DATOS LOCAL
# ==============================
DATA_FILE = "registros_medicamentos.csv"
USERS_FILE = "usuarios.csv"

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def cargar_usuarios():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    else:
        return pd.DataFrame(columns=["usuario", "contraseña"])

def guardar_usuario(usuario, contraseña):
    df = cargar_usuarios()
    if usuario in df["usuario"].values:
        st.warning("⚠️ El usuario ya existe.")
    else:
        nuevo = pd.DataFrame([[usuario, contraseña]], columns=["usuario", "contraseña"])
        df = pd.concat([df, nuevo], ignore_index=True)
        df.to_csv(USERS_FILE, index=False)
        st.success("✅ Usuario creado exitosamente.")

def cargar_datos():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Fecha", "PLU", "Código Genérico", "Nombre", "Estado", "Observaciones", "Soporte"])

def guardar_registro(data):
    df = cargar_datos()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def descargar_soporte(ruta):
    with open(ruta, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{os.path.basename(ruta)}">📄 Descargar Soporte</a>'
    return href

# ==============================
# LOGIN
# ==============================
def login():
    st.markdown("## 🔐 Inicio de Sesión")
    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        usuarios = cargar_usuarios()
        if ((usuarios["usuario"] == usuario) & (usuarios["contraseña"] == contraseña)).any():
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.success("Inicio de sesión exitoso ✅")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

# ==============================
# INTERFAZ PRINCIPAL
# ==============================
def app_principal():
    st.sidebar.markdown("### 💊 Control de Estado de Medicamentos")
    menu = st.sidebar.radio(
        "Navegación",
        ["Inicio", "Registrar Medicamento", "Registros Guardados", "Gestión de Usuarios"]
    )

    if menu == "Inicio":
        st.markdown("## 📋 Bienvenido al Sistema de Control de Medicamentos")
        st.write("Seleccione una opción en el panel lateral para comenzar.")

    elif menu == "Registrar Medicamento":
        st.markdown("## 🧾 Registrar Nuevo Medicamento")

        explicaciones_estado = {
            "Agotado": "El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado.",
            "Desabastecido": "No se encuentra disponible ni en el inventario interno ni en el mercado nacional.",
            "Descontinuado": "Ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria."
        }

        estado = st.selectbox("Estado", list(explicaciones_estado.keys()))
        st.info(explicaciones_estado[estado])

        plu = st.text_input("PLU")
        nombre = st.text_input("Nombre del Medicamento")
        observaciones = st.text_area("Observaciones")
        soporte = st.file_uploader("Subir soporte (obligatorio)", type=["pdf", "jpg", "png"])

        # Fecha del día (no editable)
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        st.write(f"📅 Fecha del registro: **{fecha_actual}**")

        # Código genérico automático
        codigo_generico = ""
        if "_" in plu:
            codigo_generico = plu.split("_")[0]
        st.text_input("Código Genérico", value=codigo_generico, disabled=True)

        if st.button("Guardar Registro"):
            if not soporte:
                st.error("❌ Debes subir un archivo de soporte antes de guardar.")
            else:
                ruta_soporte = os.path.join("soportes", soporte.name)
                with open(ruta_soporte, "wb") as f:
                    f.write(soporte.getbuffer())

                data = {
                    "Fecha": fecha_actual,
                    "PLU": plu,
                    "Código Genérico": codigo_generico,
                    "Nombre": nombre,
                    "Estado": estado,
                    "Observaciones": observaciones,
                    "Soporte": ruta_soporte
                }
                guardar_registro(data)
                st.success("✅ Registro guardado correctamente.")

    elif menu == "Registros Guardados":
        st.markdown("## 📚 Registros Guardados")
        df = cargar_datos()
        if df.empty:
            st.info("No hay registros guardados aún.")
        else:
            for i, row in df.iterrows():
                st.markdown(f"""
                **Fecha:** {row['Fecha']}  
                **PLU:** {row['PLU']}  
                **Código Genérico:** {row['Código Genérico']}  
                **Nombre:** {row['Nombre']}  
                **Estado:** {row['Estado']}  
                **Observaciones:** {row['Observaciones']}  
                {descargar_soporte(row['Soporte'])}
                """)
                st.markdown("---")

    elif menu == "Gestión de Usuarios":
        st.markdown("## 👤 Gestión de Usuarios")
        st.subheader("Crear nuevo usuario")
        nuevo_usuario = st.text_input("Nuevo usuario")
        nueva_contraseña = st.text_input("Contraseña", type="password")
        if st.button("Crear usuario"):
            guardar_usuario(nuevo_usuario, nueva_contraseña)

# ==============================
# EJECUCIÓN
# ==============================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
else:
    app_principal()

