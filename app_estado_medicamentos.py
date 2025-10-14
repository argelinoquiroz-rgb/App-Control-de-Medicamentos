import streamlit as st
import pandas as pd
import json
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from datetime import datetime

# ------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------
st.set_page_config(page_title="Control de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ------------------------------------------------------------
# GOOGLE DRIVE SETTINGS
# ------------------------------------------------------------
GOOGLE_DRIVE_FOLDER_ID = "1itzZF2zLNLmGEDm-ok8FD_rhadaIUM_Z"  # Carpeta de destino
SERVICE_ACCOUNT_FILE = "service_account.json"

# Guardar credenciales desde st.secrets si estás en Streamlit Cloud
if "service_account" in st.secrets:
    creds = dict(st.secrets["service_account"])
    with open(SERVICE_ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------
# FUNCIÓN: Verificar credenciales
# ------------------------------------------------------------
def verificar_credenciales():
    """Verifica que el archivo JSON de la cuenta de servicio exista y esté bien formado."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"❌ Archivo de credenciales no encontrado: {SERVICE_ACCOUNT_FILE}")
        st.stop()

    try:
        with open(SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ["type", "client_email", "private_key", "token_uri"]:
            if key not in data:
                st.error(f"❌ Falta la clave requerida '{key}' en el JSON de credenciales.")
                st.stop()
    except Exception as e:
        st.error(f"❌ Error al leer credenciales: {e}")
        st.stop()


# ------------------------------------------------------------
# FUNCIÓN: Autenticación con Google Drive
# ------------------------------------------------------------
def authenticate_drive():
    """Autentica con Google Drive usando una cuenta de servicio."""
    verificar_credenciales()

    try:
        gauth = GoogleAuth(settings={
            "client_config_backend": "service",
            "service_config_file": SERVICE_ACCOUNT_FILE,
            "oauth_scope": ["https://www.googleapis.com/auth/drive"]
        })
        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)
        return drive
    except Exception as e:
        st.error(f"⚠️ Error de autenticación con Google Drive: {e}")
        st.stop()


# ------------------------------------------------------------
# FUNCIÓN: Subir archivo a Google Drive
# ------------------------------------------------------------
def upload_to_drive(file_path, file_name):
    """Sube un archivo a Google Drive dentro de la carpeta especificada."""
    try:
        drive = authenticate_drive()
        gfile = drive.CreateFile({
            "title": file_name,
            "parents": [{"id": GOOGLE_DRIVE_FOLDER_ID}]
        })
        gfile.SetContentFile(file_path)
        gfile.Upload()
        st.success(f"✅ Archivo '{file_name}' subido exitosamente a Google Drive.")
    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Drive: {e}")


# ------------------------------------------------------------
# FUNCIÓN: Página principal de registro
# ------------------------------------------------------------
def page_registrar():
    st.header("📋 Registrar estado de medicamento")

    with st.form("registro_form"):
        nombre_medicamento = st.text_input("Nombre del medicamento")
        estado = st.selectbox("Estado", ["Disponible", "Agotado", "Desabastecido", "Descontinuado"])
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        submitted = st.form_submit_button("Guardar registro")

        if submitted:
            if not nombre_medicamento.strip():
                st.warning("Por favor, ingresa el nombre del medicamento.")
                return

            # Crear dataframe con los datos
            data = pd.DataFrame([{
                "Medicamento": nombre_medicamento,
                "Estado": estado,
                "Fecha Registro": fecha_actual
            }])

            # Guardar localmente
            archivo_csv = "registro_medicamentos.csv"
            if os.path.exists(archivo_csv):
                df_existente = pd.read_csv(archivo_csv)
                df_final = pd.concat([df_existente, data], ignore_index=True)
            else:
                df_final = data
            df_final.to_csv(archivo_csv, index=False, encoding="utf-8-sig")

            # Subir a Google Drive
            upload_to_drive(archivo_csv, archivo_csv)


# ------------------------------------------------------------
# FUNCIÓN: Ver registros guardados
# ------------------------------------------------------------
def page_registros():
    st.header("📁 Registros guardados")

    archivo_csv = "registro_medicamentos.csv"
    if not os.path.exists(archivo_csv):
        st.info("No hay registros guardados aún.")
        return

    df = pd.read_csv(archivo_csv)
    st.dataframe(df, use_container_width=True)


# ------------------------------------------------------------
# MENÚ PRINCIPAL
# ------------------------------------------------------------
menu = st.sidebar.radio("Menú", ["Registrar medicamento", "Ver registros"])

if menu == "Registrar medicamento":
    page_registrar()
else:
    page_registros()
