import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from fpdf import FPDF
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
# ------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------
st.set_page_config(page_title="Control de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

GOOGLE_DRIVE_FOLDER_ID = "1itzZF2zLNLmGEDm-ok8FD_rhadaIUM_Z"
SERVICE_ACCOUNT_FILE = "service_account.json"
ARCHIVO_USUARIOS = "usuarios.csv"

# ------------------------------------------------------------
# CARGAR CREDENCIALES GOOGLE DRIVE
# ------------------------------------------------------------
if "service_account" in st.secrets:
    creds = dict(st.secrets["service_account"])
    with open(SERVICE_ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)


def verificar_credenciales():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error("❌ No se encontró el archivo de credenciales.")
        st.stop()
    try:
        with open(SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ["type", "client_email", "private_key", "token_uri"]:
            if key not in data:
                st.error(f"❌ Falta la clave '{key}' en las credenciales.")
                st.stop()
    except Exception as e:
        st.error(f"❌ Error leyendo credenciales: {e}")
        st.stop()


# ------------------------------------------------------------
# AUTENTICAR CON GOOGLE DRIVE
# ------------------------------------------------------------
def authenticate_drive():
    verificar_credenciales()
    try:
        gauth = GoogleAuth(settings={
            "client_config_backend": "service",
            "service_config_file": SERVICE_ACCOUNT_FILE,
            "oauth_scope": ["https://www.googleapis.com/auth/drive"]
        })
        gauth.ServiceAuth()
        return GoogleDrive(gauth)
    except Exception as e:
        st.error(f"⚠️ Error autenticando con Google Drive: {e}")
        st.stop()


# ------------------------------------------------------------
# USUARIOS: CARGA, CREACIÓN Y VALIDACIÓN
# ------------------------------------------------------------
def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        df = pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]})
        df.to_csv(ARCHIVO_USUARIOS, index=False)
    return pd.read_csv(ARCHIVO_USUARIOS, dtype=str)


def guardar_usuario(usuario, contrasena):
    df = cargar_usuarios()
    if usuario.lower().strip() in df["usuario"].str.lower().values:
        return False, "⚠️ El usuario ya existe."
    nuevo = pd.DataFrame({"usuario": [usuario], "contrasena": [contrasena]})
    df = pd.concat([df, nuevo], ignore_index=True)
    df.to_csv(ARCHIVO_USUARIOS, index=False)
    return True, "✅ Usuario creado correctamente."


def login(usuario, contrasena):
    df = cargar_usuarios()
    valid = ((df["usuario"].str.lower() == usuario.lower()) & (df["contrasena"] == contrasena)).any()
    return valid


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------
def upload_to_drive(file_path, file_name):
    try:
        drive = authenticate_drive()
        gfile = drive.CreateFile({
            "title": file_name,
            "parents": [{"id": GOOGLE_DRIVE_FOLDER_ID}]
        })
        gfile.SetContentFile(file_path)
        gfile.Upload()
        gfile.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
        link = f"https://drive.google.com/uc?id={gfile['id']}&export=download"
        return link
    except Exception as e:
        st.error(f"❌ Error al subir a Google Drive: {e}")
        return None


def generar_pdf(medicamento, estado, fecha, consecutivo):
    nombre_archivo = f"{consecutivo}_{medicamento.replace(' ', '_')}.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Reporte de Estado de Medicamento", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Medicamento: {medicamento}", ln=True)
    pdf.cell(0, 10, f"Estado: {estado}", ln=True)
    pdf.cell(0, 10, f"Fecha: {fecha}", ln=True)
    pdf.cell(0, 10, f"Consecutivo: {consecutivo}", ln=True)
    pdf.output(nombre_archivo)
    return nombre_archivo


# ------------------------------------------------------------
# PÁGINAS DE LA APLICACIÓN
# ------------------------------------------------------------
def page_registrar(usuario):
    st.header("➕ Registrar nuevo medicamento")
    with st.form("registro_form"):
        medicamento = st.text_input("💊 Nombre del medicamento").strip()
        estado = st.selectbox("⚕️ Estado", ["Disponible", "Agotado", "Desabastecido", "Descontinuado"])
        enviado = st.form_submit_button("Guardar registro")

    if enviado:
        if not medicamento:
            st.warning("⚠️ Ingresa el nombre del medicamento.")
            return
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        archivo = "registros_medicamentos.csv"

        if os.path.exists(archivo):
            df = pd.read_csv(archivo)
            consecutivo = len(df) + 1
        else:
            df = pd.DataFrame(columns=["Consecutivo", "Usuario", "Medicamento", "Estado", "Fecha", "PDF"])
            consecutivo = 1

        pdf_name = generar_pdf(medicamento, estado, fecha, consecutivo)
        link = upload_to_drive(pdf_name, pdf_name)

        nuevo = pd.DataFrame([{
            "Consecutivo": consecutivo,
            "Usuario": usuario,
            "Medicamento": medicamento,
            "Estado": estado,
            "Fecha": fecha,
            "PDF": link
        }])

        df = pd.concat([df, nuevo], ignore_index=True)
        df.to_csv(archivo, index=False, encoding="utf-8-sig")
        st.success("✅ Registro guardado correctamente.")
        if link:
            st.markdown(f"[📥 Descargar PDF en Drive]({link})")


def page_registros():
    st.header("📁 Registros guardados")
    archivo = "registros_medicamentos.csv"
    if not os.path.exists(archivo):
        st.info("Aún no hay registros.")
        return
    df = pd.read_csv(archivo)
    buscar = st.text_input("🔍 Buscar medicamento o estado")
    if buscar:
        df = df[df.apply(lambda r: buscar.lower() in str(r).lower(), axis=1)]
    st.dataframe(df, use_container_width=True)


def page_gestion_usuarios():
    st.header("👥 Gestión de usuarios")
    st.subheader("Crear nuevo usuario")
    nuevo_usuario = st.text_input("Usuario")
    nueva_contrasena = st.text_input("Contraseña", type="password")
    if st.button("Crear usuario"):
        ok, msg = guardar_usuario(nuevo_usuario, nueva_contrasena)
        st.info(msg)
    st.subheader("Usuarios actuales")
    st.dataframe(cargar_usuarios(), use_container_width=True)


# ------------------------------------------------------------
# INTERFAZ PRINCIPAL
# ------------------------------------------------------------
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

if not st.session_state["usuario"]:
    st.sidebar.header("🔐 Inicio de sesión")
    user = st.sidebar.text_input("Usuario")
    pwd = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Iniciar sesión"):
        if login(user, pwd):
            st.session_state["usuario"] = user
            st.sidebar.success("✅ Sesión iniciada.")
            st.rerun()
        else:
            st.sidebar.error("❌ Usuario o contraseña incorrectos.")
else:
    usuario = st.session_state["usuario"]
    st.sidebar.markdown(f"👤 **Usuario:** {usuario}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["usuario"] = None
        st.rerun()

    menu = ["Registrar medicamento", "Ver registros"]
    if usuario.lower() == "admin":
        menu.append("Gestión de usuarios")
    opcion = st.sidebar.radio("Menú principal", menu)

    if opcion == "Registrar medicamento":
        page_registrar(usuario)
    elif opcion == "Ver registros":
        page_registros()
    elif opcion == "Gestión de usuarios":
        page_gestion_usuarios()
