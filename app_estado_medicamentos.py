import streamlit as st
import pandas as pd
import json
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from io import BytesIO
import os

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ==============================
# ARCHIVO DE USUARIOS
# ==============================
USERS_FILE = "usuarios.csv"

# Crear archivo si no existe
if not os.path.exists(USERS_FILE):
    df = pd.DataFrame(columns=["usuario", "password", "rol"])
    # Crear usuario admin inicial
    df.loc[0] = ["admin", "1234", "admin"]
    df.to_csv(USERS_FILE, index=False)

# Cargar usuarios
usuarios_df = pd.read_csv(USERS_FILE)

# ==============================
# LOGIN DE USUARIO
# ==============================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = None
    st.session_state.rol = None

if not st.session_state.login:
    st.subheader("🔑 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        user_row = usuarios_df[(usuarios_df["usuario"] == username) & (usuarios_df["password"] == password)]
        if not user_row.empty:
            st.session_state.login = True
            st.session_state.user = username
            st.session_state.rol = user_row.iloc[0]["rol"]
            st.success(f"Bienvenido {username}")
            st.experimental_rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")
else:
    st.write(f"✅ Usuario autenticado: **{st.session_state.user}** (Rol: {st.session_state.rol})")

    # ==============================
    # REGISTRO DE NUEVOS USUARIOS (solo admin)
    # ==============================
    if st.session_state.rol == "admin":
        st.subheader("➕ Registrar nuevo usuario")
        nuevo_usuario = st.text_input("Nuevo usuario")
        nueva_contrasena = st.text_input("Contraseña", type="password")
        rol_usuario = st.selectbox("Rol del usuario", ["usuario", "admin"])
        if st.button("Registrar usuario"):
            if nuevo_usuario in usuarios_df["usuario"].values:
                st.warning("⚠️ El usuario ya existe")
            elif nuevo_usuario == "" or nueva_contrasena == "":
                st.warning("⚠️ Usuario y contraseña no pueden estar vacíos")
            else:
                usuarios_df.loc[len(usuarios_df)] = [nuevo_usuario, nueva_contrasena, rol_usuario]
                usuarios_df.to_csv(USERS_FILE, index=False)
                st.success(f"✅ Usuario '{nuevo_usuario}' registrado correctamente")
                st.experimental_rerun()

    # ==============================
    # CONEXIÓN A GOOGLE DRIVE
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
        gauth.LoadServiceConfigFile(SERVICE_FILE)
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
