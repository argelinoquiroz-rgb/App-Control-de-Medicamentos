# app_estado_medicamentos.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import mimetypes
from PIL import Image

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", page_icon="💊", layout="wide")

# Ruta fija en OneDrive
BASE_DIR = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Documentos\Reportes\01_Informes Power BI\01_Analisis de Solicitudes y Ordenes de Compras\Actualiza Informes Phyton\control_estado_medicamentos"
os.makedirs(BASE_DIR, exist_ok=True)

USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_empresa.png")

os.makedirs(SOPORTES_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# ---------------- UTIL: usuarios ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USERS_FILE, index=False)

    df = pd.read_csv(USERS_FILE, dtype=str)
    df.columns = [c.strip().lower().replace("ñ","n") for c in df.columns]

    if "usuario" not in df.columns:
        for alt in ["user","username","usuario "]:
            if alt in df.columns:
                df.rename(columns={alt:"usuario"}, inplace=True)
                break
    if "contrasena" not in df.columns:
        for alt in ["contrasena","contraseña","password","passwd"]:
            if alt in df.columns:
                df.rename(columns={alt:"contrasena"}, inplace=True)
                break

    df["usuario"] = df["usuario"].astype(str).str.strip().str.lower()
    df["contrasena"] = df["contrasena"].astype(str).str.strip()
    return df[["usuario","contrasena"]]

def save_user(username,password):
    df = load_users()
    if username.lower().strip() in df["usuario"].values:
        return False, "Usuario ya existe"
    new = pd.DataFrame({"usuario":[username.lower().strip()],"contrasena":[password.strip()]})
    df = pd.concat([df,new],ignore_index=True)
    df.to_csv(USERS_FILE,index=False)
    return True,"Usuario creado correctamente ✅"

# ---------------- UTIL: registros ----------------
def load_records():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE,dtype=str)
    else:
        cols = ["consecutivo","fecha_hora","usuario","estado","plu","codigo_generico",
                "nombre_comercial","laboratorio","presentacion","observaciones","soporte"]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE,index=False)
        return df

def append_record(record:dict):
    df = load_records()
    df = pd.concat([df,pd.DataFrame([record])],ignore_index=True)
    df.to_csv(DATA_FILE,index=False)

def save_support_file(uploaded_file, consecutivo, nombre):
    extension = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{consecutivo}_{nombre.replace(' ','_')}{extension}"
    path = os.path.join(SOPORTES_DIR,safe_name)
    with open(path,"wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def guess_mime(path):
    mime,_ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"

# ---------------- UI: login ----------------
def show_logo_center():
    if os.path.exists(LOGO_PATH):
        img = Image.open(LOGO_PATH)
        st.image(img,width=220)
    else:
        st.markdown("<h3 style='text-align:center;'>💊</h3>",unsafe_allow_html=True)

def login_page():
    st.markdown("<div style='text-align:center; margin-top: 10px;'>",unsafe_allow_html=True)
    show_logo_center()
    st.markdown("<h2 style='text-align:center; color:#0D3B66;'>Control de Estado de Medicamentos</h2>",unsafe_allow_html=True)
    st.markdown("</div>")
    st.write("**Inicie sesión** para acceder al sistema.")
    col1,col2,col3 = st.columns([1,2,1])
    with col2:
        usuario_input = st.text_input("Usuario", key="login_usuario")
        contrasena_input = st.text_input("Contraseña", type="password", key="login_contrasena")
        if st.button("Iniciar sesión", use_container_width=True):
            users = load_users()
            match = ((users["usuario"]==usuario_input.strip().lower()) & 
                     (users["contrasena"]==contrasena_input.strip())).any()
            if match:
                st.session_state["usuario"] = usuario_input.strip().lower()
                st.session_state["logged_in"] = True
                st.success("✅ Inicio de sesión correcto.")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

# ---------------- UI: sidebar ----------------
def app_sidebar():
    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH,width=150)

    st.sidebar.markdown(f"**👤 Usuario:** `{st.session_state.get('usuario','')}`")
    st.sidebar.markdown("---")

    with st.sidebar.expander("➕ Crear usuario",expanded=False):
        new_user = st.text_input("Nuevo usuario", key="new_user")
        new_pass = st.text_input("Contraseña", type="password", key="new_pass")
        if st.button("Crear usuario", key="create_user_btn"):
            if not new_user or not new_pass:
                st.warning("Completa usuario y contraseña.")
            else:
                ok,msg = save_user(new_user,new_pass)
                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)

    st.sidebar.markdown("---")
    menu = st.sidebar.radio("📋 Navegación", ["Inicio","Registrar medicamento","Registros guardados","Gestión de usuarios"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Cerrar sesión"):
        for k in ["usuario","logged_in"]:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
    return menu

# ---------------- PAGES ----------------
def page_inicio():
    st.title("🏠 Inicio")
    st.info("Bienvenido al sistema de control de estado de medicamentos. Usa el menú lateral para navegar.")
    st.write("📂 Ruta base usada para archivos:")
    st.code(BASE_DIR)

def page_registrar():
    st.title("➕ Registrar medicamento")
    explicaciones_estado = {
        "Agotado": "🟡 **Agotado:** medicamento no disponible temporalmente.",
        "Desabastecido": "🔴 **Desabastecido:** no se encuentra disponible en inventario interno ni mercado.",
        "Descontinuado": "⚫ **Descontinuado:** retirado del mercado y no volverá a producirse."
    }
    estado = st.selectbox("Estado del medicamento", list(explicaciones_estado.keys()))
    st.info(explicaciones_estado[estado])

    fecha_actual = datetime.now().date()
    st.date_input("📅 Fecha de registro", value=fecha_actual, disabled=True)

    col1,col2 = st.columns(2)
    with col1:
        plu = st.text_input("🔢 PLU (ej. 12345_ABC)", key="plu_input").strip().upper()
    with col2:
        codigo_gen = plu.split("_")[0] if "_" in plu else ""
        st.text_input("🧬 Código Genérico", value=codigo_gen, disabled=True)

    nombre = st.text_input("💊 Nombre comercial", key="nombre_input").strip().upper()
    laboratorio = st.text_input("🏭 Laboratorio", key="lab_input").strip().upper()
    presentacion = st.text_input("📦 Presentación", key="pres_input").strip()
    observaciones = st.text_area("📝 Observaciones", key="obs_input").strip()
    soporte = st.file_uploader("📎 Subir soporte (OBLIGATORIO) — PDF/JPG/PNG", type=["pdf","jpg","jpeg","png"], key="soporte_input")

    if st.button("💾 Guardar registro"):
        if not (plu and nombre and soporte):
            st.error("Debes completar PLU, Nombre y subir el soporte.")
        else:
            df = load_records()
            consecutivo = str(len(df)+1)
            ruta_soporte = save_support_file(soporte, consecutivo, nombre)
            registro = {
                "consecutivo": consecutivo,
                "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": st.session_state.get("usuario",""),
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

    # Buscador por cualquier campo
    query = st.text_input("🔍 Buscar en registros")
    if query:
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        df_filtered = df[mask]
    else:
        df_filtered = df

    # Mostrar tabla de registros
    st.dataframe(df_filtered[["consecutivo","fecha_hora","usuario","estado","plu","codigo_generico",
                              "nombre_comercial","laboratorio","presentacion","observaciones"]],
                 use_container_width=True)

    # Mostrar botón de descarga por registro
    st.markdown("### ⬇️ Soportes")
    for idx,row in df_filtered.iterrows():
        soporte_path = row.get("soporte","")
        if os.path.exists(soporte_path):
            with open(soporte_path,"rb") as f:
                data_bytes = f.read()
            st.download_button(label=f"📥 Descargar soporte {row['consecutivo']}_{row['nombre_comercial']}",
                               data=data_bytes,
                               file_name=os.path.basename(soporte_path),
                               mime=guess_mime(soporte_path))
        else:
            st.warning(f"Soporte no encontrado para registro {row['consecutivo']}")

def page_gestion_usuarios():
    st.title("👥 Gestión de usuarios")
    users_df = load_users()
    st.dataframe(users_df,use_container_width=True)

# ---------------- FLOW ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    menu = app_sidebar()
    if menu=="Inicio": page_inicio()
    elif menu=="Registrar medicamento": page_registrar()
    elif menu=="Registros guardados": page_registros()
    elif menu=="Gestión de usuarios": page_gestion_usuarios()

