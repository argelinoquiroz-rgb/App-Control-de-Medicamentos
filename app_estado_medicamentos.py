import streamlit as st
import pandas as pd
import os
import re
import base64
import time
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import json
import tempfile

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Directorios
BASE_DIR = os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")

# ---------------- CARGAR CSVS ----------------
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"]
if os.path.exists(DATA_FILE):
    df_registros = pd.read_csv(DATA_FILE)
    for col in expected_columns:
        if col not in df_registros.columns:
            df_registros[col] = ""
    df_registros = df_registros[expected_columns]
else:
    df_registros = pd.DataFrame(columns=expected_columns)
    df_registros.to_csv(DATA_FILE, index=False)

if os.path.exists(USERS_FILE):
    df_usuarios = pd.read_csv(USERS_FILE)
else:
    df_usuarios = pd.DataFrame([{"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}])
    df_usuarios.to_csv(USERS_FILE, index=False)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

# ---------------- FUNCIONES ----------------
def save_registros(df):
    df.to_csv(DATA_FILE, index=False)

def save_usuarios(df):
    df.to_csv(USERS_FILE, index=False)

def nombre_valido_archivo(nombre):
    nombre = nombre.upper().replace(' ', '_')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre

def obtener_consecutivo():
    if df_registros.empty:
        return 1
    else:
        return int(df_registros["Consecutivo"].max()) + 1

def descargar_csv(df):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    st.markdown(f'<a href="data:file/csv;base64,{b64}" download="consolidado_medicamentos.csv">📥 Descargar CSV consolidado</a>', unsafe_allow_html=True)

# ---------------- AUTENTICACIÓN DRIVE ----------------
def autenticar_drive():
    creds_dict = json.loads(st.secrets["google_credentials"])
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
        json.dump(creds_dict, tmpfile)
        service_file = tmpfile.name

    gauth = GoogleAuth()
    gauth.settings['client_config_file'] = service_file
    gauth.ServiceAuth()  # ✅ correcto para cuenta de servicio
    drive = GoogleDrive(gauth)
    return drive

try:
    drive = autenticar_drive()
    st.success("✅ Conexión exitosa con Google Drive")
except Exception as e:
    st.error(f"❌ Error autenticando con Google Drive: {e}")
    st.stop()

# ---------------- SESIÓN ----------------
st.sidebar.header("🔐 Inicio de sesión")
if "usuario" in st.session_state:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.experimental_rerun()
else:
    usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.experimental_rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")

# ---------------- CREAR USUARIO ----------------
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
        save_usuarios(df_usuarios)
        st.sidebar.success(f"Usuario creado: {nombre_usuario_nuevo}")

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])

    # -------- TAB REGISTRO --------
    with tabs[0]:
        consecutivo = obtener_consecutivo()
        estado = st.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"], index=0)
        plu = st.text_input("PLU").upper()
        codigo_gen = st.text_input("Código genérico").upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])

        if st.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif soporte_file is None:
                st.warning("Debes subir un PDF")
            else:
                nombre_pdf = f"{consecutivo}_{nombre_valido_archivo(nombre)}.pdf"
                # Guardar temporalmente
                temp_path = os.path.join(BASE_DIR, nombre_pdf)
                with open(temp_path, "wb") as f:
                    f.write(soporte_file.getbuffer())

                # Subir a Drive
                try:
                    carpeta_drive_id = st.secrets["carpeta_drive_id"]
                    gfile = drive.CreateFile({'title': nombre_pdf, 'parents':[{'id': carpeta_drive_id}]})
                    gfile.SetContentFile(temp_path)
                    gfile.Upload()
                    st.success(f"✅ Archivo subido a Drive: {nombre_pdf}")
                except Exception as e:
                    st.error(f"❌ Error subiendo a Drive: {e}")
                    st.stop()

                # Guardar registro en CSV
                new_row = pd.DataFrame([[consecutivo, usuario, estado, plu, codigo_gen,
                                         nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"),
                                         nombre_pdf]], columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                save_registros(df_registros)
                st.success("✅ Registro guardado")

    # -------- TAB CONSOLIDADO --------
    with tabs[1]:
        st.dataframe(df_registros)
        descargar_csv(df_registros)
