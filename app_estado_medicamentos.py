import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from fpdf import FPDF
import urllib.request

# ---------------- CONFIGURACIÓN STREAMLIT ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", page_icon="💊", layout="wide")

# ---------------- GOOGLE DRIVE SETTINGS ----------------
GOOGLE_DRIVE_FOLDER_ID = "1itzZF2zLNLmGEDm-ok8FD_rhadaIUM_Z"  # Carpeta destino en Drive
SERVICE_ACCOUNT_FILE = "service_account.json"

# Guardar credenciales desde st.secrets si existen
if "service_account" in st.secrets:
    creds = dict(st.secrets["service_account"])
    with open(SERVICE_ACCOUNT_FILE, "w") as f:
        json.dump(creds, f)

# ---------------- AUTENTICACIÓN GOOGLE DRIVE ----------------
def authenticate_drive():
    """Autenticación con cuenta de servicio."""
    gauth = GoogleAuth(settings={
        "client_config_backend": "service",
        "service_config_file": SERVICE_ACCOUNT_FILE
    })
    gauth.ServiceAuth()
    return GoogleDrive(gauth)

# ---------------- UTILIDADES DE DATOS ----------------
def load_users():
    if not os.path.exists("usuarios.csv"):
        pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv("usuarios.csv", index=False)
    df = pd.read_csv("usuarios.csv", dtype=str)
    df.columns = [c.strip().lower().replace("ñ", "n") for c in df.columns]
    df["usuario"] = df["usuario"].str.strip().str.lower()
    df["contrasena"] = df["contrasena"].str.strip()
    return df

def save_user(username, password):
    df = load_users()
    if username.lower().strip() in df["usuario"].values:
        return False, "Usuario ya existe"
    new = pd.DataFrame({"usuario": [username.lower().strip()], "contrasena": [password.strip()]})
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv("usuarios.csv", index=False)
    return True, "Usuario creado correctamente ✅"

def load_records():
    if os.path.exists("registros_medicamentos.csv"):
        df = pd.read_csv("registros_medicamentos.csv", dtype=str).fillna("")
        return df
    else:
        cols = [
            "consecutivo", "fecha_hora", "usuario", "estado", "plu",
            "codigo_generico", "nombre_comercial", "laboratorio",
            "observaciones", "soporte"
        ]
        pd.DataFrame(columns=cols).to_csv("registros_medicamentos.csv", index=False)
        return pd.DataFrame(columns=cols)

def append_record(record: dict):
    df = load_records()
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv("registros_medicamentos.csv", index=False)

# ---------------- FUNCIÓN PARA GENERAR PDF ----------------
def generar_pdf(datos, ruta_pdf):
    fuente_path = "DejaVuSans.ttf"

    # Descargar fuente si no existe
    if not os.path.exists(fuente_path):
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/version_2_37/ttf/DejaVuSans.ttf"
        urllib.request.urlretrieve(url, fuente_path)

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", fuente_path, uni=True)
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(200, 10, txt="REGISTRO DE MEDICAMENTO", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("DejaVu", "", 12)
    for campo, valor in datos.items():
        texto = str(valor).replace("\n", " ").strip()
        pdf.multi_cell(0, 10, f"{campo}: {texto}")

    pdf.output(ruta_pdf)

# ---------------- GUARDAR SOPORTE EN DRIVE ----------------
def save_support_file(uploaded_file, consecutivo, nombre, drive, folder_id):
    ext = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{consecutivo}_{nombre.replace(' ', '_')}{ext}"
    temp_path = f"temp_{safe_name}"

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_drive = drive.CreateFile({'title': safe_name, "parents": [{"id": folder_id}]})
    file_drive.SetContentFile(temp_path)
    file_drive.Upload()
    file_drive.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
    os.remove(temp_path)

    return f"https://drive.google.com/uc?id={file_drive['id']}&export=download"

# ---------------- LOGIN ----------------
def sidebar_login():
    st.sidebar.title("💊 Control de Medicamentos")
    menu = st.sidebar.radio("Acción", ["Iniciar sesión", "Crear usuario"], horizontal=True)

    if menu == "Iniciar sesión":
        usuario = st.sidebar.text_input("Usuario")
        contrasena = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Iniciar sesión"):
            users = load_users()
            match = ((users["usuario"] == usuario.strip().lower()) &
                     (users["contrasena"] == contrasena.strip())).any()
            if match:
                st.session_state["usuario"] = usuario.strip().lower()
                st.session_state["logged_in"] = True
                st.success("✅ Inicio de sesión correcto.")
                st.rerun()
            else:
                st.sidebar.error("❌ Usuario o contraseña incorrectos.")
    else:
        nuevo_usuario = st.sidebar.text_input("Nuevo usuario")
        nueva_contrasena = st.sidebar.text_input("Nueva contraseña", type="password")
        if st.sidebar.button("Crear usuario"):
            ok, msg = save_user(nuevo_usuario, nueva_contrasena)
            if ok:
                st.sidebar.success(msg)
            else:
                st.sidebar.error(msg)

# ---------------- MENÚ SUPERIOR ----------------
def main_menu():
    opciones = ["Registrar medicamento", "Registros guardados"]
    if st.session_state.get("usuario") == "admin":
        opciones.append("Gestión de usuarios")
    return st.radio("Seleccione una opción", opciones, horizontal=True)

# ---------------- PÁGINAS ----------------
def page_registrar():
    st.title("➕ Registrar medicamento")

    estados = {
        "Agotado": "🟡 Agotado: No disponible temporalmente en inventario interno.",
        "Desabastecido": "🔴 Desabastecido: No disponible en inventario ni mercado nacional.",
        "Descontinuado": "⚫ Descontinuado: Retirado del mercado definitivamente."
    }

    estado = st.selectbox("Estado del medicamento", list(estados.keys()))
    st.info(estados[estado])

    col1, col2 = st.columns(2)
    with col1:
        plu = st.text_input("🔢 PLU").strip().upper()
    with col2:
        codigo_gen = plu.split("_")[0] if "_" in plu else ""
        st.text_input("🧬 Código Genérico", value=codigo_gen, disabled=True)

    nombre = st.text_input("💊 Nombre comercial").strip().upper()
    laboratorio = st.text_input("🏭 Laboratorio").strip().upper()
    observaciones = st.text_area("📝 Observaciones").strip()
    soporte = st.file_uploader("📎 Subir soporte (PDF/JPG/PNG)", type=["pdf","jpg","jpeg","png"])

    if st.button("💾 Guardar registro"):
        if not (plu and nombre and soporte):
            st.error("Debes completar PLU, Nombre y subir el soporte.")
        else:
            df = load_records()
            consecutivo = len(df) + 1
            drive = authenticate_drive()

            # Generar PDF
            datos = {
                "Consecutivo": consecutivo,
                "Fecha y hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Usuario": st.session_state.get("usuario", ""),
                "Estado": estado,
                "PLU": plu,
                "Código genérico": codigo_gen,
                "Nombre comercial": nombre,
                "Laboratorio": laboratorio,
                "Observaciones": observaciones
            }
            ruta_pdf = f"Registro_{consecutivo}_{nombre.replace(' ', '_')}.pdf"
            generar_pdf(datos, ruta_pdf)

            ruta_soporte = save_support_file(soporte, consecutivo, nombre, drive, GOOGLE_DRIVE_FOLDER_ID)
            registro = {
                **{k.lower(): v for k, v in datos.items()},
                "soporte": ruta_soporte
            }
            append_record(registro)
            st.success("✅ Registro guardado correctamente.")
            os.remove(ruta_pdf)

def page_registros():
    st.title("📂 Registros guardados")
    df = load_records()
    if df.empty:
        st.info("No hay registros guardados aún.")
        return

    busqueda = st.text_input("🔍 Buscar registro por cualquier campo")
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False, na=False).any(), axis=1)
        df = df[mask]

    df_vista = df.copy()
    df_vista.drop(columns=["soporte"], inplace=True, errors='ignore')
    st.dataframe(df_vista, use_container_width=True)

    st.markdown("### ⬇️ Descarga de soportes")
    for _, row in df.iterrows():
        soporte_url = row.get("soporte", "")
        if soporte_url:
            st.markdown(f"<a href='{soporte_url}' target='_blank'>📥 Descargar {row.get('nombre_comercial', '')}</a>", unsafe_allow_html=True)

def page_gestion_usuarios():
    st.title("👥 Gestión de usuarios")
    users_df = load_users()
    st.dataframe(users_df, use_container_width=True)

# ---------------- FLUJO PRINCIPAL ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    sidebar_login()
else:
    st.sidebar.markdown(f"👤 Usuario: **{st.session_state.get('usuario','')}**")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["logged_in"] = False
        st.session_state["usuario"] = ""
        st.rerun()

    seleccion = main_menu()
    if seleccion == "Registrar medicamento":
        page_registrar()
    elif seleccion == "Registros guardados":
        page_registros()
    elif seleccion == "Gestión de usuarios":
        page_gestion_usuarios()
