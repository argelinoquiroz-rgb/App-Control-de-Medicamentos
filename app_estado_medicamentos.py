import os
from datetime import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Control de Medicamentos - Pharmaser",
    page_icon="💊",
    layout="wide"
)

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
<style>
div.block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
.stTextInput, .stSelectbox, .stFileUploader, .stButton { margin-bottom: 0.2rem !important; padding: 0 !important; }
h1, h2, h3, h4 { margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
button[kind="primary"] { height: 2rem !important; padding: 0.2rem 0.8rem !important; font-size: 0.85rem !important; }
p, label, span { font-size: 0.9rem !important; }
div[data-baseweb="select"] > div { flex-direction: column !important; }
.logo-container { display: flex; justify-content: center; align-items: center; margin-top: -0.5rem; margin-bottom: 0.1rem; }
.titulo-principal { text-align: center; font-weight: 600; margin-top: 0 !important; margin-bottom: 0.2rem !important; }
hr { margin-top: 0.4rem !important; margin-bottom: 0.4rem !important; }
</style>
""", unsafe_allow_html=True)

# --- CONFIG GOOGLE SHEETS / DRIVE ---
SERVICE_ACCOUNT_FILE = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Escritorio\App_Control_Medicamentos\credenciales.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

SHEET_ID = "TU_ID_DE_GOOGLE_SHEET"  # <--- reemplaza por tu Sheet
SHEET_NAME = "Registros"
USERS_SHEET = "Usuarios"
DRIVE_FOLDER_ID = "TU_ID_CARPETA_DRIVE"  # <--- reemplaza por tu carpeta de PDFs

# --- FUNCIONES GOOGLE SHEETS ---
def load_data():
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except:
        return pd.DataFrame(columns=[
            "consecutivo","estado","plu","codigo_generico","nombre","presentacion",
            "laboratorio","fecha_creacion","soporte","usuario_creacion"
        ])

def save_data(df):
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Error guardando datos en Google Sheets: {e}")

def load_users():
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(USERS_SHEET)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["correo","nombres","apellidos","cargo","usuario","password"])

def save_users(df):
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(USERS_SHEET)
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Error guardando usuarios: {e}")

# --- SUBIDA DE ARCHIVOS A DRIVE ---
def subir_pdf_drive(file, nombre_archivo):
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype='application/pdf')
    file_metadata = {"name": nombre_archivo, "parents": [DRIVE_FOLDER_ID]}
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return uploaded_file.get('webViewLink')  # Devuelve el link para abrir en Drive

# --- LOGO ---
def mostrar_encabezado():
    logo_path = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Escritorio\App_Control_Medicamentos\logo_pharmaser.png"
    if os.path.exists(logo_path):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(Image.open(logo_path), width=250)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="titulo-principal">Sistema de Control de Medicamentos - Pharmaser</h2>', unsafe_allow_html=True)
    st.divider()

# --- LOGIN / REGISTRO ---
def login():
    mostrar_encabezado()
    tab_login, tab_register = st.tabs(["Iniciar sesión","Registrar usuario"])
    users = load_users()

    with tab_login:
        usuario = st.text_input("Usuario", key="login_usuario").upper()
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Ingresar", key="btn_ingresar"):
            if not users.empty and (users["usuario"].str.upper() == usuario).any():
                user_row = users[users["usuario"].str.upper() == usuario].iloc[0]
                if str(user_row["password"]) == password:
                    st.session_state["usuario"] = user_row["usuario"]
                    st.session_state["nombre"] = user_row["nombres"]
                    st.session_state["apellido"] = user_row["apellidos"]
                    st.rerun()
                else:
                    st.error("Password incorrecto")
            else:
                st.error("Usuario no encontrado")

    with tab_register:
        st.subheader("Registrar Usuario")
        col1,col2 = st.columns(2)
        with col1:
            nombres = st.text_input("Nombres").upper()
            cargo = st.text_input("Cargo").upper()
            usuario_new = st.text_input("Nombre de usuario").upper()
        with col2:
            apellidos = st.text_input("Apellidos").upper()
            correo = st.text_input("Correo (@pharmaser.com.co)").lower()
            password_new = st.text_input("Password", type="password")
        if st.button("Crear usuario"):
            if not all([nombres, apellidos, cargo, usuario_new, correo, password_new]):
                st.error("Todos los campos son obligatorios")
            elif not correo.endswith("@pharmaser.com.co"):
                st.error("Correo no permitido")
            elif usuario_new in users["usuario"].str.upper().values:
                st.error("Usuario ya existe")
            else:
                new_user = pd.DataFrame([[correo,nombres,apellidos,cargo,usuario_new,password_new]], columns=users.columns)
                users = pd.concat([users,new_user], ignore_index=True)
                save_users(users)
                st.success("Usuario creado ✅")

# --- APP PRINCIPAL ---
def main_app():
    mostrar_encabezado()
    st.sidebar.write(f"👋 Bienvenido {st.session_state['nombre']} {st.session_state['apellido']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

    tab_registro, tab_reporte = st.tabs(["📝 Registrar Medicamento","📊 Reporte de Medicamentos"])

    with tab_registro:
        st.subheader("📝 Registro de Medicamentos")
        estado = st.selectbox("Estado", ["Agotado","Desabastecido","Descontinuado"])
        plu = st.text_input("PLU").upper()
        codigo_generico = plu.split("_")[0] if "_" in plu else ""
        nombre = st.text_input("Nombre del Medicamento").upper()
        presentacion = st.text_input("Presentación").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte = st.file_uploader("Adjuntar soporte (PDF, máx 200 KB)", type=["pdf"])

        if st.button("Guardar Registro"):
            if not all([estado,plu,nombre,presentacion,laboratorio,st.session_state["usuario"]]):
                st.error("Todos los campos son obligatorios")
            else:
                df = load_data()
                consecutivo = len(df)+1
                fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                soporte_link = ""
                if soporte:
                    if soporte.size > 200*1024:
                        st.warning("Archivo supera 200KB")
                    else:
                        soporte_link = subir_pdf_drive(soporte, f"{consecutivo}_{nombre}.pdf")
                nuevo = pd.DataFrame([[consecutivo,estado,plu,codigo_generico,nombre,presentacion,laboratorio,fecha_creacion,soporte_link,st.session_state["usuario"]]], columns=df.columns)
                df = pd.concat([df,nuevo], ignore_index=True)
                save_data(df)
                st.success("💾 Registro guardado ✅")

    with tab_reporte:
        st.subheader("📊 Reporte de Medicamentos")
        df = load_data()
        if df.empty:
            st.info("No hay registros")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Descargar CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="reporte.csv", mime="text/csv")

# --- EJECUCIÓN ---
if "usuario" not in st.session_state:
    login()
else:
    main_app()

