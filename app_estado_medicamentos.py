import streamlit as st
import pandas as pd
import os
from datetime import datetime
import mimetypes
from PIL import Image

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", page_icon="💊", layout="wide")

# Ruta fija en OneDrive (¡AJUSTADA!)
ONE_DRIVE_DIR = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Documentos\Reportes\01_Informes Power BI\01_Analisis de Solicitudes y Ordenes de Compras\Actualiza Informes Phyton\control_estado_medicamentos"

os.makedirs(ONE_DRIVE_DIR, exist_ok=True)
BASE_DIR = ONE_DRIVE_DIR

USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_empresa.png")

os.makedirs(SOPORTES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# DEBUG: Mostrar rutas en la app (puedes quitarlo después de comprobar)
st.write(f"ONE_DRIVE_DIR: {ONE_DRIVE_DIR}")
st.write(f"SOPORTES_DIR: {SOPORTES_DIR}")
st.write(f"USERS_FILE: {USERS_FILE}")
st.write(f"DATA_FILE: {DATA_FILE}")

# ---------------- UTIL ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USERS_FILE, index=False)
    df = pd.read_csv(USERS_FILE, dtype=str)
    df.columns = [c.strip().lower().replace("ñ", "n") for c in df.columns]
    df["usuario"] = df["usuario"].astype(str).str.strip().str.lower()
    df["contrasena"] = df["contrasena"].astype(str).str.strip()
    return df[["usuario", "contrasena"]]

def save_user(username, password):
    df = load_users()
    if username.lower().strip() in df["usuario"].values:
        return False, "Usuario ya existe"
    new = pd.DataFrame({"usuario": [username.lower().strip()], "contrasena": [password.strip()]})
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True, "Usuario creado correctamente ✅"

def load_records():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype=str)
        df.fillna("", inplace=True)
        return df
    else:
        cols = [
            "consecutivo", "fecha_hora", "usuario", "estado", "plu", "codigo_generico",
            "nombre_comercial", "laboratorio", "presentacion", "observaciones", "soporte"
        ]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE, index=False)
        return df

def append_record(record: dict):
    df = load_records()
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def save_support_file(uploaded_file, consecutivo, nombre):
    ext = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{consecutivo}_{nombre.replace(' ', '_')}{ext}"
    path = os.path.join(SOPORTES_DIR, safe_name)
    # DEBUG: Mostrar ruta de guardado en la app
    st.write(f"Guardando soporte en: {path}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def guess_mime(path):
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"

# ---------------- SIDEBAR LOGIN/REGISTER ----------------
def sidebar_login():
    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, width=150)
    else:
        st.sidebar.markdown("<h3 style='text-align:center;'>💊</h3>", unsafe_allow_html=True)
    st.sidebar.title("Control de Medicamentos")
    menu = st.sidebar.radio("Acción", ["Iniciar sesión", "Crear usuario"], horizontal=True)

    if menu == "Iniciar sesión":
        usuario = st.sidebar.text_input("Usuario", key="sidebar_login_usuario")
        contrasena = st.sidebar.text_input("Contraseña", type="password", key="sidebar_login_contrasena")
        if st.sidebar.button("Iniciar sesión"):
            users = load_users()
            match = ((users["usuario"] == usuario.strip().lower()) &
                     (users["contrasena"] == contrasena.strip())).any()
            if match:
                st.session_state["usuario"] = usuario.strip().lower()
                st.session_state["logged_in"] = True
                st.success("✅ Inicio de sesión correcto.")
                st.rerun()  # Usar st.rerun() moderno
            else:
                st.sidebar.error("❌ Usuario o contraseña incorrectos.")
    else:  # Crear usuario
        nuevo_usuario = st.sidebar.text_input("Nuevo usuario", key="sidebar_nuevo_usuario")
        nueva_contrasena = st.sidebar.text_input("Nueva contraseña", type="password", key="sidebar_nueva_contrasena")
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
    selected = st.radio(
        "Seleccione una opción",
        opciones,
        horizontal=True, key="main_menu_radio")
    return selected

# ---------------- PAGES ----------------
def page_registrar():
    st.title("➕ Registrar medicamento")

    estados = {
        "Agotado": "🟡 Agotado: No disponible temporalmente en inventario interno.",
        "Desabastecido": "🔴 Desabastecido: No disponible en inventario ni mercado nacional.",
        "Descontinuado": "⚫ Descontinuado: Retirado del mercado definitivamente."
    }

    estado = st.selectbox("Estado del medicamento", list(estados.keys()))
    st.info(estados[estado])

    fecha_actual = datetime.now().date()
    st.date_input("📅 Fecha de registro", value=fecha_actual, disabled=True)

    col1, col2 = st.columns(2)
    with col1:
        plu = st.text_input("🔢 PLU", key="plu_input").strip().upper()
    with col2:
        codigo_gen = plu.split("_")[0] if "_" in plu else ""
        st.text_input("🧬 Código Genérico", value=codigo_gen, disabled=True)

    nombre = st.text_input("💊 Nombre comercial", key="nombre_input").strip().upper()
    laboratorio = st.text_input("🏭 Laboratorio", key="lab_input").strip().upper()
    presentacion = st.text_input("📦 Presentación", key="pres_input").strip()
    observaciones = st.text_area("📝 Observaciones", key="obs_input").strip()
    soporte = st.file_uploader("📎 Subir soporte (OBLIGATORIO) — PDF/JPG/PNG", type=["pdf", "jpg", "jpeg", "png"], key="soporte_input")

    if st.button("💾 Guardar registro"):
        if not (plu and nombre and soporte):
            st.error("Debes completar PLU, Nombre y subir el soporte.")
        else:
            df = load_records()
            consecutivo = len(df) + 1
            ruta_soporte = save_support_file(soporte, consecutivo, nombre)
            registro = {
                "consecutivo": consecutivo,
                "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": st.session_state.get("usuario", ""),
                "estado": estado,
                "plu": plu,
                "codigo_generico": codigo_gen,
                "nombre_comercial": nombre,
                "laboratorio": laboratorio,
                "presentacion": presentacion,
                "observaciones": observaciones,
                "soporte": ruta_soporte
            }
            append_record(registro)
            st.success("✅ Registro guardado correctamente.")

def page_registros():
    st.title("📂 Registros guardados")
    df = load_records()
    if df.empty:
        st.info("No hay registros guardados aún.")
        return

    busqueda = st.text_input("🔍 Buscar registro por cualquier campo")
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False, na=False).any(), axis=1)
        df_filtered = df[mask]
    else:
        df_filtered = df

    display_df = df_filtered.copy()
    display_df.drop(columns=["soporte"], inplace=True, errors='ignore')
    st.dataframe(display_df, use_container_width=True)

    st.markdown("### ⬇️ Descarga de soportes")
    for idx, row in df_filtered.iterrows():
        soporte_path = row.get("soporte", "")
        if os.path.exists(soporte_path):
            mime = guess_mime(soporte_path)
            with open(soporte_path, "rb") as f:
                data_bytes = f.read()
            st.download_button(
                label=f"📥 Descargar {row.get('nombre_comercial', '')}",
                data=data_bytes,
                file_name=os.path.basename(soporte_path),
                mime=mime
            )

def page_gestion_usuarios():
    st.title("👥 Gestión de usuarios")
    users_df = load_users()
    st.dataframe(users_df, use_container_width=True)

# ---------------- FLOW PRINCIPAL ----------------
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
