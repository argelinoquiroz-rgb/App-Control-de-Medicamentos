import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# Ruta del archivo de credenciales de servicio
SERVICE_ACCOUNT_FILE = "service_account.json"

# --- FUNCIÓN PARA SUBIR PDF A GOOGLE DRIVE ---
def upload_to_drive(file_path, file_name, folder_id=None):
    """Sube un archivo a Google Drive usando un servicio sin intervención humana"""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": file_name}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = open(file_path, "rb")
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    media.close()

    file_id = uploaded.get("id")
    return f"https://drive.google.com/file/d/{file_id}/view"

# --- FUNCIÓN PARA GENERAR EL PDF ---
def generar_pdf(datos, ruta_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="REGISTRO DE MEDICAMENTOS", ln=True, align="C")
    pdf.ln(10)

    for campo, valor in datos.items():
        pdf.multi_cell(0, 10, f"{campo}: {valor}")

    pdf.output(ruta_pdf)

# --- FUNCIÓN PRINCIPAL DEL FORMULARIO ---
def page_registrar():
    st.title("Registro de Medicamentos")

    with st.form("form_registro"):
        nombre = st.text_input("Nombre del medicamento")
        codigo = st.text_input("Código interno")
        laboratorio = st.text_input("Laboratorio")
        fecha_registro = st.date_input("Fecha de registro", datetime.now().date())
        cantidad = st.number_input("Cantidad disponible", min_value=0)
        lote = st.text_input("Lote")
        fecha_vencimiento = st.date_input("Fecha de vencimiento")
        observaciones = st.text_area("Observaciones adicionales")

        enviado = st.form_submit_button("Guardar Registro")

    if enviado:
        datos = {
            "Nombre": nombre,
            "Código Interno": codigo,
            "Laboratorio": laboratorio,
            "Fecha de Registro": fecha_registro,
            "Cantidad Disponible": cantidad,
            "Lote": lote,
            "Fecha de Vencimiento": fecha_vencimiento,
            "Observaciones": observaciones
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            generar_pdf(datos, tmpfile.name)
            drive_url = upload_to_drive(tmpfile.name, f"{nombre}.pdf")

        st.success("Registro guardado correctamente ✅")
        st.markdown(f"[📄 Descargar PDF en Google Drive]({drive_url})")

# --- MAIN ---
def main():
    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Selecciona una opción", ["Registrar Medicamento"])

    if opcion == "Registrar Medicamento":
        page_registrar()

if __name__ == "__main__":
    main()
