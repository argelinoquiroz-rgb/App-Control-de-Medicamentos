import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

os.makedirs("soportes", exist_ok=True)
os.makedirs("assets", exist_ok=True)
DATA_FILE = "registros_medicamentos.csv"

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def cargar_datos():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Fecha", "Estado", "Nombre", "PLU", "Código Genérico", "Soporte"])

def guardar_datos(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def guardar_soporte(archivo):
    if archivo is not None:
        file_path = os.path.join("soportes", archivo.name)
        with open(file_path, "wb") as f:
            f.write(archivo.getbuffer())
        return file_path
    return None

# ==============================
# ESTILO VISUAL
# ==============================
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #1B263B;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 30px;
    }
    .sub-title {
        color: #0D1B2A;
        font-size: 20px;
        font-weight: 600;
        margin-top: 20px;
        border-left: 4px solid #1B263B;
        padding-left: 10px;
    }
    .block {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================
# MENÚ PRINCIPAL (Pestañas superiores)
# ==============================
tabs = st.tabs(["🔐 Inicio de sesión", "💊 Registrar medicamento", "📋 Registros guardados", "➕ Crear usuario"])

# ==============================
# 1️⃣ INICIO DE SESIÓN
# ==============================
with tabs[0]:
    st.markdown("<div class='main-title'>🔐 Inicio de Sesión</div>", unsafe_allow_html=True)

    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if usuario == "admin" and contraseña == "123":
            st.success("✅ Inicio de sesión exitoso.")
        else:
            st.error("❌ Usuario o contraseña incorrectos.")

# ==============================
# 2️⃣ REGISTRAR MEDICAMENTO
# ==============================
with tabs[1]:
    st.markdown("<div class='main-title'>💊 Registrar Medicamento</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='sub-title'>Estado del medicamento</div>", unsafe_allow_html=True)
        explicaciones_estado = {
            "Agotado": "El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado y puede ser adquirido nuevamente.",
            "Desabastecido": "El medicamento no se encuentra disponible ni en el inventario interno ni en el mercado nacional.",
            "Descontinuado": "El medicamento ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria."
        }

        estado = st.selectbox("Selecciona el estado", list(explicaciones_estado.keys()))
        st.info(explicaciones_estado[estado])

    with st.container():
        st.markdown("<div class='sub-title'>Datos del medicamento</div>", unsafe_allow_html=True)
        fecha = datetime.today().strftime("%Y-%m-%d")
        st.text_input("📅 Fecha de registro", value=fecha, disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("💊 Nombre del medicamento")
            plu = st.text_input("🔢 PLU (Ejemplo: 12345_ABC)")
        with col2:
            # Autocompletar Código Genérico
            codigo_generico = ""
            if "_" in plu:
                codigo_generico = plu.split("_")[0]
            codigo_generico = st.text_input("🧬 Código Genérico", value=codigo_generico, disabled=True)

        soporte = st.file_uploader("📎 Subir soporte (obligatorio)", type=["pdf", "jpg", "png"])

        if st.button("💾 Guardar registro"):
            if not soporte:
                st.error("❌ Debes subir un soporte antes de guardar.")
            elif not nombre or not plu:
                st.warning("⚠️ Por favor completa todos los campos requeridos.")
            else:
                file_path = guardar_soporte(soporte)
                df = cargar_datos()
                nuevo = pd.DataFrame([{
                    "Fecha": fecha,
                    "Estado": estado,
                    "Nombre": nombre,
                    "PLU": plu,
                    "Código Genérico": codigo_generico,
                    "Soporte": file_path
                }])
                df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df)
                st.success("✅ Registro guardado correctamente.")

# ==============================
# 3️⃣ REGISTROS GUARDADOS
# ==============================
with tabs[2]:
    st.markdown("<div class='main-title'>📋 Registros Guardados</div>", unsafe_allow_html=True)

    df = cargar_datos()
    if df.empty:
        st.warning("⚠️ No hay registros guardados.")
    else:
        st.dataframe(df, use_container_width=True)

        for _, row in df.iterrows():
            if pd.notna(row["Soporte"]) and os.path.exists(row["Soporte"]):
                with open(row["Soporte"], "rb") as f:
                    st.download_button(
                        label=f"📥 Descargar soporte de {row['Nombre']}",
                        data=f,
                        file_name=os.path.basename(row["Soporte"]),
                        mime="application/octet-stream"
                    )

# ==============================
# 4️⃣ CREAR USUARIO
# ==============================
with tabs[3]:
    st.markdown("<div class='main-title'>➕ Crear Nuevo Usuario</div>", unsafe_allow_html=True)

    nuevo_usuario = st.text_input("👤 Nombre de usuario")
    nueva_contraseña = st.text_input("🔑 Contraseña", type="password")

    if st.button("Crear usuario"):
        if nuevo_usuario and nueva_contraseña:
            st.success(f"✅ Usuario '{nuevo_usuario}' creado correctamente.")
        else:
            st.warning("⚠️ Completa todos los campos para crear un usuario.")
