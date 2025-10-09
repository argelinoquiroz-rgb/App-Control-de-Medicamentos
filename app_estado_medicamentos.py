import streamlit as st
import pandas as pd
import json
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ==================================
# LOGIN DE USUARIOS
# ==================================
try:
    usuarios_df = pd.read_csv("usuarios.csv")
    if "usuario" not in usuarios_df.columns or "contrasena" not in usuarios_df.columns:
        st.error("❌ Columnas 'usuario' o 'contrasena' no encontradas en usuarios.csv")
        st.stop()
except FileNotFoundError:
    st.error("❌ Archivo usuarios.csv no encontrado")
    st.stop()

with st.form("login_form"):
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    submit = st.form_submit_button("Iniciar sesión")

if submit:
    user_row = usuarios_df[(usuarios_df["usuario"] == username) & (usuarios_df["contrasena"] == password)]
    if user_row.empty:
        st.error("❌ Usuario o contraseña incorrectos")
        st.stop()
    else:
        st.success(f"✅ Bienvenido {username}")

# ==================================
# CONEXIÓN A GOOGLE DRIVE
# ==================================
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
except Exception as e:
    st.error("❌ No se pudo cargar 'google_credentials' desde st.secrets")
    st.stop()

with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
    json.dump(creds_dict, tmpfile)
    SERVICE_FILE = tmpfile.name

try:
    gauth = GoogleAuth()
    gauth.LoadServiceConfigFile = SERVICE_FILE  # Método correcto para PyDrive2 reciente
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    st.success("✅ Conexión exitosa con Google Drive mediante cuenta de servicio.")
except Exception as e:
    st.error(f"❌ Error autenticando con la cuenta de servicio: {e}")
    st.stop()

# ==================================
# CONFIGURACIÓN DE CARPETA EN DRIVE
# ==================================
st.subheader("📁 Configuración de carpeta")
carpeta_id = st.text_input("🔑 Ingresa el ID de la carpeta en Google Drive:")

file_list = []
if carpeta_id:
    try:
        query = f"'{carpeta_id}' in parents and trashed=false"
        file_list = drive.ListFile({'q': query}).GetList()
    except Exception as e:
        st.error(f"❌ Error al listar archivos: {e}")
        file_list = []

if file_list:
    st.subheader("📄 Archivos encontrados:")
    for file in file_list:
        file_title = file['title']
        file_id = file['id']
        col1, col2, col3 = st.columns([4,2,2])
        with col1:
            st.write(f"📘 **{file_title}** (ID: `{file_id}`)")
        with col2:
            if st.button(f"⬇️ Descargar {file_title}", key=file_id):
                try:
                    downloaded = drive.CreateFile({'id': file_id})
                    downloaded.GetContentFile(file_title)
                    with open(file_title, "rb") as f:
                        st.download_button(label=f"Descargar {file_title}", data=f, file_name=file_title)
                except Exception as e:
                    st.error(f"❌ Error descargando el archivo: {e}")
        with col3:
            if st.button(f"🗑️ Eliminar {file_title}", key=f"del_{file_id}"):
                try:
                    to_delete = drive.CreateFile({'id': file_id})
                    to_delete.Delete()
                    st.warning(f"🗑️ Archivo **{file_title}** eliminado.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando el archivo: {e}")

# ==================================
# SUBIR NUEVO ARCHIVO
# ==================================
st.subheader("📤 Subir un nuevo archivo")
uploaded_file = st.file_uploader("Selecciona un archivo para subir a Google Drive:", type=None)

if uploaded_file and carpeta_id:
    try:
        gfile = drive.CreateFile({'title': uploaded_file.name, 'parents':[{'id': carpeta_id}]})
        gfile.SetContentBytes(uploaded_file.getvalue())
        gfile.Upload()
        st.success(f"✅ Archivo '{uploaded_file.name}' subido correctamente a la carpeta seleccionada.")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"❌ Error al subir el archivo: {e}")
elif uploaded_file and not carpeta_id:
    st.warning("⚠️ Debes ingresar primero un ID de carpeta antes de subir un archivo.")
