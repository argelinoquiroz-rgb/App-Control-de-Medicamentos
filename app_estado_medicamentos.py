import streamlit as st
import pandas as pd
import re
import hashlib
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import io
import base64
import json
import os

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# ---------------- AUTENTICACIÓN DRIVE ----------------
# Cargar credenciales desde Streamlit Secrets
if "google_credentials" not in st.secrets:
    st.error("❌ No se encontraron credenciales en st.secrets. Configura 'google_credentials' en la pestaña Secrets.")
    st.stop()

# Guardar temporalmente las credenciales en un archivo
SERVICE_FILE = "service_account.json"
with open(SERVICE_FILE, "w") as f:
    json.dump(dict(st.secrets["google_credentials"]), f)

gauth = GoogleAuth()
gauth.LoadServiceConfigSettings()
gauth.LoadCredentialsFile(SERVICE_FILE)
gauth.ServiceAuth()
drive = GoogleDrive(gauth)

FOLDER_ID = "1AzQrHdxkkdWYnKbu0zLeIeM8jgXbMCZF"
CSV_NAME = "registros_medicamentos.csv"

# ---------------- FUNCIONES DRIVE ----------------
def upload_pdf_to_drive(file_buffer, file_name):
    file_drive = drive.CreateFile({'title': file_name, 'parents': [{'id': FOLDER_ID}]})
    file_drive.SetContentFile(file_buffer.name)
    file_drive.Upload()
    return file_drive['id']

def upload_csv_to_drive(df, file_name):
    csv_data = df.to_csv(index=False)
    file_drive = drive.CreateFile({'title': file_name, 'parents': [{'id': FOLDER_ID}]})
    file_drive.SetContentString(csv_data)
    file_drive.Upload()
    return file_drive['id']

def get_file_id_by_name(file_name):
    query = f"'{FOLDER_ID}' in parents and title='{file_name}' and trashed=false"
    files = drive.ListFile({'q': query}).GetList()
    if len(files) > 0:
        return files[0]['id']
    return None

def download_file_from_drive(file_id):
    file_drive = drive.CreateFile({'id': file_id})
    return file_drive.GetContentString()

# ---------------- CARGAR CSV ----------------
file_id = get_file_id_by_name(CSV_NAME)
if file_id:
    csv_content = download_file_from_drive(file_id)
    df_registros = pd.read_csv(io.StringIO(csv_content))
else:
    df_registros = pd.DataFrame(columns=[
        "Consecutivo","Usuario","Estado","PLU","Código Genérico",
        "Nombre Medicamento","Laboratorio","Fecha","SoporteID","SoporteNombre"
    ])
    upload_csv_to_drive(df_registros, CSV_NAME)

# ---------------- FUNCIONES AUXILIARES ----------------
def save_registros_drive(df):
    existing_id = get_file_id_by_name(CSV_NAME)
    if existing_id:
        file_drive = drive.CreateFile({'id': existing_id})
        file_drive.SetContentString(df.to_csv(index=False))
        file_drive.Upload()
    else:
        upload_csv_to_drive(df, CSV_NAME)

def limpiar_formulario():
    for key in ["estado","plu","codigo_generico","nombre_medicamento","laboratorio","soporte_file","ultimo_pdf_id","ultimo_pdf_name"]:
        if key in st.session_state:
            del st.session_state[key]

def obtener_consecutivo():
    if df_registros.empty:
        return 1
    else:
        return int(df_registros["Consecutivo"].max()) + 1

# ---------------- LOGIN ----------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

USERS_FILE_LOCAL = "usuarios.csv"
if os.path.exists(USERS_FILE_LOCAL):
    df_usuarios = pd.read_csv(USERS_FILE_LOCAL)
else:
    df_usuarios = pd.DataFrame([{"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}])
    df_usuarios.to_csv(USERS_FILE_LOCAL, index=False)

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

# ---------------- INTERFAZ ----------------
if st.session_state["usuario"]:
    usuario = st.session_state["usuario"]
    st.sidebar.success(f"Sesión iniciada: {usuario}")
    st.markdown(f"### Hola, **{usuario}**")

    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])
    with tabs[0]:
        consecutivo = obtener_consecutivo()
        estado = st.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"], index=0)
        plu = st.text_input("PLU").upper()
        codigo_gen = st.text_input("Código genérico").upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])

        if soporte_file and nombre.strip():
            nombre_pdf = f"{consecutivo}_{usuario}_{re.sub(r'[^A-Za-z0-9_]', '', nombre.upper())}.pdf"
            pdf_id = upload_pdf_to_drive(soporte_file, nombre_pdf)
            st.session_state["ultimo_pdf_id"] = pdf_id
            st.session_state["ultimo_pdf_name"] = nombre_pdf
            st.success("PDF subido a Drive ✅")

        if st.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif "ultimo_pdf_id" not in st.session_state:
                st.warning("Debes subir un PDF")
            else:
                new_row = pd.DataFrame([[
                    consecutivo, usuario, estado, plu, codigo_gen,
                    nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"),
                    st.session_state["ultimo_pdf_id"], st.session_state["ultimo_pdf_name"]
                ]], columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                save_registros_drive(df_registros)
                st.success("✅ Registro guardado en Drive")
                limpiar_formulario()

    with tabs[1]:
        st.dataframe(df_registros)


