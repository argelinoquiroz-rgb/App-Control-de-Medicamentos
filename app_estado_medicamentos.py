import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Control de Estado de Medicamentos",
    page_icon="💊",
    layout="wide"
)

# Crear carpetas necesarias
os.makedirs("soportes", exist_ok=True)
os.makedirs("assets", exist_ok=True)

DATA_FILE = "registros_medicamentos.csv"
USERS_FILE = "usuarios.csv"

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def cargar_usuarios():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE)
    else:
        # Crear usuario admin por defecto
        df = pd.DataFrame([["admin", "250382"]], columns=["usuario", "contraseña"])
        df.to_csv(USERS_FILE, index=False)
        return df

def guardar_usuario(usuario, contraseña):
    df = cargar_usuarios()
    if usuario in df["usuario"].values:
        st.warning("⚠️ El usuario ya existe.")
    else:
        nuevo = pd.DataFrame([[usuario, contraseña]], columns=["usuario", "contraseña"])
        df = pd.concat([df, nuevo], ignore_index=True)
        df.to_csv(USERS_FILE, index=False)
        st.success("✅ Usuario creado exitosamente.")

def cargar_datos():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Fecha", "PLU", "Código Genérico", "Nombre", "Estado", "Observaciones", "Soporte"])

def guardar_registro(data):
    df = cargar_datos()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def descargar_soporte(ruta):
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        href = f'<a href="data:file/octet-stream;base64,{b64}" download="{os.path.basename(ruta)}">📄 Descargar Soporte</a>'
        return href
    else:
        return "❌ Archivo no encontrado."

# ==============================
# LOGIN
# ==============================
def login():
    st.title("💊 Control de Estado de Medicamentos")
    st.markdown("### 🔐 Iniciar sesión para continuar")

    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Ingresar", use_container_width=True):
        usuarios = cargar_usuarios()
        if ((usuarios["usuario"] == usuario) & (usuarios["contraseña"] == contraseña)).any():
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.success("Inicio de sesión exitoso ✅")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

# ==============================
# APLICACIÓN PRINCIPAL
# ==============================
def app_principal():
    # --- Panel lateral profesional ---
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>💊 Sistema de Control</h2>", unsafe_allow_html=True)
        st.markdown("---")

        menu = st.radio(
            "Navegación",
            ["🏠 Inicio", "➕ Registrar Medicamento", "📦 Registros Guardados", "👥 Gestión de Usuarios"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown(f"**Usuario activo:** `{st.session_state['usuario']}`")
        if st.button("🔓 Cerrar sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    # --- Contenido principal según el menú ---
    if menu == "🏠 Inicio":
        st.markdown("## 🏠 Bienvenido al Sistema de Control de Medicamentos")
        st.write("Use el panel lateral para registrar, consultar o administrar usuarios del sistema.")
        st.markdown("---")

    elif menu == "➕ Registrar Medicamento":
        st.markdown("## ➕ Registrar Medicamento")

        # Estados con explicación
        explicaciones_estado = {
            "Agotado": "El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado.",
            "Desabastecido": "El medicamento no se encuentra disponible ni en el inventario interno ni en el mercado nacional.",
            "Descontinuado": "El medicamento ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria."
        }

        estado = st.selectbox("Estado", list(explicaciones_estado.keys()))
        st.info(explicaciones_estado[estado])

        plu = st.text_input("PLU")
        nombre = st.text_input("Nombre del Medicamento")
        observaciones = st.text_area("Observaciones")
        soporte = st.file_uploader("📎 Subir soporte (obligatorio)", type=["pdf", "jpg", "png"])

        # Fecha automática (no editable)
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        st.write(f"📅 Fecha del registro: **{fecha_actual}**")

        # Código genérico automático desde el PLU
        codigo_generico = ""
        if "_" in plu:
            codigo_generico = plu.split("_")[0]
        st.text_input("Código Genérico", value=codigo_generico, disabled=True)

        if st.button("💾 Guardar Registro", use_container_width=True):
            if not soporte:
                st.error("❌ Debes subir un archivo de soporte antes de guardar.")
            else:
                ruta_soporte = os.path.join("soportes", soporte.name)
                with open(ruta_soporte, "wb") as f:
                    f.write(soporte.getbuffer())

                data = {
                    "Fecha": fecha_actual,
                    "PLU": plu,
                    "Código Genérico": codigo_generico,
                    "Nombre": nombre,
                    "Estado": estado,
                    "Observaciones": observaciones,
                    "Soporte": ruta_soporte
                }
                guardar_registro(data)
                st.success("✅ Registro guardado correctamente.")

    elif menu == "📦 Registros Guardados":
        st.markdown("## 📦 Registros Guardados")
        df = cargar_datos()
        if df.empty:
            st.info("No hay registros guardados aún.")
        else:
            st.dataframe(df[["Fecha", "PLU", "Código Genérico", "Nombre", "Estado", "Observaciones"]], use_container_width=True)

            for i, row in df.iterrows():
                st.markdown(descargar_soporte(row["Soporte"]), unsafe_allow_html=True)

    elif menu == "👥 Gestión de Usuarios":
        st.markdown("## 👥 Gestión de Usuarios")
        st.subheader("Crear nuevo usuario")

        nuevo_usuario = st.text_input("Nuevo usuario")
        nueva_contraseña = st.text_input("Contraseña", type="password")

        if st.button("➕ Crear Usuario", use_container_width=True):
            guardar_usuario(nuevo_usuario, nueva_contraseña)

# ==============================
# EJECUCIÓN
# ==============================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
else:
    app_principal()
