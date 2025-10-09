import streamlit as st
import pandas as pd
import json
import os
import re
import time
import base64
from datetime import datetime
from io import BytesIO
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Directorios locales temporales
BASE_DIR = os.getcwd()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Logo opcional
logo_path = os.path.join(ASSETS_DIR, "logo_empresa.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=180)
st.markdown("## 🧾 Control de Estado de Medicamentos")

# ==================================
# GOOGLE DRIVE - CUENTA DE SERVICIO
# ==================================
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
except Exception as e:
    st.error("❌ No se pudo cargar 'google_credentials' desde st.secrets")
    st.stop()

with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
    json.dump(creds_dict, tmpfile)
    SERVICE_FILE = tmpfile.name

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_FILE

try:
    gauth = GoogleAuth()
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    st.success("✅ Conexión exitosa con Google Drive mediante cuenta de servicio.")
except Exception as e:
    st.error(f"❌ Error autenticando con la cuenta de servicio: {e}")
    st.stop()

# ==================================
# USUARIOS
# ==================================
# CSV local temporal para usuarios
USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
if os.path.exists(USERS_FILE):
    df_usuarios = pd.read_csv(USERS_FILE)
else:
    df_usuarios = pd.DataFrame([{
        "usuario": "admin",
        "contrasena": "250382",
        "correo": "lidercompras@pharmaser.com.co"
    }])
    df_usuarios.to_csv(USERS_FILE, index=False)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

def save_usuarios(df):
    df.to_csv(USERS_FILE, index=False)

# ==================================
# SESIÓN - LOGIN Y CREAR USUARIO
# ==================================
st.sidebar.header("🔐 Inicio de sesión")
if "usuario" in st.session_state:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.success("Sesión cerrada. Recarga la página para iniciar de nuevo.")
else:
    usuario_input = st.sidebar.text_input("Usuario").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        user_row = df_usuarios[(df_usuarios["usuario"] == usuario_input) & (df_usuarios["contrasena"] == contrasena_input)]
        if user_row.empty:
            st.sidebar.error("❌ Usuario o contraseña incorrectos")
        else:
            st.session_state["usuario"] = usuario_input
            st.success(f"Bienvenido {usuario_input}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Crear nuevo usuario")
    nombre_usuario_nuevo = st.sidebar.text_input("Usuario", key="usuario_nuevo").strip().lower()
    correo_nuevo = st.sidebar.text_input("Correo electrónico", key="correo_nuevo").strip().lower()
    contrasena_nueva = st.sidebar.text_input("Contraseña", type="password", key="pass_nueva")
    if st.sidebar.button("Crear usuario"):
        if not nombre_usuario_nuevo or not correo_nuevo or not contrasena_nueva:
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

# ==================================
# PROYECTO PRINCIPAL (REGISTRO MEDICAMENTOS)
# ==================================
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")

    # Carpeta Drive donde se guardan los PDFs
    st.subheader("📁 Configuración de carpeta en Google Drive")
    carpeta_id = st.text_input("ID de carpeta en Google Drive")
    
    df_registros = pd.DataFrame(columns=["Consecutivo","Usuario","Estado","PLU","Código Genérico",
                                         "Nombre Medicamento","Laboratorio","Fecha","Soporte Drive ID"])
    
    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])
    
    # -------- TAB REGISTRO --------
    with tabs[0]:
        consecutivo = df_registros.shape[0] + 1
        estado = st.selectbox("Estado", ["Agotado","Desabastecido","Descontinuado"])
        plu = st.text_input("PLU").upper()
        codigo_gen = st.text_input("Código genérico", value=plu.split("_")[0] if "_" in plu else "").upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])
        fecha = datetime.now().strftime("%Y-%m-%d")
        
        if soporte_file and carpeta_id and nombre.strip():
            # Subir PDF a Drive
            try:
                gfile = drive.CreateFile({'title': f"{consecutivo}_{nombre}.pdf", 'parents':[{'id': carpeta_id}]})
                gfile.SetContentBytes(soporte_file.getvalue())
                gfile.Upload()
                st.success(f"✅ PDF subido a Drive con ID: {gfile['id']}")
                soporte_id = gfile['id']
            except Exception as e:
                st.error(f"❌ Error subiendo PDF a Drive: {e}")
                soporte_id = ""
            
            if st.button("💾 Guardar registro"):
                new_row = pd.DataFrame([[consecutivo, usuario, estado, plu, codigo_gen, nombre, laboratorio, fecha, soporte_id]],
                                       columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                st.success("✅ Registro guardado")

    # -------- TAB CONSOLIDADO --------
    with tabs[1]:
        st.dataframe(df_registros)
        # Descargar CSV
        csv = df_registros.to_csv(index=False).encode()
        st.download_button("📥 Descargar CSV consolidado", data=csv, file_name="consolidado_medicamentos.csv", mime="text/csv")
        # Descargar PDFs desde Drive
        for idx, row in df_registros.iterrows():
            if row["Soporte Drive ID"]:
                gfile = drive.CreateFile({'id': row["Soporte Drive ID"]})
                st.download_button(f"📥 Descargar {row['Nombre Medicamento']}.pdf", data=gfile.GetContentBinary(), file_name=f"{row['Nombre Medicamento']}.pdf", mime="application/pdf")
