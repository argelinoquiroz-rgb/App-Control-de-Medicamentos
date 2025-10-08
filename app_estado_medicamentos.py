import streamlit as st
import pandas as pd
import re
import hashlib
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import io
import base64
import os

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# ---------------- AUTENTICACIÓN CON DRIVE ----------------
SERVICE_JSON = "psychic-fin-456901-t8-aaef9c7badb0.JSON"  # Tu JSON
FOLDER_ID = "1AzQrHdxkkdWYnKbu0zLeIeM8jgXbMCZF"  # Carpeta de Drive

gauth = GoogleAuth()
gauth.ServiceAuthSettings = {
    "client_config_file": SERVICE_JSON,
    "save_credentials": True,
    "save_credentials_backend": "file",
    "save_credentials_file": "credentials.json"
}
gauth.ServiceAuth()
drive = GoogleDrive(gauth)

# ---------------- FUNCIONES DRIVE ----------------
def upload_pdf_to_drive(file_buffer, file_name):
    file_drive = drive.CreateFile({'title': file_name, 'parents': [{'id': FOLDER_ID}]})
    file_drive.SetContentString(file_buffer.getvalue().decode("latin-1"))
    file_drive.Upload()
    return file_drive['id']

def upload_csv_to_drive(df, file_name):
    file_drive = drive.CreateFile({'title': file_name, 'parents': [{'id': FOLDER_ID}]})
    file_drive.SetContentString(df.to_csv(index=False))
    file_drive.Upload()
    return file_drive['id']

def download_file_from_drive(file_id):
    file_drive = drive.CreateFile({'id': file_id})
    file_drive.FetchMetadata()
    return file_drive.GetContentString()

# ---------------- VARIABLES ----------------
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "SoporteID", "SoporteNombre"]

CSV_NAME = "registros_medicamentos.csv"

# ---------------- CARGAR O CREAR REGISTROS ----------------
try:
    csv_content = download_file_from_drive(CSV_NAME)
    df_registros = pd.read_csv(io.StringIO(csv_content))
except:
    df_registros = pd.DataFrame(columns=expected_columns)
    upload_csv_to_drive(df_registros, CSV_NAME)

# ---------------- FUNCIONES AUXILIARES ----------------
def save_registros_drive(df):
    upload_csv_to_drive(df, CSV_NAME)

def limpiar_formulario():
    for key in ["estado","plu","codigo_generico","nombre_medicamento","laboratorio","soporte_file","ultimo_pdf_id","ultimo_pdf_name"]:
        if key in st.session_state:
            del st.session_state[key]

def nombre_valido_archivo(nombre):
    nombre = nombre.upper().replace(' ', '_')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre

def obtener_consecutivo():
    if df_registros.empty:
        return 1
    else:
        return int(df_registros["Consecutivo"].max()) + 1

def mostrar_pdf_drive(file_id, file_name):
    key_hash = hashlib.md5(file_id.encode()).hexdigest()
    st.markdown(f'<a href="https://drive.google.com/uc?id={file_id}" target="_blank">📄 Abrir PDF</a>', unsafe_allow_html=True)
    file_drive = drive.CreateFile({'id': file_id})
    file_buffer = io.BytesIO(file_drive.GetContentBinary())
    st.download_button(
        label="📥 Descargar PDF",
        data=file_buffer,
        file_name=file_name,
        mime="application/pdf",
        key=f"download_{key_hash}"
    )

def descargar_csv(df):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    st.markdown(f'<a href="data:file/csv;base64,{b64}" download="consolidado_medicamentos.csv">📥 Descargar CSV consolidado</a>', unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# Usuarios locales
USERS_FILE_LOCAL = "usuarios.csv"
if os.path.exists(USERS_FILE_LOCAL):
    df_usuarios = pd.read_csv(USERS_FILE_LOCAL)
else:
    df_usuarios = pd.DataFrame([{"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}])
    df_usuarios.to_csv(USERS_FILE_LOCAL, index=False)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

# Login
usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
contrasena_input = st.sidebar.text_input("Contraseña", type="password")

if st.sidebar.button("Ingresar"):
    if usuario_input in df_usuarios["usuario"].values:
        stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
        if contrasena_input == stored_pass:
            st.session_state["usuario"] = usuario_input
        else:
            st.sidebar.error("Contraseña incorrecta")
    else:
        st.sidebar.error("Usuario no registrado")

# Crear usuario
st.sidebar.markdown("---")
st.sidebar.markdown("### Crear nuevo usuario")
nombre_usuario_nuevo = st.sidebar.text_input("Usuario (nombre.apellido)", key="usuario_nuevo").strip().lower()
correo_nuevo = st.sidebar.text_input("Correo electrónico", key="correo_nuevo").strip().lower()
contrasena_nueva = st.sidebar.text_input("Contraseña", type="password", key="pass_nueva")
if st.sidebar.button("Crear usuario"):
    if not correo_nuevo or not contrasena_nueva or not nombre_usuario_nuevo:
        st.sidebar.error("Debes ingresar usuario, correo y contraseña")
    elif not correo_nuevo.endswith("@pharmaser.com.co"):
        st.sidebar.error("El correo debe terminar en @pharmaser.com.co")
    elif correo_nuevo in df_usuarios["correo"].values:
        st.sidebar.error("Este correo ya está registrado")
    elif nombre_usuario_nuevo in df_usuarios["usuario"].values:
        st.sidebar.error("Este usuario ya existe")
    else:
        df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{
            "usuario": nombre_usuario_nuevo,
            "contrasena": contrasena_nueva,
            "correo": correo_nuevo
        }])], ignore_index=True)
        df_usuarios.to_csv(USERS_FILE_LOCAL, index=False)
        st.sidebar.success(f"Usuario creado: {nombre_usuario_nuevo}")

# ---------------- INTERFAZ ----------------
if st.session_state["usuario"]:
    usuario = st.session_state["usuario"]
    st.sidebar.success(f"Sesión iniciada: {usuario}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["usuario"] = None
        st.experimental_rerun()

    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento", "Consolidado general", "Buscar registro"])

    # -------- TAB REGISTRO --------
    with tabs[0]:
        consecutivo = obtener_consecutivo()
        estado = st.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"], index=0, key="estado")
        plu = st.text_input("PLU", key="plu").upper()
        codigo_gen_default = plu.split("_")[0] if "_" in plu else ""
        codigo_gen = st.text_input("Código genérico", value=codigo_gen_default, key="codigo_generico").upper()
        nombre = st.text_input("Nombre del medicamento", key="nombre_medicamento").upper()
        laboratorio = st.text_input("Laboratorio", key="laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"], key="soporte_file")
        st.date_input("Fecha", value=datetime.now(), disabled=True)

        if soporte_file and nombre.strip():
            nombre_pdf = f"{consecutivo}_{usuario}_{re.sub(r'[^A-Za-z0-9_]', '', nombre.upper())}.pdf"
            pdf_id = upload_pdf_to_drive(soporte_file, nombre_pdf)
            st.session_state["ultimo_pdf_id"] = pdf_id
            st.session_state["ultimo_pdf_name"] = nombre_pdf
            st.success("PDF subido a Drive ✅")

        if "ultimo_pdf_id" in st.session_state:
            if st.button("Mostrar / Descargar PDF"):
                mostrar_pdf_drive(st.session_state["ultimo_pdf_id"], st.session_state["ultimo_pdf_name"])

        col1, col2 = st.columns([1,1])
        if col1.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif "ultimo_pdf_id" not in st.session_state:
                st.warning("Debes subir un PDF")
            else:
                new_row = pd.DataFrame([[
                    consecutivo, usuario, estado, plu, codigo_gen,
                    nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"),
                    st.session_state["ultimo_pdf_id"],
                    st.session_state["ultimo_pdf_name"]
                ]], columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                save_registros_drive(df_registros)
                st.success("✅ Registro guardado en Drive")
                limpiar_formulario()

        if col2.button("🧹 Limpiar formulario"):
            limpiar_formulario()
            st.success("Formulario limpiado ✅")

    # -------- TAB CONSOLIDADO --------
    with tabs[1]:
        st.dataframe(df_registros)
