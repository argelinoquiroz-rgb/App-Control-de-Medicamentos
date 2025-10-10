# app_estado_medicamentos.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import mimetypes
from PIL import Image

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", page_icon="💊", layout="wide")

# Si quieres forzar una ruta local específica, descomenta y ajusta la siguiente línea:
# ONE_DRIVE_DIR = r"C:\Users\lidercompras\OneDrive - pharmaser.com.co\Documentos\Reportes\01_Informes Power BI\01_Analisis de Solicitudes y Ordenes de Compras\Actualiza Informes Phyton\control_estado_medicamentos"
ONE_DRIVE_DIR = None  # o la ruta anterior si quieres forzarla

# Buscar ubicación de trabajo: primero cwd, luego ONE_DRIVE_DIR si existe allí.
CANDIDATES = [os.getcwd()]
if ONE_DRIVE_DIR:
    CANDIDATES.append(ONE_DRIVE_DIR)

BASE_DIR = None
for c in CANDIDATES:
    if os.path.isdir(c):
        BASE_DIR = c
        break
if BASE_DIR is None:
    BASE_DIR = os.getcwd()

USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
LOGO_CAND1 = os.path.join(BASE_DIR, "logo_empresa.png")
LOGO_CAND2 = os.path.join(BASE_DIR, "assets", "logo_empresa.png")

os.makedirs(SOPORTES_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)

# ---------------- UTIL: usuarios robusto ----------------
def load_users():
    # Si no existe, crear con admin por defecto
    if not os.path.exists(USERS_FILE):
        pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USERS_FILE, index=False)

    df = pd.read_csv(USERS_FILE, dtype=str)

    # Normalizar nombres de columnas: minúsculas, sin espacios, reemplazar ñ->n
    df.columns = [c.strip().lower().replace("ñ", "n") for c in df.columns]

    # Mapear columnas comunes a 'usuario' y 'contrasena'
    if "usuario" not in df.columns:
        # intentar detectar columna parecida
        for alt in ["user", "username", "usuario "]:
            if alt in df.columns:
                df.rename(columns={alt: "usuario"}, inplace=True)
                break
    if "contrasena" not in df.columns:
        for alt in ["contrasena", "contraseña", "password", "passwd"]:
            if alt in df.columns:
                df.rename(columns={alt: "contrasena"}, inplace=True)
                break

    # Si luego de todo falta alguna columna, regenerar archivo por seguridad
    if "usuario" not in df.columns or "contrasena" not in df.columns or df.empty:
        pd.DataFrame({"usuario": ["admin"], "contrasena": ["250382"]}).to_csv(USERS_FILE, index=False)
        df = pd.read_csv(USERS_FILE, dtype=str)
        df.columns = [c.strip().lower().replace("ñ", "n") for c in df.columns]

    # limpieza de valores
    df["usuario"] = df["usuario"].astype(str).str.strip().str.lower()
    df["contrasena"] = df["contrasena"].astype(str).str.strip()

    return df[["usuario", "contrasena"]]

def save_user(username, password):
    df = load_users()
    if username.lower().strip() in df["usuario"].values:
        return False, "Usuario ya existe"
    new = pd.DataFrame({"usuario":[username.lower().strip()], "contrasena":[password.strip()]})
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True, "Usuario creado"

# ---------------- UTIL: registros ----------------
def load_records():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, dtype=str)
    else:
        cols = ["fecha_hora", "usuario", "estado", "plu", "codigo_generico",
                "nombre_comercial", "laboratorio", "presentacion", "observaciones", "soporte"]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE, index=False)
        return df

def append_record(record: dict):
    df = load_records()
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def save_support_file(uploaded_file):
    # crear nombre único para evitar sobreescrituras
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = f"{ts}_{uploaded_file.name.replace(' ', '_')}"
    path = os.path.join(SOPORTES_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

def guess_mime(path):
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"

# ---------------- UI: login ----------------
def show_logo_center():
    if os.path.exists(LOGO_CAND1):
        try:
            img = Image.open(LOGO_CAND1)
            st.image(img, width=200)
            return
        except Exception:
            pass
    if os.path.exists(LOGO_CAND2):
        try:
            img = Image.open(LOGO_CAND2)
            st.image(img, width=200)
            return
        except Exception:
            pass
    # fallback
    st.markdown("<h3 style='text-align:center;'>💊</h3>", unsafe_allow_html=True)

def login_page():
    st.markdown("<div style='text-align:center; margin-top: 10px;'>", unsafe_allow_html=True)
    show_logo_center()
    st.markdown("<h2 style='text-align:center; color:#0D3B66;'>Control de Estado de Medicamentos</h2>", unsafe_allow_html=True)
    st.markdown("</div>")
    st.write("")
    st.write("**Inicie sesión** para acceder al sistema.")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        usuario_input = st.text_input("Usuario", key="login_usuario")
        contrasena_input = st.text_input("Contraseña", type="password", key="login_contrasena")
        if st.button("Iniciar sesión", use_container_width=True):
            users = load_users()
            match = ((users["usuario"] == str(usuario_input).strip().lower()) &
                     (users["contrasena"] == str(contrasena_input).strip())).any()
            if match:
                st.session_state["usuario"] = usuario_input.strip().lower()
                st.session_state["logged_in"] = True
                st.success("✅ Inicio de sesión correcto.")
                st.experimental_rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos. Revisa usuarios.csv o crea el usuario en 'Crear usuario' (lateral).")

# ---------------- UI: app principal ----------------
def app_sidebar():
    # Mostrar logo pequeño arriba en sidebar
    if os.path.exists(LOGO_CAND1):
        try:
            st.sidebar.image(LOGO_CAND1, width=140)
        except Exception:
            pass
    elif os.path.exists(LOGO_CAND2):
        try:
            st.sidebar.image(LOGO_CAND2, width=140)
        except Exception:
            pass
    else:
        st.sidebar.markdown("## 💊 Sistema")

    st.sidebar.markdown(f"**Usuario:** `{st.session_state.get('usuario','')}`")
    st.sidebar.markdown("---")

    # Expander para crear usuario (lateral, según requeriste)
    with st.sidebar.expander("➕ Crear usuario", expanded=False):
        new_user = st.text_input("Nuevo usuario", key="new_user")
        new_pass = st.text_input("Contraseña", type="password", key="new_pass")
        if st.button("Crear usuario", key="create_user_btn"):
            if not new_user or not new_pass:
                st.warning("Completa usuario y contraseña.")
            else:
                ok, msg = save_user(new_user, new_pass)
                if ok:
                    st.success(msg)
                else:
                    st.warning(msg)

    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["Inicio","Registrar medicamento","Registros guardados","Gestión de usuarios"])
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Cerrar sesión"):
        for k in ["usuario","logged_in"]:
            if k in st.session_state: del st.session_state[k]
        st.experimental_rerun()

    return menu

def page_inicio():
    st.title("🏠 Inicio")
    st.info("Seleccione una opción en el panel lateral. Registro, consulta y administración de usuarios están disponibles.")
    st.write("Ruta base usada para archivos:", BASE_DIR)

def page_registrar():
    st.title("➕ Registrar medicamento")
    explicaciones_estado = {
        "Agotado": "🟡 **Agotado:** El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado y puede ser adquirido nuevamente por el proveedor o distribuidor.",
        "Desabastecido": "🔴 **Desabastecido:** El medicamento no se encuentra disponible ni en el inventario interno ni en el mercado nacional. Existen dificultades en su producción, importación o distribución.",
        "Descontinuado": "⚫ **Descontinuado:** El medicamento ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria y no volverá a producirse o comercializarse."
    }

    estado = st.selectbox("Estado", options=list(explicaciones_estado.keys()))
    st.info(explicaciones_estado[estado])

    # Fecha automática NO editable
    fecha_actual = datetime.now().date()
    st.date_input("Fecha de registro", value=fecha_actual, disabled=True)

    # PLU y Código Genérico autocompletado
    col1, col2 = st.columns(2)
    with col1:
        plu = st.text_input("🔢 PLU (ej. 12345_ABC)", key="plu_input").strip().upper()
    with col2:
        codigo_gen = ""
        if "_" in plu:
            codigo_gen = plu.split("_")[0]
        st.text_input("🧬 Código Genérico", value=codigo_gen, disabled=True)

    # Campos adicionales
    nombre = st.text_input("💊 Nombre comercial", key="nombre_input").strip().upper()
    laboratorio = st.text_input("🏭 Laboratorio", key="lab_input").strip().upper()
    presentacion = st.text_input("📦 Presentación (ej. Tabletas 500mg)", key="pres_input").strip()
    observaciones = st.text_area("📝 Observaciones", key="obs_input").strip()

    soporte = st.file_uploader("📎 Subir soporte (OBLIGATORIO) — PDF/JPG/PNG", type=["pdf","jpg","jpeg","png"], key="soporte_input")

    # Prevención doble guardado
    if "guardado_flag" not in st.session_state:
        st.session_state["guardado_flag"] = False

    if st.button("💾 Guardar registro"):
        if st.session_state.get("guardado_flag", False):
            st.warning("El registro ya fue guardado. Para agregar otro, recarga la página o limpia el formulario.")
        else:
            # Validaciones
            if not (plu and nombre and soporte):
                st.error("Debes completar PLU, Nombre y subir el soporte.")
            else:
                # Guardar soporte
                ruta_soporte = save_support_file(soporte)
                registro = {
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
                st.info(f"Soporte guardado en: `{ruta_soporte}`")
                st.session_state["guardado_flag"] = True

def page_registros():
    st.title("📂 Registros guardados")
    df = load_records()
    if df.empty:
        st.info("No hay registros guardados aún.")
        return

    # Mostrar tabla profesional
    st.dataframe(df[["fecha_hora","usuario","estado","plu","codigo_generico","nombre_comercial","laboratorio","presentacion","observaciones"]], use_container_width=True)

    # Descargas debajo de la tabla
    st.markdown("### ⬇️ Descargas de soportes")
    for idx, row in df.iterrows():
        soporte_path = row.get("soporte","")
        if isinstance(soporte_path, str) and os.path.exists(soporte_path):
            mime = guess_mime(soporte_path)
            label = f"📥 Descargar: {os.path.basename(soporte_path)} — {row.get('nombre_comercial','')}"
            with open(soporte_path, "rb") as f:
                data_bytes = f.read()
            st.download_button(label=label, data=data_bytes, file_name=os.path.basename(soporte_path), mime=mime)
        else:
            st.info(f"Soporte no encontrado para registro {idx}")

def page_gestion_usuarios():
    st.title("👥 Gestión de usuarios")
    st.markdown("Crear nuevo usuario (también puedes crear desde el expander en el lateral).")
    users_df = load_users()
    st.dataframe(users_df, use_container_width=True)

# ---------------- FLOW ----------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# If not logged, show login page
if not st.session_state["logged_in"]:
    login_page()
else:
    menu = app_sidebar()
    if menu == "Inicio":
        page_inicio()
    elif menu == "Registrar medicamento":
        page_registrar()
    elif menu == "Registros guardados":
        page_registros()
    elif menu == "Gestión de usuarios":
        page_gestion_usuarios()
