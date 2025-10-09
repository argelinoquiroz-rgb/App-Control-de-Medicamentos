import streamlit as st
import json
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")
st.title("💊 Control de Estado de Medicamentos")

# ==================================
# CARGAR CREDENCIALES DESDE st.secrets
# ==================================
try:
    creds_dict = json.loads(st.secrets["google_credentials"])

    # 🔹 Reemplazar \n por saltos de línea reales
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

except Exception as e:
    st.error(f"❌ No se pudo cargar 'google_credentials': {e}")
    st.stop()

# ==================================
# GUARDAR JSON EN ARCHIVO TEMPORAL
# ==================================
with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
    json.dump(creds_dict, tmpfile)
    service_file = tmpfile.name

# ==================================
# CREAR CONFIG TEMPORAL PARA PyDrive2
# ==================================
settings_json = {
    "client_config_backend": "service",
    "service_config": {
        "client_json_file_path": service_file
    }
}

with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmpfile:
    json.dump(settings_json, tmpfile)
    settings_file = tmpfile.name

# ==================================
# AUTENTICACIÓN CON GOOGLE DRIVE
# ==================================
try:
    gauth = GoogleAuth(settings_file=settings_file)
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    st.success("✅ Conexión exitosa con Google Drive mediante cuenta de servicio.")
except Exception as e:
    st.error(f"❌ Error autenticando con la cuenta de servicio: {e}")
    st.stop()

st.info("🎉 La autenticación con la cuenta de servicio funciona correctamente.")
