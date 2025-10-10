import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Control de Estado de Medicamentos 💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CONFIGURACIÓN DE ARCHIVOS ----------------
BASE_DIR = os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
USUARIOS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")

# Crear carpetas necesarias
os.makedirs(SOPORTES_DIR, exist_ok=True)

# ---------------- VALIDACIÓN ARCHIVO DE USUARIOS ----------------
if not os.path.exists(USUARIOS_FILE):
    pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USUARIOS_FILE, index=False)

usuarios = pd.read_csv(USUARIOS_FILE)
usuarios.columns = usuarios.columns.str.lower().str.strip().str.replace("ñ", "n")

if "usuario" not in usuarios.columns or "contrasena" not in usuarios.columns or usuarios.empty:
    pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USUARIOS_FILE, index=False)
    usuarios = pd.read_csv(USUARIOS_FILE)

# ---------------- FUNCIONES ----------------
def guardar_registro(data, soporte_file):
    df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()

    # Guardar archivo soporte
    if soporte_file:
        file_path = os.path.join(SOPORTES_DIR, soporte_file.name)
        with open(file_path, "wb") as f:
            f.write(soporte_file.getbuffer())
        data["soporte"] = file_path
    else:
        st.warning("Debe subir un soporte en PDF para guardar el registro.")
        return

    # Agregar registro
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ Registro guardado exitosamente.")


def descargar_soporte(ruta):
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            return f.read()
    else:
        return None


def login():
    st.title("💊 Control de Estado de Medicamentos")
    st.subheader("Inicio de Sesión")

    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if ((usuarios["usuario"] == usuario) & (usuarios["contrasena"] == contraseña)).any():
            st.session_state["usuario_autenticado"] = usuario
            st.experimental_rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos.")


def app_principal():
    st.sidebar.title(f"Bienvenido, {st.session_state['usuario_autenticado']} 👋")
    menu = st.sidebar.radio(
        "Menú",
        ["📋 Registrar Medicamento", "📂 Registros Guardados", "👤 Administración de Usuarios"]
    )

    if menu == "📋 Registrar Medicamento":
        st.header("📋 Registro de Medicamentos")

        estado = st.selectbox(
            "Selecciona el estado del medicamento",
            ["AGOTADO", "DESABASTECIDO", "DESCONTINUADO"]
        )

        explicaciones = {
            "AGOTADO": "El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado.",
            "DESABASTECIDO": "El medicamento no está disponible ni en el inventario interno ni en el mercado por un tiempo prolongado.",
            "DESCONTINUADO": "El medicamento ha sido retirado permanentemente del mercado o del portafolio del proveedor."
        }
        st.info(explicaciones[estado])

        plu = st.text_input("PLU")
        codigo_generico = ""
        if "_" in plu:
            codigo_generico = plu.split("_")[0]

        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del Medicamento")
        with col2:
            laboratorio = st.text_input("Laboratorio")

        fecha_ingreso = datetime.now().strftime("%Y-%m-%d")
        st.date_input("Fecha de ingreso", datetime.strptime(fecha_ingreso, "%Y-%m-%d"), disabled=True)

        soporte_file = st.file_uploader("📎 Subir soporte (solo PDF)", type=["pdf"])
        if not soporte_file:
            st.warning("⚠️ Debe subir un soporte para poder guardar el registro.")

        if st.button("💾 Guardar Registro"):
            if all([estado, plu, nombre, laboratorio, soporte_file]):
                data = {
                    "fecha": fecha_ingreso,
                    "estado": estado,
                    "plu": plu,
                    "codigo_generico": codigo_generico,
                    "nombre": nombre,
                    "laboratorio": laboratorio,
                    "usuario": st.session_state["usuario_autenticado"]
                }
                guardar_registro(data, soporte_file)
            else:
                st.error("❌ Por favor complete todos los campos y suba el soporte.")

    elif menu == "📂 Registros Guardados":
        st.header("📂 Registros Guardados")
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            st.dataframe(df)

            for i, row in df.iterrows():
                ruta = row.get("soporte", "")
                if os.path.exists(ruta):
                    with open(ruta, "rb") as f:
                        btn = st.download_button(
                            label=f"⬇️ Descargar soporte - {row['nombre']}",
                            data=f.read(),
                            file_name=os.path.basename(ruta),
                            mime="application/pdf"
                        )
        else:
            st.info("No hay registros guardados aún.")

    elif menu == "👤 Administración de Usuarios":
        st.header("👤 Administración de Usuarios")
        st.write("Crea nuevos usuarios para el sistema.")

        nuevo_usuario = st.text_input("Nuevo usuario")
        nueva_contrasena = st.text_input("Nueva contraseña", type="password")

        if st.button("➕ Crear usuario"):
            usuarios_df = pd.read_csv(USUARIOS_FILE)
            if nuevo_usuario in usuarios_df["usuario"].values:
                st.warning("⚠️ Ese usuario ya existe.")
            else:
                nuevo = pd.DataFrame({"usuario": [nuevo_usuario], "contrasena": [nueva_contrasena]})
                usuarios_df = pd.concat([usuarios_df, nuevo], ignore_index=True)
                usuarios_df.to_csv(USUARIOS_FILE, index=False)
                st.success(f"✅ Usuario '{nuevo_usuario}' creado exitosamente.")


# ==============================
# EJECUCIÓN DE LA APLICACIÓN
# ==============================
if "usuario_autenticado" not in st.session_state:
    login()
else:
    app_principal()

