import streamlit as st
import pandas as pd
import os
import re
import base64
import tempfile
import json
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Directorios locales
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

# ==============================
# AUTENTICACIÓN GOOGLE DRIVE
# ==============================
try:
    creds_dict = st.secrets["google_credentials"]

    # 🔹 Ajuste de saltos de línea
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n") if "\\n" in creds_dict["private_key"] else creds_dict["private_key"]
    creds_json_str = json.dumps(creds_dict)

    # Crear archivo temporal de configuración YAML para PyDrive2
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        f.write(f"""
client_config_backend: service
service_config:
  client_json: {creds_json_str}
save_credentials: False
""")
        settings_file = f.name

    gauth = GoogleAuth(settings_file=settings_file)
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    st.success("✅ Conexión exitosa con Google Drive")
except Exception as e:
    st.error(f"❌ Error autenticando con Google Drive: {e}")
    st.stop()

# ==============================
# CARGAR USUARIOS Y REGISTROS
# ==============================
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"]

# Registros de medicamentos
if os.path.exists(DATA_FILE):
    df_registros = pd.read_csv(DATA_FILE)
    for col in expected_columns:
        if col not in df_registros.columns:
            df_registros[col] = ""
    df_registros = df_registros[expected_columns]
else:
    df_registros = pd.DataFrame(columns=expected_columns)
    df_registros.to_csv(DATA_FILE, index=False)

# Usuarios
if os.path.exists(USERS_FILE):
    df_usuarios = pd.read_csv(USERS_FILE)
else:
    df_usuarios = pd.DataFrame([{"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}])
    df_usuarios.to_csv(USERS_FILE, index=False)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

# ==============================
# FUNCIONES AUXILIARES
# ==============================
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
    return int(df_registros["Consecutivo"].max()) + 1 if not df_registros.empty else 1

def mostrar_pdf_en_pestana(soporte_path):
    if os.path.exists(soporte_path):
        st.markdown(f'<a href="file:///{soporte_path}" target="_blank">📄 Abrir PDF</a>', unsafe_allow_html=True)
        unique_key = f"download_{os.path.basename(soporte_path)}_{int(datetime.now().timestamp()*1000)}"
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

# ==============================
# SESIÓN DE USUARIO
# ==============================
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
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.success(f"Bienvenido {usuario_input}")
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")

    # Crear usuario
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

# ==============================
# INTERFAZ PRINCIPAL
# ==============================
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])

    # ---- TAB REGISTRO ----
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
                st.warning("Deb

