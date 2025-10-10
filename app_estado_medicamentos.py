import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# Crear carpetas necesarias
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
    df.to_csv(DATA_FILE, index=False)

def guardar_soporte(archivo):
    if archivo is not None:
        file_path = os.path.join("soportes", archivo.name)
        with open(file_path, "wb") as f:
            f.write(archivo.getbuffer())
        return file_path
    return None

# ==============================
# MENÚ LATERAL PRINCIPAL
# ==============================
st.sidebar.title("⚙️ Panel de Control")

menu = st.sidebar.radio(
    "Selecciona una opción",
    ["Inicio de sesión", "Registrar medicamento", "Registros guardados"]
)

# Subpestaña en el panel lateral para crear usuarios
with st.sidebar.expander("➕ Crear nuevo usuario"):
    nuevo_usuario = st.text_input("Nuevo usuario", key="nuevo_usuario")
    nueva_contraseña = st.text_input("Nueva contraseña", type="password", key="nueva_contraseña")
    if st.button("Crear usuario"):
        if nuevo_usuario and nueva_contraseña:
            st.success(f"Usuario '{nuevo_usuario}' creado correctamente.")
        else:
            st.warning("Por favor completa todos los campos.")

# ==============================
# 1️⃣ INICIO DE SESIÓN
# ==============================
if menu == "Inicio de sesión":
    st.title("🔐 Inicio de Sesión")

    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario == "admin" and contraseña == "123":
            st.success("✅ Inicio de sesión exitoso.")
        else:
            st.error("❌ Usuario o contraseña incorrectos.")

# ==============================
# 2️⃣ REGISTRAR MEDICAMENTO
# ==============================
elif menu == "Registrar medicamento":
    st.title("💊 Registrar medicamento")

    # Estado en la parte superior
    explicaciones_estado = {
        "Agotado": "El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado y puede ser adquirido nuevamente por el proveedor o distribuidor.",
        "Desabastecido": "El medicamento no se encuentra disponible ni en el inventario interno ni en el mercado nacional. Existen dificultades en su producción, importación o distribución.",
        "Descontinuado": "El medicamento ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria y no volverá a producirse o comercializarse."
    }

    estado = st.selectbox("Estado del medicamento", options=list(explicaciones_estado.keys()))
    st.info(explicaciones_estado[estado])

    # Fecha automática (no editable)
    fecha = datetime.today().strftime("%Y-%m-%d")
    st.text_input("Fecha de registro", value=fecha, disabled=True)

    # Datos del medicamento
    nombre = st.text_input("Nombre del medicamento")
    plu = st.text_input("PLU (Formato: 12345_ABC)")

    # Código Genérico automático
    codigo_generico = ""
    if "_" in plu:
        codigo_generico = plu.split("_")[0]
    codigo_generico = st.text_input("Código Genérico", value=codigo_generico, disabled=True)

    # Subir soporte obligatorio
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
elif menu == "Registros guardados":
    st.title("📋 Registros guardados")

    df = cargar_datos()
    if df.empty:
        st.warning("⚠️ No hay registros guardados.")
    else:
        st.dataframe(df, use_container_width=True)

        # Botones de descarga de soporte
        for _, row in df.iterrows():
            if pd.notna(row["Soporte"]) and os.path.exists(row["Soporte"]):
                with open(row["Soporte"], "rb") as f:
                    st.download_button(
                        label=f"📥 Descargar soporte de {row['Nombre']}",
                        data=f,
                        file_name=os.path.basename(row["Soporte"]),
                        mime="application/octet-stream"
                    )
