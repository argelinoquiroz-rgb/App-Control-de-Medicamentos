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

# Carpeta de destino en Google Drive
GOOGLE_DRIVE_FOLDER_ID = "1itzZF2zLNLmGEDm-ok8FD_rhadaIUM_Z"
SERVICE_ACCOUNT_FILE = "service_account.json"

# ------------------------------------------------------------
# CONFIGURACIÓN DE CREDENCIALES
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
# AUTENTICACIÓN GOOGLE DRIVE
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
# FUNCIÓN: SUBIR ARCHIVO A GOOGLE DRIVE
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
        st.success(f"✅ '{file_name}' subido exitosamente a Google Drive.")
    except Exception as e:
        st.error(f"❌ Error al subir el archivo: {e}")


# ------------------------------------------------------------
# FUNCIÓN: GENERAR PDF DEL REGISTRO
# ------------------------------------------------------------
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
    pdf.cell(0, 10, f"Fecha de Registro: {fecha}", ln=True)
    pdf.cell(0, 10, f"Consecutivo: {consecutivo}", ln=True)
    pdf.output(nombre_archivo)
    return nombre_archivo


# ------------------------------------------------------------
# FUNCIÓN: REGISTRAR NUEVO MEDICAMENTO
# ------------------------------------------------------------
def page_registrar():
    st.header("📋 Registrar estado de medicamento")

    with st.form("registro_form"):
        nombre = st.text_input("Nombre del medicamento")
        estado = st.selectbox("Estado", ["Disponible", "Agotado", "Desabastecido", "Descontinuado"])
        enviado = st.form_submit_button("Guardar registro")

    if enviado:
        if not nombre.strip():
            st.warning("⚠️ Ingresa el nombre del medicamento antes de continuar.")
            return

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        archivo_csv = "registro_medicamentos.csv"

        # Crear o actualizar CSV
        if os.path.exists(archivo_csv):
            df = pd.read_csv(archivo_csv)
            consecutivo = len(df) + 1
        else:
            df = pd.DataFrame(columns=["Consecutivo", "Medicamento", "Estado", "Fecha"])
            consecutivo = 1

        nuevo = pd.DataFrame([{
            "Consecutivo": consecutivo,
            "Medicamento": nombre,
            "Estado": estado,
            "Fecha": fecha
        }])
        df = pd.concat([df, nuevo], ignore_index=True)
        df.to_csv(archivo_csv, index=False, encoding="utf-8-sig")

        # Generar PDF
        pdf_file = generar_pdf(nombre, estado, fecha, consecutivo)
        st.success(f"✅ Registro guardado correctamente. Se generó el archivo {pdf_file}.")

        # Subir PDF a Drive
        upload_to_drive(pdf_file, pdf_file)

        # Botón de descarga directa
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="📄 Descargar reporte PDF",
                data=f,
                file_name=pdf_file,
                mime="application/pdf"
            )


# ------------------------------------------------------------
# FUNCIÓN: VER REGISTROS GUARDADOS
# ------------------------------------------------------------
def page_registros():
    st.header("📁 Registros guardados")

    archivo_csv = "registro_medicamentos.csv"
    if not os.path.exists(archivo_csv):
        st.info("Aún no hay registros disponibles.")
        return

    df = pd.read_csv(archivo_csv)
    buscar = st.text_input("🔍 Buscar medicamento o estado:")

    if buscar:
        df = df[df.apply(lambda r: buscar.lower() in str(r).lower(), axis=1)]

    st.dataframe(df, use_container_width=True)

    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Descargar registros en CSV", csv, "registros_medicamentos.csv", "text/csv")


# ------------------------------------------------------------
# INTERFAZ PRINCIPAL
# ------------------------------------------------------------
menu = st.sidebar.radio("Menú", ["Registrar medicamento", "Ver registros"])

if menu == "Registrar medicamento":
    page_registrar()
else:
    page_registros()
