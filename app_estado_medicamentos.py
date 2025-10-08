import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
import re
import time

# Google Drive
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.oauth2.service_account import Credentials
from io import BytesIO

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# ---------------- GOOGLE DRIVE ----------------
SERVICE_JSON = "streamlit-drive-app.json"  # Pon aquí el nombre exacto de tu JSON
gauth = GoogleAuth()
gauth.credentials = Credentials.from_service_account_file(SERVICE_JSON)
drive = GoogleDrive(gauth)

# Carpeta en Drive donde guardar los archivos (crea una carpeta y pon su ID)
DRIVE_FOLDER_ID = "TU_FOLDER_ID_AQUI"

# ---------------- FUNCIONES DRIVE ----------------
def subir_archivo_drive(nombre_archivo, archivo_bytes):
    """Sube un archivo (BytesIO) a la carpeta de Drive"""
    file_drive = drive.CreateFile({'title': nombre_archivo, 'parents':[{'id': DRIVE_FOLDER_ID}]})
    file_drive.SetContentString(archivo_bytes.decode() if isinstance(archivo_bytes, bytes) else archivo_bytes)
    file_drive.Upload()
    return file_drive['id']

def descargar_csv_drive(file_id):
    file_drive = drive.CreateFile({'id': file_id})
    file_drive.GetContentFile("tmp.csv")
    return pd.read_csv("tmp.csv")

# ---------------- FUNCIONES ----------------
def nombre_valido_archivo(nombre):
    nombre = nombre.upper().replace(' ', '_')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre

def obtener_consecutivo(df):
    if df.empty:
        return 1
    else:
        return int(df["Consecutivo"].max()) + 1

# ---------------- SESIÓN ----------------
st.sidebar.header("🔐 Inicio de sesión")
if "usuario" in st.session_state:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.success("Sesión cerrada. Recarga la página para iniciar de nuevo.")
else:
    usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        # Aquí deberías cargar usuarios desde un CSV en Drive o archivo local
        st.session_state["usuario"] = usuario_input
        st.success(f"Bienvenido {usuario_input}")

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    
    # Cargar CSV desde Drive si existe
    try:
        # Busca archivo CSV en la carpeta Drive
        file_list = drive.ListFile({'q': f"'{DRIVE_FOLDER_ID}' in parents and trashed=false and title='registros_medicamentos.csv'"}).GetList()
        if file_list:
            df_registros = pd.read_csv(BytesIO(file_list[0].GetContentString().encode()))
        else:
            df_registros = pd.DataFrame(columns=["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                                                 "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"])
    except:
        df_registros = pd.DataFrame(columns=["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                                             "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"])

    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])

    # -------- TAB REGISTRO --------
    with tabs[0]:
        consecutivo = obtener_consecutivo(df_registros)
        estado = st.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"], index=0)
        plu = st.text_input("PLU").upper()
        codigo_gen_default = plu.split("_")[0] if "_" in plu else ""
        codigo_gen = st.text_input("Código genérico", value=codigo_gen_default).upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])
        st.date_input("Fecha", value=datetime.now(), disabled=True)

        if st.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif soporte_file is None:
                st.warning("Debes subir un PDF")
            else:
                # Guardar PDF en Drive
                pdf_nombre = f"{consecutivo}_{nombre_valido_archivo(nombre)}.pdf"
                archivo_bytes = BytesIO(soporte_file.getbuffer())
                file_drive = drive.CreateFile({'title': pdf_nombre, 'parents':[{'id': DRIVE_FOLDER_ID}]})
                file_drive.SetContentFile(archivo_bytes)
                file_drive.Upload()
                
                # Agregar registro
                new_row = pd.DataFrame([[consecutivo, usuario, estado, plu, codigo_gen,
                                         nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"), pdf_nombre]],
                                       columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                
                # Guardar CSV actualizado en Drive
                csv_buffer = BytesIO()
                df_registros.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                file_drive_csv = drive.CreateFile({'title':'registros_medicamentos.csv','parents':[{'id': DRIVE_FOLDER_ID}]})
                file_drive_csv.SetContentString(csv_buffer.getvalue().decode())
                file_drive_csv.Upload()
                
                st.success("✅ Registro guardado y PDF subido a Drive")

