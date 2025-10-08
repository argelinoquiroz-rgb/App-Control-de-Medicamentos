import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re
from io import BytesIO

# Google Drive
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.oauth2.service_account import Credentials

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# ---------------- GOOGLE DRIVE ----------------
SERVICE_JSON = "streamlit-drive-app.json"  # Nombre del JSON descargado de tu cuenta de servicio
gauth = GoogleAuth()
gauth.credentials = Credentials.from_service_account_file(SERVICE_JSON)
drive = GoogleDrive(gauth)

# Carpeta en Drive donde se guardan archivos
DRIVE_FOLDER_ID = "TU_FOLDER_ID_AQUI"  # Cambia esto por el ID de tu carpeta en Drive

# ---------------- FUNCIONES ----------------
def nombre_valido_archivo(nombre):
    nombre = nombre.upper().replace(' ', '_')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre

def obtener_consecutivo(df):
    return int(df["Consecutivo"].max() + 1) if not df.empty else 1

def cargar_csv_drive():
    files = drive.ListFile({'q': f"'{DRIVE_FOLDER_ID}' in parents and trashed=false and title='registros_medicamentos.csv'"}).GetList()
    if files:
        file_content = files[0].GetContentString()
        return pd.read_csv(BytesIO(file_content.encode()))
    else:
        cols = ["Consecutivo","Usuario","Estado","PLU","Código Genérico","Nombre Medicamento",
                "Laboratorio","Fecha","Soporte"]
        return pd.DataFrame(columns=cols)

def guardar_csv_drive(df):
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    file_drive_csv = drive.CreateFile({'title':'registros_medicamentos.csv','parents':[{'id': DRIVE_FOLDER_ID}]})
    file_drive_csv.SetContentString(csv_buffer.getvalue().decode())
    file_drive_csv.Upload()

def subir_pdf_drive(nombre_pdf, archivo):
    file_drive = drive.CreateFile({'title': nombre_pdf,'parents':[{'id': DRIVE_FOLDER_ID}]})
    file_drive.SetContentFile(archivo)
    file_drive.Upload()
    return nombre_pdf

def descargar_csv(df):
    csv_data = df.to_csv(index=False).encode()
    st.download_button("📥 Descargar CSV consolidado", csv_data, file_name="consolidado_medicamentos.csv")

# ---------------- SESIÓN ----------------
if "usuario" not in st.session_state:
    st.sidebar.header("🔐 Inicio de sesión")
    usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        # Carga usuarios desde Drive o un CSV local
        # Aquí puedes reemplazar con tu propio CSV de usuarios en Drive
        df_usuarios = pd.DataFrame([
            {"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}
        ])
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"]==usuario_input,"contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.success(f"Bienvenido {usuario_input}")
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")

    df_registros = cargar_csv_drive()

    tabs = st.tabs(["Registrar medicamento", "Consolidado general"])

    # -------- TAB REGISTRO --------
    with tabs[0]:
        consecutivo = obtener_consecutivo(df_registros)
        estado = st.selectbox("Estado", ["Agotado","Desabastecido","Descontinuado"], index=0)
        plu = st.text_input("PLU").upper()
        codigo_gen_default = plu.split("_")[0] if "_" in plu else ""
        codigo_gen = st.text_input("Código genérico", value=codigo_gen_default).upper()
        nombre = st.text_input("Nombre del medicamento").upper()
        laboratorio = st.text_input("Laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"])
        st.date_input("Fecha", value=datetime.now(), disabled=True)

        if st.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif soporte_file is None:
                st.warning("Debes subir un PDF")
            else:
                # Guardar PDF en Drive
                nombre_pdf = f"{consecutivo}_{nombre_valido_archivo(nombre)}.pdf"
                pdf_path_local = os.path.join(os.getcwd(), nombre_pdf)
                with open(pdf_path_local, "wb") as f:
                    f.write(soporte_file.getbuffer())
                subir_pdf_drive(nombre_pdf, pdf_path_local)
                os.remove(pdf_path_local)  # Limpiar local

                # Guardar registro
                new_row = pd.DataFrame([[consecutivo, usuario, estado, plu, codigo_gen,
                                         nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"), nombre_pdf]],
                                       columns=df_registros.columns)
                df_registros = pd.concat([df_registros,new_row], ignore_index=True)
                guardar_csv_drive(df_registros)

                st.success("✅ Registro guardado y PDF subido a Drive")

    # -------- TAB CONSOLIDADO --------
    with tabs[1]:
        st.dataframe(df_registros)
        descargar_csv(df_registros)
        for idx,row in df_registros.iterrows():
            st.markdown(f"**{row['Nombre Medicamento']}** - {row['Soporte']}")
