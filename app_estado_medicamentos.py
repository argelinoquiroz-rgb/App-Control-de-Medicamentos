import streamlit as st
from fpdf import FPDF
import tempfile
import os
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ----------------------------------------------------------
# CONFIGURACIÓN DE GOOGLE DRIVE
# ----------------------------------------------------------
# Archivo JSON de cuenta de servicio (debes tenerlo en la misma carpeta del script)
SERVICE_ACCOUNT_FILE = "credenciales.json"

# ID de la carpeta en Drive donde se subirán los PDFs
# (puedes obtenerlo de la URL de la carpeta en Drive: https://drive.google.com/drive/folders/XXXXXXXX)
FOLDER_ID = "TU_FOLDER_ID_AQUI"  # <-- reemplaza esto

# ----------------------------------------------------------
# FUNCIÓN: Subir archivo PDF a Google Drive
# ----------------------------------------------------------
def upload_to_drive(file_path, file_name):
    # Cargar credenciales de cuenta de servicio
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    # Crear servicio de conexión con Google Drive
    service = build("drive", "v3", credentials=creds)

    # Metadatos del archivo
    file_metadata = {
        "name": file_name,
        "parents": [FOLDER_ID]
    }

    # Subida del archivo
    media = MediaFileUpload(file_path, mimetype="application/pdf")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return file.get("id")

# ----------------------------------------------------------
# FUNCIÓN: Generar el PDF con los datos del medicamento
# ----------------------------------------------------------
def generar_pdf(datos, ruta_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "REGISTRO DE MEDICAMENTO", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    for clave, valor in datos.items():
        texto = f"{clave}: {valor}"
        pdf.multi_cell(0, 8, texto)
        pdf.ln(2)

    pdf.output(ruta_pdf)

# ----------------------------------------------------------
# FUNCIÓN PRINCIPAL DE STREAMLIT
# ----------------------------------------------------------
def page_registrar():
    st.title("📋 Registro de Medicamentos")
    st.markdown("Complete la siguiente información para registrar un nuevo medicamento:")

    # --- CAMPOS DEL FORMULARIO ---
    nombre = st.text_input("Nombre del medicamento")
    laboratorio = st.text_input("Laboratorio fabricante")
    tipo = st.selectbox("Tipo de medicamento", ["Genérico", "Comercial"])
    estado = st.selectbox("Estado del medicamento", ["Activo", "Inactivo", "Pendiente"])
    cantidad = st.number_input("Cantidad disponible", min_value=0, step=1)
    fecha_registro = st.date_input("Fecha de registro", value=date.today())

    # --- BOTÓN PARA GUARDAR ---
    if st.button("Guardar Registro"):
        if not nombre:
            st.error("Debe ingresar el nombre del medicamento.")
            return

        # Crear estructura de datos
        datos = {
            "Nombre del medicamento": nombre,
            "Laboratorio": laboratorio,
            "Tipo": tipo,
            "Estado": estado,
            "Cantidad disponible": cantidad,
            "Fecha de registro": fecha_registro.strftime("%Y-%m-%d")
        }

        # Crear PDF temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            generar_pdf(datos, tmpfile.name)

            # Subir PDF a Google Drive
            drive_id = upload_to_drive(tmpfile.name, f"{nombre}.pdf")

        # Mostrar resultado en la app
        st.success(f"✅ Medicamento '{nombre}' registrado exitosamente.")
        st.markdown(f"📄 [Abrir PDF en Google Drive](https://drive.google.com/file/d/{drive_id}/view)")

# ----------------------------------------------------------
# FUNCIÓN MAIN
# ----------------------------------------------------------
def main():
    page_registrar()

# ----------------------------------------------------------
# EJECUCIÓN
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
