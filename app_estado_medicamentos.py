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

# Crear archivo de usuarios si no existe
if not os.path.exists(USERS_FILE):
    df_usuarios = pd.DataFrame([{
        "usuario": "admin",
        "contrasena": "1234",
        "correo": "admin@pharmaser.com.co"
    }])
    df_usuarios.to_csv(USERS_FILE, index=False)
else:
    df_usuarios = pd.read_csv(USERS_FILE)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()

# ==============================
# PANEL LATERAL
# ==============================
st.sidebar.header("💊 Control de acceso")

# ---- LOGIN ----
with st.sidebar.expander("🔐 Iniciar sesión", expanded=True):
    if "usuario" in st.session_state:
        st.success(f"Sesión activa: {st.session_state['usuario']}")
        if st.button("Cerrar sesión"):
            st.session_state.clear()
            st.rerun()
    else:
        usuario_input = st.text_input("👤 Usuario (nombre.apellido)").strip().lower()
        contrasena_input = st.text_input("🔑 Contraseña", type="password")

        if st.button("Ingresar"):
            if usuario_input in df_usuarios["usuario"].values:
                stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
                if contrasena_input == stored_pass:
                    st.session_state["usuario"] = usuario_input
                    st.success(f"Bienvenido, {usuario_input}")
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta")
            else:
                st.error("❌ Usuario no registrado")

# ---- CREAR USUARIO ----
with st.sidebar.expander("👥 Crear nuevo usuario"):
    nuevo_usuario = st.text_input("Nuevo usuario (nombre.apellido)").strip().lower()
    nuevo_correo = st.text_input("Correo electrónico").strip().lower()
    nueva_contra = st.text_input("Contraseña", type="password")

    if st.button("➕ Crear usuario"):
        if not nuevo_usuario or not nuevo_correo or not nueva_contra:
            st.error("⚠️ Todos los campos son obligatorios.")
        elif not nuevo_correo.endswith("@pharmaser.com.co"):
            st.error("El correo debe terminar en @pharmaser.com.co")
        elif nuevo_usuario in df_usuarios["usuario"].values:
            st.error("Este usuario ya existe.")
        else:
            df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{
                "usuario": nuevo_usuario,
                "contrasena": nueva_contra,
                "correo": nuevo_correo
            }])], ignore_index=True)
            df_usuarios.to_csv(USERS_FILE, index=False)
            st.success("✅ Usuario creado correctamente.")

# ==============================
# INTERFAZ PRINCIPAL
# ==============================
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]

    st.title("💊 Control de Estado de Medicamentos")
    st.markdown(f"👤 **Usuario activo:** {usuario}")
    st.markdown("---")

    tabs = st.tabs(["🧾 Registrar medicamento", "📂 Registros guardados"])

    # ==========================================================
    # 🧾 TAB 1: REGISTRAR MEDICAMENTO
    # ==========================================================
    with tabs[0]:
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
        st.markdown(explicaciones_estado[estado])
        st.markdown("---")

        # Fecha automática
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        st.text_input("📅 Fecha de registro (automática)", value=fecha_actual, disabled=True)

        # PLU y Código Genérico con autollenado
        col1, col2 = st.columns(2)
        with col1:
            plu = st.text_input("🔢 PLU del medicamento", key="plu").upper()
        with col2:
            # Extraer automáticamente el código genérico si el PLU tiene "_"
            if "_" in plu:
                codigo_generico = plu.split("_")[0]
            else:
                codigo_generico = ""
            st.text_input("🧬 Código genérico", value=codigo_generico, key="codigo_generico", disabled=True)

        # Resto de los campos
        nombre = st.text_input("💊 Nombre comercial del medicamento").upper()
        laboratorio = st.text_input("🏭 Laboratorio fabricante").upper()
        presentacion = st.text_input("📦 Presentación (ej: Tabletas 500mg)").upper()
        observaciones = st.text_area("🗒️ Observaciones o comentarios adicionales")
        archivo = st.file_uploader("📎 Subir soporte (OBLIGATORIO)", type=["pdf", "jpg", "png"])

        if st.button("💾 Guardar registro"):
            if not (plu and nombre and archivo):
                st.error("⚠️ Debes ingresar PLU, Nombre del medicamento y adjuntar el soporte.")
            else:
                soporte_path = os.path.join("soportes", archivo.name)
                with open(soporte_path, "wb") as f:
                    f.write(archivo.getbuffer())

                nuevo_registro = {
                    "Usuario": usuario,
                    "Fecha": fecha_actual,
                    "Estado": estado,
                    "PLU": plu,
                    "Código Genérico": codigo_generico,
                    "Nombre Comercial": nombre,
                    "Presentación": presentacion,
                    "Laboratorio": laboratorio,
                    "Observaciones": observaciones,
                    "Soporte": soporte_path
                }

                if os.path.exists(DATA_FILE):
                    df = pd.read_csv(DATA_FILE)
                    df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
                else:
                    df = pd.DataFrame([nuevo_registro])

                df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

                st.success(f"✅ Registro guardado correctamente por {usuario}.")
                st.info(f"📎 Soporte guardado en: `{soporte_path}`")

    # ==========================================================
    # 📂 TAB 2: REGISTROS GUARDADOS
    # ==========================================================
    with tabs[1]:
        st.subheader("📊 Registros guardados")
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                for i, row in df.iterrows():
                    with st.expander(f"📌 {row['Nombre Comercial']} ({row['Estado']}) - {row['Fecha']}"):
                        st.write(f"**Usuario:** {row['Usuario']}")
                        st.write(f"**PLU:** {row['PLU']}")
                        st.write(f"**Código Genérico:** {row['Código Genérico']}")
                        st.write(f"**Laboratorio:** {row['Laboratorio']}")
                        st.write(f"**Presentación:** {row['Presentación']}")
                        st.write(f"**Observaciones:** {row['Observaciones']}")

                        soporte_path = row["Soporte"]
                        if os.path.exists(soporte_path):
                            with open(soporte_path, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode()
                            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(soporte_path)}">📥 Descargar soporte</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        else:
                            st.warning("❌ Soporte no encontrado en la carpeta local.")
            else:
                st.info("No hay registros aún.")
        else:
            st.info("No hay registros aún.")
