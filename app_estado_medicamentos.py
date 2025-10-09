import streamlit as st
import pandas as pd
import os
import re
import base64
import time
import json
import tempfile
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Directorios
BASE_DIR = os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(SOPORTES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Logo (opcional)
logo_path = os.path.join(ASSETS_DIR, "logo_empresa.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=180)
st.markdown("## 🧾 Control de Estado de Medicamentos")

# ---------------- CREAR ARCHIVOS SI NO EXISTEN ----------------
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"]

# Cargar registros
if os.path.exists(DATA_FILE):
    df_registros = pd.read_csv(DATA_FILE)
    for col in expected_columns:
        if col not in df_registros.columns:
            df_registros[col] = ""
    df_registros = df_registros[expected_columns]
else:
    df_registros = pd.DataFrame(columns=expected_columns)
    df_registros.to_csv(DATA_FILE, index=False)

# Cargar usuarios
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

def limpiar_formulario():
    for key in ["estado","plu","codigo_generico","nombre_medicamento","laboratorio","soporte_file","ultimo_pdf_path"]:
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

def mostrar_pdf_en_pestana(soporte_path):
    if os.path.exists(soporte_path):
        st.markdown(f'<a href="file:///{soporte_path}" target="_blank">📄 Abrir PDF</a>', unsafe_allow_html=True)
        unique_key = f"download_{os.path.basename(soporte_path)}_{int(time.time()*1000)}"
        with open(soporte_path, "rb") as f:
            pdf_data = f.read()
        st.download_button(
            label=f"📥 Descargar PDF",
            data=pdf_data,
            file_name=os.path.basename(soporte_path),
            mime="application/pdf",
            key=unique_key
        )

def descargar_csv(df):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    st.markdown(f'<a href="data:file/csv;base64,{b64}" download="consolidado_medicamentos.csv">📥 Descargar CSV consolidado</a>', unsafe_allow_html=True)

# ---------------- SESIÓN ----------------
st.sidebar.header("🔐 Inicio de sesión")

if "usuario" not in st.session_state:
    # Mostrar formulario de login
    usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.success(f"Bienvenido {usuario_input}")
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")
else:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.success("Sesión cerrada. Recarga la página para iniciar de nuevo.")

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])

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

        if soporte_file is not None and nombre.strip():
            nombre_pdf = f"{consecutivo}_{nombre_valido_archivo(nombre)}.pdf"
            pdf_path = os.path.join(SOPORTES_DIR, nombre_pdf)
            with open(pdf_path, "wb") as f:
                f.write(soporte_file.getbuffer())
            st.session_state["ultimo_pdf_path"] = pdf_path
            st.markdown("### PDF disponible")
            mostrar_pdf_en_pestana(pdf_path)

        col1, col2 = st.columns([1,1])
        if col1.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif "ultimo_pdf_path" not in st.session_state:
                st.warning("Debes subir un PDF")
            else:
                # Guardar registro en CSV local
                new_row = pd.DataFrame([[
                    consecutivo, usuario, estado, plu, codigo_gen,
                    nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"),
                    st.session_state["ultimo_pdf_path"]
                ]], columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                save_registros(df_registros)

               # ---------------- SUBIR PDF A GOOGLE DRIVE ----------------
def subir_pdf_drive(ruta_local):
    try:
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
        import json
        import tempfile

        # Leer credenciales desde st.secrets
        creds_dict = json.loads(st.secrets["google"]["service_account_file"])
        carpeta_drive_id = st.secrets["google"]["carpeta_drive_id"]

        # Crear archivo temporal con la credencial
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tmpfile:
            json.dump(creds_dict, tmpfile)
            SERVICE_FILE = tmpfile.name

        # Autenticación con PyDrive2 usando ServiceAuth
        gauth = GoogleAuth()
        gauth.ServiceAuth(filename=SERVICE_FILE)  # ✅ solo un argumento

        drive = GoogleDrive(gauth)

        # Subir archivo a la carpeta especificada
        nombre_archivo = os.path.basename(ruta_local)
        gfile = drive.CreateFile({'title': nombre_archivo,
                                  'parents':[{'id': carpeta_drive_id}]})
        gfile.SetContentFile(ruta_local)
        gfile.Upload()

        st.success(f"✅ Archivo subido a Drive: {nombre_archivo}")
        return True

    except Exception as e:
        st.error(f"❌ Error subiendo a Google Drive: {e}")
        return False
