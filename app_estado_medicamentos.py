import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.oauth2 import service_account
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DE AUTENTICACIÓN CON GOOGLE DRIVE
# ============================================================

def authenticate_drive():
    SERVICE_ACCOUNT_FILE = "service_account.json"  # JSON de la cuenta de servicio
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    return drive


# ============================================================
# FUNCIÓN PARA GENERAR EL PDF
# ============================================================

def generar_pdf(datos, ruta_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, txt="REGISTRO DE MEDICAMENTO", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    for campo, valor in datos.items():
        pdf.cell(60, 10, f"{campo}:", border=0)
        pdf.multi_cell(0, 10, str(valor))
    pdf.output(ruta_pdf)


# ============================================================
# FUNCIÓN PARA GUARDAR EN GOOGLE DRIVE
# ============================================================

def subir_a_drive(nombre_archivo, ruta_local, carpeta_id=None):
    drive = authenticate_drive()
    archivo_drive = drive.CreateFile({
        "title": nombre_archivo,
        "parents": [{"id": carpeta_id}] if carpeta_id else []
    })
    archivo_drive.SetContentFile(ruta_local)
    archivo_drive.Upload()
    return archivo_drive["id"]


# ============================================================
# FUNCIÓN PRINCIPAL DE REGISTRO
# ============================================================

def page_registrar():
    st.title("📋 Registro de Medicamentos")
    st.write("Completa la información del medicamento para registrarlo y generar su soporte en PDF.")

    with st.form("registro_medicamento"):
        nombre_medicamento = st.text_input("Nombre del medicamento")
        laboratorio = st.text_input("Laboratorio")
        proveedor = st.text_input("Proveedor")
        lote = st.text_input("Número de lote")
        fecha_vencimiento = st.date_input("Fecha de vencimiento")
        cantidad = st.number_input("Cantidad disponible", min_value=0, step=1)
        estado = st.selectbox("Estado del medicamento", ["Activo", "Descontinuado", "Agotado", "Desabastecido"])
        observaciones = st.text_area("Observaciones adicionales")

        registrado_por = st.text_input("Registrado por (nombre del usuario)")
        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        enviar = st.form_submit_button("Guardar Registro")

        if enviar:
            if not nombre_medicamento or not laboratorio or not proveedor:
                st.warning("⚠️ Debes llenar todos los campos obligatorios.")
                return

            datos = {
                "Nombre del medicamento": nombre_medicamento,
                "Laboratorio": laboratorio,
                "Proveedor": proveedor,
                "Lote": lote,
                "Fecha de vencimiento": fecha_vencimiento,
                "Cantidad": cantidad,
                "Estado": estado,
                "Observaciones": observaciones,
                "Registrado por": registrado_por,
                "Fecha de registro": fecha_registro
            }

            nombre_pdf = f"{nombre_medicamento.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            ruta_pdf = os.path.join(os.getcwd(), nombre_pdf)
            generar_pdf(datos, ruta_pdf)

            st.success("✅ Medicamento registrado correctamente.")
            with open(ruta_pdf, "rb") as file:
                st.download_button("📄 Descargar PDF", data=file, file_name=nombre_pdf, mime="application/pdf")

            try:
                drive_id = subir_a_drive(nombre_pdf, ruta_pdf)
                st.info(f"📤 El PDF fue subido exitosamente a Google Drive (ID: {drive_id}).")
            except Exception as e:
                st.error(f"Error al subir a Drive: {e}")


# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================

def main():
    st.set_page_config(page_title="Control de Medicamentos", layout="centered")
    menu = st.sidebar.selectbox(
        "Menú principal",
        ["Registro de medicamentos"]
    )

    if menu == "Registro de medicamentos":
        page_registrar()


if __name__ == "__main__":
    main()
