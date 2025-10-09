import streamlit as st
import pandas as pd
import json
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from io import BytesIO

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ==============================
# LOGIN DE USUARIO
# ==============================
USERS = {
    "admin": "1234",
    "usuario1": "abcd",
    # Agrega más usuarios si es necesario
}

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.subheader("🔑 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if username in USERS and USERS[username] == password:
            st.session_state.login = True
            st.session_state.user = username
            st.success(f"Bienvenido {username}")
            st.experimental_rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
else:
    st.write(f"✅ Usuario autenticado: **{st.session_state.user}**")

    # ==============================
    # CARGAR CREDENCIALES DE GOOGLE DRIVE
    # ==============================
    try:
        creds_dict = json.loads(st.secrets["google_credentials"])
    except Exception as e:
        st.error("❌ No se pudo cargar 'google_credentials' desde st.secrets.")
        st.stop()

    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
        json.dump(creds_dict, tmpfile)
        SERVICE_FILE = tmpfile.name

    try:
        gauth = GoogleAuth()
        gauth.LoadServiceConfigFile(SERVICE_FILE)  # ⚡ Autenticación correcta con pydrive2
        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)
        st.success("✅ Conexión exitosa con Google Drive mediante cuenta de servicio.")
    except Exception as e:
        st.error(f"❌ Error autenticando con la cuenta de servicio: {e}")
        st.stop()

    # ==============================
    # CONFIGURACIÓN DE CARPETA EN DRIVE
    # ==============================
    st.subheader("📁 Configuración de carpeta")
    carpeta_id = st.text_input("🔑 Ingresa el ID de la carpeta en Google Drive:", "")

    if carpeta_id:
        st.info(f"📂 Buscando archivos en carpeta ID: `{carpeta_id}`")
        try:
            query = f"'{carpeta_id}' in parents and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()

            if not file_list:
                st.warning("⚠️ No se encontraron archivos en esta carpeta.")
            else:
                st.subheader("📄 Archivos encontrados:")
                for file in file_list:
                    file_title = file['title']
                    file_id = file['id']

                    col1, col2, col3 = st.columns([4, 2, 2])
                    with col1:
                        st.write(f"📘 **{file_title}** (ID: `{file_id}`)")
                    with col2:
                        if st.button(f"⬇️ Descargar {file_title}", key=file_id):
                            downloaded = drive.CreateFile({'id': file_id})
                            downloaded.GetContentFile(file_title)
                            with open(file_title, "rb") as f:
                                st.download_button(
                                    label=f"Descargar {file_title}",
                                    data=f,
                                    file_name=file_title,
                                    mime="application/octet-stream"
                                )
                    with col3:
                        if st.button(f"🗑️ Eliminar {file_title}", key=f"del_{file_id}"):
                            downloaded = drive.CreateFile({'id': file_id})
                            downloaded.Delete()
                            st.warning(f"🗑️ Archivo **{file_title}** eliminado.")
                            st.experimental_rerun()

        except Exception as e:
            st.error(f"❌ Error al listar archivos: {e}")

        # ==============================
        # SUBIR NUEVO ARCHIVO
        # ==============================
        st.subheader("📤 Subir un nuevo archivo")
        uploaded_file = st.file_uploader("Selecciona un archivo para subir a Google Drive:", type=None)

        if uploaded_file:
            try:
                gfile = drive.CreateFile({'title': uploaded_file.name, 'parents': [{'id': carpeta_id}]})
                gfile.SetContentBytes(uploaded_file.getvalue())
                gfile.Upload()
                st.success(f"✅ Archivo '{uploaded_file.name}' subido correctamente.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error al subir el archivo: {e}")
