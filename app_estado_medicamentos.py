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

# Archivos base
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

# Asegurar limpieza de texto
df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()

# ==============================
# INTERFAZ DE AUTENTICACIÓN
# ==============================
st.sidebar.header("🔐 Inicio de sesión")

if "usuario" in st.session_state:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()
else:
    usuario_input = st.sidebar.text_input("👤 Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("🔑 Contraseña", type="password")

    if st.sidebar.button("Ingresar"):
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.success(f"Bienvenido, {usuario_input}")
                st.rerun()
            else:
                st.sidebar.error("❌ Contraseña incorrecta")
        else:
            st.sidebar.error("❌ Usuario no registrado")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🆕 Crear nuevo usuario")
    nuevo_usuario = st.sidebar.text_input("Usuario (nombre.apellido)", key="nuevo_usuario").strip().lower()
    nuevo_correo = st.sidebar.text_input("Correo electrónico", key="nuevo_correo").strip().lower()
    nueva_contra = st.sidebar.text_input("Contraseña", type="password", key="nueva_contra")

    if st.sidebar.button("Registrar usuario"):
        if not nuevo_usuario or not nuevo_correo or not nueva_contra:
            st.sidebar.error("⚠️ Todos los campos son obligatorios.")
        elif not nuevo_correo.endswith("@pharmaser.com.co"):
            st.sidebar.error("El correo debe terminar en @pharmaser.com.co")
        elif nuevo_usuario in df_usuarios["usuario"].values:
            st.sidebar.error("Este usuario ya existe.")
        else:
            df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{
                "usuario": nuevo_usuario,
                "contrasena": nueva_contra,
                "correo": nuevo_correo
            }])], ignore_index=True)
            df_usuarios.to_csv(USERS_FILE, index=False)
            st.sidebar.success("✅ Usuario creado correctamente.")

# ==============================
# INTERFAZ PRINCIPAL (DESPUÉS DEL LOGIN)
# ==============================
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.title("💊 Control de Estado de Medicamentos")
    st.markdown(f"👤 **Usuario activo:** {usuario}")
    st.markdown("---")

    # ESTADO (ARRIBA)
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

    # FORMULARIO DE REGISTRO
    st.subheader("📋 Información del medicamento")

    col1, col2, col3 = st.columns(3)
    with col1:
        plu = st.text_input("🔢 PLU del medicamento").upper()
    with col2:
        codigo_generico = st.text_input("🧬 Código genérico").upper()
    with col3:
        fecha = st.date_input("📅 Fecha de registro", value=datetime.today())

    col4, col5, col6 = st.columns(3)
    with col4:
        nombre = st.text_input("💊 Nombre comercial del medicamento").upper()
    with col5:
        laboratorio = st.text_input("🏭 Laboratorio fabricante").upper()
    with col6:
        presentacion = st.text_input("📦 Presentación (ej: Tabletas 500mg)").upper()

    observaciones = st.text_area("🗒️ Observaciones o comentarios adicionales")

    archivo = st.file_uploader("📎 Subir soporte (OBLIGATORIO)", type=["pdf", "jpg", "png"])

    # BOTÓN GUARDAR
    if st.button("💾 Guardar registro"):
        if not (plu and nombre and archivo):
            st.error("⚠️ Debes ingresar PLU, Nombre del medicamento y adjuntar el soporte.")
        else:
            nuevo_registro = {
                "Usuario": usuario,
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Estado": estado,
                "PLU": plu,
                "Código Genérico": codigo_generico,
                "Nombre Comercial": nombre,
                "Presentación": presentacion,
                "Laboratorio": laboratorio,
                "Observaciones": observaciones,
                "Soporte": archivo.name
            }

            if os.path.exists(DATA_FILE):
                df = pd.read_csv(DATA_FILE)
                df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)
            else:
                df = pd.DataFrame([nuevo_registro])

            df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

            # Guardar soporte
            soporte_path = os.path.join("soportes", archivo.name)
            with open(soporte_path, "wb") as f:
                f.write(archivo.getbuffer())

            st.success(f"✅ Registro guardado correctamente por {usuario}.")
            st.info(f"📎 Soporte guardado en: `{soporte_path}`")

    # VISUALIZAR REGISTROS
    st.markdown("---")
    st.subheader("📊 Registros guardados")

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        st.dataframe(df)
    else:
        st.warning("Aún no hay registros guardados.")

