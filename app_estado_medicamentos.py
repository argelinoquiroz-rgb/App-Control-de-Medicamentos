import streamlit as st
import pandas as pd
import os
from datetime import datetime

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

# Logo (si existe)
logo_path = "assets/logo_empresa.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=200)

# ==============================
# TÍTULO PRINCIPAL
# ==============================
st.title("💊 Control de Estado de Medicamentos")
st.markdown("---")

# ==============================
# SELECCIÓN DE ESTADO (EN LA PARTE SUPERIOR)
# ==============================
st.subheader("⚙️ Estado del medicamento")

explicaciones_estado = {
    "Agotado": "🟡 **Agotado:** El medicamento no está disponible temporalmente en el inventario interno, pero sí existe en el mercado y puede ser adquirido nuevamente por el proveedor o distribuidor.",
    "Desabastecido": "🔴 **Desabastecido:** El medicamento no se encuentra disponible ni en el inventario interno ni en el mercado nacional. Existen dificultades en su producción, importación o distribución.",
    "Descontinuado": "⚫ **Descontinuado:** El medicamento ha sido retirado del mercado por decisión del fabricante o autoridad sanitaria y no volverá a producirse o comercializarse."
}

estado = st.selectbox(
    "Selecciona el estado actual del medicamento",
    options=list(explicaciones_estado.keys()),
    index=0,
    key="estado"
)

# Mostrar explicación automática del estado
st.markdown(explicaciones_estado[estado])
st.markdown("---")

# ==============================
# REGISTRO DE MEDICAMENTOS
# ==============================
st.subheader("📋 Información del medicamento")

col1, col2, col3 = st.columns(3)
with col1:
    plu = st.text_input("🔢 PLU del medicamento")
with col2:
    codigo_generico = st.text_input("🧬 Código genérico")
with col3:
    fecha = st.date_input("📅 Fecha de registro", value=datetime.today())

col4, col5, col6 = st.columns(3)
with col4:
    nombre = st.text_input("💊 Nombre comercial del medicamento")
with col5:
    laboratorio = st.text_input("🏭 Laboratorio fabricante")
with col6:
    presentacion = st.text_input("📦 Presentación (ej: Tabletas 500mg)")

observaciones = st.text_area("🗒️ Observaciones o comentarios adicionales")
archivo = st.file_uploader("📎 Subir soporte (opcional)", type=["pdf", "jpg", "png"])

# ==============================
# GUARDAR REGISTRO
# ==============================
if st.button("💾 Guardar registro"):
    if not (plu and nombre):
        st.error("⚠️ Por favor completa al menos los campos: *PLU* y *Nombre del medicamento*.")
    else:
        data_file = "registros_medicamentos.csv"
        nuevo_registro = {
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Estado": estado,
            "PLU": plu,
            "Código Genérico": codigo_generico,
            "Nombre Comercial": nombre,
            "Presentación": presentacion,
            "Laboratorio": laboratorio,
            "Observaciones": observaciones
        }

        if os.path.exists(data_file):
            df = pd.read_csv(data_file)
            df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
        else:
            df = pd.DataFrame([nuevo_registro])

        df.to_csv(data_file, index=False, encoding="utf-8-sig")

        st.success("✅ Registro guardado correctamente.")

        if archivo is not None:
            soporte_path = os.path.join("soportes", archivo.name)
            with open(soporte_path, "wb") as f:
                f.write(archivo.getbuffer())
            st.info(f"📎 Soporte guardado en: `{soporte_path}`")

# ==============================
# VISUALIZAR REGISTROS
# ==============================
st.markdown("---")
st.subheader("📊 Registros guardados")

data_file = "registros_medicamentos.csv"
if os.path.exists(data_file):
    df = pd.read_csv(data_file)
    st.dataframe(df)
else:
    st.warning("Aún no hay registros guardados.")
