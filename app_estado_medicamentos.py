import streamlit as st
import pandas as pd
import json
import tempfile
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from io import BytesIO

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ==============================
# RUTA DEL ARCHIVO DE USUARIOS
# ==============================
USERS_FILE = "usuarios.csv"

# ==============================
# CARGAR CREDENCIALES DE GOOGLE
# ==============================
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
except Exception as e:
    st.error("❌ No se pudo cargar 'google_credentials' desde st.secrets. Verifica que esté correctamente configurado.")
    st.stop()

# Crear archivo temporal
with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
    json.dump(creds_dict, tmpfile)
    SERVICE_FILE = tmpfile.name

# AUTENTICACIÓN CUENTA DE SERVICIO
try:
    gauth = GoogleAuth()
    gauth.LoadServiceConfig()  # ⚠️ asegúrate de usar LoadServiceConfig sin argumentos
    gauth.ServiceAuth()        # autentica la cuenta de servicio
    drive = GoogleDrive(gauth)
    st.success("✅ Conexión exitosa con Google Drive mediante cuenta de servicio.")
except Exception as e:
    st.error(f"❌ Error autenticando con la cuenta de servicio: {e}")
    st.stop()

# ==============================
# FUNCIONES DE LOGIN Y REGISTRO
# ==============================
def cargar_usuarios():
    if os.path.exists(USERS_FILE):
        df = pd.read_csv(USERS_FILE)
        df.columns = df.columns.str.strip().str.lower()
        return df
    else:
        return pd.DataFrame(columns=["usuario", "password"])

def guardar_usuario(usuario, password):
    df = cargar_usuarios()
    if usuario.lower() in df["usuario"].str.lower().values:
        st.warning("⚠️ El usuario ya existe.")
        return False
    nuevo = pd.DataFrame({"usuario":[usuario], "password":[password]})
    df = pd.concat([df, nuevo], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    st.success(f"✅ Usuario '{usuario}' registrado correctamente.")
    return True

# ==============================
# PANTALLA DE LOGIN/REGISTRO
# ==============================
st.subheader("🔐 Inicio de sesión")

opcion = st.radio("¿Qué deseas hacer?", ["Iniciar sesión", "Registrar nuevo usuario"])

username = st.text_input("Usuario")
password = st.text_input("Contraseña", type="password")

usuarios_df = cargar_usuarios()

if st.button("Aceptar"):
    if opcion == "Iniciar sesión":
        user_row = usuarios_df[
            (usuarios_df["usuario"].str.lower() == username.strip().lower()) &
            (usuarios_df["password"] == password.strip())
        ]
        if not user_row.empty:
            st.success(f"✅ Bienvenido, {username}!")
            st.session_state["usuario"] = username
        else:
            st.error("❌ Usuario o contraseña incorrectos.")
    elif opcion == "Registrar nuevo usuario":
        if username.strip() == "" or password.strip() == "":
            st.warning("⚠️ Debes ingresar usuario y contraseña.")
        else:
            guardar_usuario(username.strip(), password.strip())

# ==============================
# CONTENIDO SOLO PARA USUARIOS LOGUEADOS
# ==============================
if "usuario" in st.session_state:
    st.subheader(f"👋 Hola {st.session_state['usuario']}, puedes administrar tus archivos en Drive")

    # Entrada de ID de carpeta
    carpeta_id = st.text_input("🔑 Ingresa el ID de la carpeta en Google Drive:", "")

    if carpeta_id:
        st.info(f"📂 Buscando archivos dentro de la carpeta con ID: `{carpeta_id}`")
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
                    col1, col2, col3 = st.columns([4,2,2])
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
                            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al listar archivos: {e}")

    # Subir archivo
    st.subheader("📤 Subir un nuevo archivo")
    uploaded_file = st.file_uploader("Selecciona un archivo para subir a Google Drive:", type=None)
    if uploaded_file and carpeta_id:
        try:
            gfile = drive.CreateFile({'title': uploaded_file.name, 'parents':[{'id': carpeta_id}]})
            gfile.SetContentBytes(uploaded_file.getvalue())
            gfile.Upload()
            st.success(f"✅ Archivo '{uploaded_file.name}' subido correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al subir el archivo: {e}")
    elif uploaded_file and not carpeta_id:
        st.warning("⚠️ Debes ingresar primero un ID de carpeta antes de subir un archivo.")
