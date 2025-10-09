import pandas as pd
import os
import re
import base64
import time
from datetime import datetime
import json
import tempfile
import streamlit as st

# PyDrive2
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

BASE_DIR = os.getcwd()
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(SOPORTES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

logo_path = os.path.join(ASSETS_DIR, "logo_empresa.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=180)
st.markdown("## 🧾 Control de Estado de Medicamentos")

# ---------------- CREAR ARCHIVOS SI NO EXISTEN ----------------
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"]

df_registros = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=expected_columns)
for col in expected_columns:
    if col not in df_registros.columns:
        df_registros[col] = ""

df_usuarios = pd.read_csv(USERS_FILE) if os.path.exists(USERS_FILE) else pd.DataFrame([{"usuario":"admin","contrasena":"1234","correo":"admin@pharmaser.com.co"}])
df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

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
    return int(df_registros["Consecutivo"].max()+1) if not df_registros.empty else 1

def mostrar_pdf_en_pestana(soporte_path):
    if os.path.exists(soporte_path):
        st.markdown(f'<a href="file:///{soporte_path}" target="_blank">📄 Abrir PDF</a>', unsafe_allow_html=True)
        with open(soporte_path, "rb") as f:
            pdf_data = f.read()
        st.download_button("📥 Descargar PDF", pdf_data, os.path.basename(soporte_path), mime="application/pdf")

def descargar_csv(df):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    st.markdown(f'<a href="data:file/csv;base64,{b64}" download="consolidado_medicamentos.csv">📥 Descargar CSV consolidado</a>', unsafe_allow_html=True)

# ---------------- SESIÓN ----------------
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
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"]==usuario_input,"contrasena"].values[0]
            if contrasena_input==stored_pass:
                st.session_state["usuario"] = usuario_input
                st.experimental_rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento","Consolidado general"])

    with tabs[0]:
        consecutivo = obtener_consecutivo()
        estado = st.selectbox("Estado", ["Agotado","Desabastecido","Descontinuado"], index=0)
        plu = st.text_input("PLU").upper()
        codigo_gen = st.text_input("Código genérico").upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])
        st.date_input("Fecha", value=datetime.now(), disabled=True)

        if soporte_file and nombre.strip():
            nombre_pdf = f"{consecutivo}_{nombre_valido_archivo(nombre)}.pdf"
            pdf_path = os.path.join(SOPORTES_DIR,nombre_pdf)
            with open(pdf_path,"wb") as f:
                f.write(soporte_file.getbuffer())
            st.session_state["ultimo_pdf_path"] = pdf_path
            mostrar_pdf_en_pestana(pdf_path)

        col1, _ = st.columns([1,1])
        if col1.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif "ultimo_pdf_path" not in st.session_state:
                st.warning("Debes subir un PDF")
            else:
                # Guardar local
                new_row = pd.DataFrame([[consecutivo, usuario, estado, plu, codigo_gen,
                                         nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"),
                                         st.session_state["ultimo_pdf_path"]]],
                                       columns=df_registros.columns)
                df_registros = pd.concat([df_registros,new_row],ignore_index=True)
                save_registros(df_registros)
                st.success("✅ Registro guardado localmente")

                # Subir a Google Drive
                try:
                    creds_dict = json.loads(st.secrets["google"]["service_account_file"])
                    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
                        json.dump(creds_dict,tmpfile)
                        service_file = tmpfile.name

                    gauth = GoogleAuth()
                    gauth.LoadServiceConfigFile(service_file)
                    gauth.ServiceAuth()
                    drive = GoogleDrive(gauth)

                    carpeta_id = st.secrets["google"]["carpeta_drive_id"]
                    gfile = drive.CreateFile({'title':os.path.basename(st.session_state["ultimo_pdf_path"]),
                                              'parents':[{'id':carpeta_id}]})
                    gfile.SetContentFile(st.session_state["ultimo_pdf_path"])
                    gfile.Upload()
                    st.success(f"✅ Archivo subido a Drive: {gfile['title']}")
                except Exception as e:
                    st.error(f"❌ Error autenticando o subiendo a Google Drive: {e}")

                limpiar_formulario()

    with tabs[1]:
        st.markdown("### 📊 Consolidado de registros")
        st.dataframe(df_registros)
        descargar_csv(df_registros)
