import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
import re
import time

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="Control de Estado de Medicamentos", layout="wide")

# ---------------- DIRECTORIOS ----------------
BASE_DIR = "."  # Carpeta del proyecto, escribible en Streamlit Cloud
DATA_FILE = os.path.join(BASE_DIR, "registros_medicamentos.csv")
USERS_FILE = os.path.join(BASE_DIR, "usuarios.csv")
SOPORTES_DIR = os.path.join(BASE_DIR, "soportes")
os.makedirs(SOPORTES_DIR, exist_ok=True)  # Crear carpeta si no existe

# ---------------- CARGAR O CREAR ARCHIVOS ----------------
expected_columns = ["Consecutivo","Usuario", "Estado", "PLU", "Código Genérico",
                    "Nombre Medicamento", "Laboratorio", "Fecha", "Soporte"]

# Registros
if os.path.exists(DATA_FILE):
    df_registros = pd.read_csv(DATA_FILE)
    for col in expected_columns:
        if col not in df_registros.columns:
            df_registros[col] = ""
    df_registros = df_registros[expected_columns]
else:
    df_registros = pd.DataFrame(columns=expected_columns)
    df_registros.to_csv(DATA_FILE, index=False)

# Usuarios
if os.path.exists(USERS_FILE):
    df_usuarios = pd.read_csv(USERS_FILE)
else:
    df_usuarios = pd.DataFrame([{"usuario": "admin", "contrasena": "1234", "correo": "admin@pharmaser.com.co"}])
    df_usuarios.to_csv(USERS_FILE, index=False)

df_usuarios["usuario"] = df_usuarios["usuario"].astype(str).str.strip().str.lower()
df_usuarios["contrasena"] = df_usuarios["contrasena"].astype(str).str.strip()
df_usuarios["correo"] = df_usuarios.get("correo", pd.Series([""]*len(df_usuarios)))

# ---------------- FUNCIONES ----------------
def save_registros(df):
    df.to_csv(DATA_FILE, index=False)

def save_usuarios(df):
    df.to_csv(USERS_FILE, index=False)

def limpiar_formulario():
    for key in ["estado","plu","codigo_generico","nombre_medicamento","laboratorio","soporte_file","ultimo_pdf_path"]:
        if key in st.session_state:
            del st.session_state[key]

def nombre_valido_archivo(nombre):
    nombre = nombre.upper().replace(' ', '_')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return nombre

def obtener_consecutivo():
    if df_registros.empty:
        return 1
    else:
        return int(df_registros["Consecutivo"].max()) + 1

def mostrar_pdf(soporte_path):
    if os.path.exists(soporte_path):
        st.markdown(f'<a href="file:///{soporte_path}" target="_blank">📄 Abrir PDF</a>', unsafe_allow_html=True)
        with open(soporte_path, "rb") as f:
            pdf_data = f.read()
        st.download_button("📥 Descargar PDF", pdf_data, file_name=os.path.basename(soporte_path), mime="application/pdf")

def descargar_csv(df):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    st.markdown(f'<a href="data:file/csv;base64,{b64}" download="consolidado_medicamentos.csv">📥 Descargar CSV consolidado</a>', unsafe_allow_html=True)

# ---------------- SESIÓN ----------------
st.sidebar.header("🔐 Inicio de sesión")

# Manejo seguro de rerun
if "rerun_flag" not in st.session_state:
    st.session_state["rerun_flag"] = False

if "usuario" in st.session_state:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['usuario']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.experimental_rerun()
else:
    usuario_input = st.sidebar.text_input("Usuario (nombre.apellido)").strip().lower()
    contrasena_input = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Ingresar"):
        if usuario_input in df_usuarios["usuario"].values:
            stored_pass = df_usuarios.loc[df_usuarios["usuario"] == usuario_input, "contrasena"].values[0]
            if contrasena_input == stored_pass:
                st.session_state["usuario"] = usuario_input
                st.session_state["rerun_flag"] = True
            else:
                st.sidebar.error("Contraseña incorrecta")
        else:
            st.sidebar.error("Usuario no registrado")

    # Crear nuevo usuario
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Crear nuevo usuario")
    nombre_usuario_nuevo = st.sidebar.text_input("Usuario (nombre.apellido)", key="usuario_nuevo").strip().lower()
    correo_nuevo = st.sidebar.text_input("Correo electrónico", key="correo_nuevo").strip().lower()
    contrasena_nueva = st.sidebar.text_input("Contraseña", type="password", key="pass_nueva")
    if st.sidebar.button("Crear usuario"):
        if not correo_nuevo or not contrasena_nueva or not nombre_usuario_nuevo:
            st.sidebar.error("Debes ingresar usuario, correo y contraseña")
        elif not correo_nuevo.endswith("@pharmaser.com.co"):
            st.sidebar.error("El correo debe terminar en @pharmaser.com.co")
        elif correo_nuevo in df_usuarios["correo"].values:
            st.sidebar.error("Este correo ya está registrado")
        elif nombre_usuario_nuevo in df_usuarios["usuario"].values:
            st.sidebar.error("Este usuario ya existe")
        else:
            df_usuarios = pd.concat([df_usuarios, pd.DataFrame([{
                "usuario": nombre_usuario_nuevo,
                "contrasena": contrasena_nueva,
                "correo": correo_nuevo
            }])], ignore_index=True)
            save_usuarios(df_usuarios)
            st.sidebar.success(f"Usuario creado: {nombre_usuario_nuevo}")

# Manejo seguro de rerun
if st.session_state.get("rerun_flag", False):
    st.session_state["rerun_flag"] = False
    st.experimental_rerun()

# ---------------- INTERFAZ ----------------
if "usuario" in st.session_state:
    usuario = st.session_state["usuario"]
    st.markdown(f"### Hola, **{usuario}**")
    tabs = st.tabs(["Registrar medicamento", "Consolidado general", "Buscar registro"])

    # -------- TAB REGISTRO --------
    with tabs[0]:
        df_usuario = df_registros[df_registros["Usuario"] == usuario]
        consecutivo = obtener_consecutivo()
        estado = st.selectbox("Estado", ["Agotado", "Desabastecido", "Descontinuado"], index=0, key="estado")
        plu = st.text_input("PLU", key="plu").upper()
        codigo_gen_default = plu.split("_")[0] if "_" in plu else ""
        codigo_gen = st.text_input("Código genérico", value=codigo_gen_default, key="codigo_generico").upper()
        nombre = st.text_input("Nombre del medicamento", key="nombre_medicamento").upper()
        laboratorio = st.text_input("Laboratorio", key="laboratorio").upper()
        soporte_file = st.file_uploader("📎 Subir soporte PDF", type=["pdf"], key="soporte_file")
        st.date_input("Fecha", value=datetime.now(), disabled=True)

        if soporte_file and nombre.strip():
            timestamp = int(time.time())
            nombre_pdf = f"{consecutivo}_{usuario}_{nombre_valido_archivo(nombre)}_{timestamp}.pdf"
            pdf_path = os.path.join(SOPORTES_DIR, nombre_pdf)
            with open(pdf_path, "wb") as f:
                f.write(soporte_file.getbuffer())
            st.session_state["ultimo_pdf_path"] = pdf_path
            st.markdown("### PDF disponible")
            mostrar_pdf(pdf_path)

        col1, col2 = st.columns([1,1])
        if col1.button("💾 Guardar registro"):
            if not nombre.strip():
                st.warning("Debes ingresar el nombre del medicamento")
            elif "ultimo_pdf_path" not in st.session_state:
                st.warning("Debes subir un PDF")
            else:
                new_row = pd.DataFrame([[
                    consecutivo, usuario, estado, plu, codigo_gen,
                    nombre, laboratorio, datetime.now().strftime("%Y-%m-%d"), st.session_state["ultimo_pdf_path"]
                ]], columns=df_registros.columns)
                df_registros = pd.concat([df_registros, new_row], ignore_index=True)
                save_registros(df_registros)
                st.success("✅ Registro guardado")
                mostrar_pdf(st.session_state["ultimo_pdf_path"])
                limpiar_formulario()

        if col2.button("🧹 Limpiar formulario"):
            limpiar_formulario()
            st.success("Formulario limpiado ✅")

    # -------- TAB CONSOLIDADO --------
    with tabs[1]:
        st.dataframe(df_registros)
        descargar_csv(df_registros)
        for idx, row in df_registros.iterrows():
            if os.path.exists(row["Soporte"]):
                st.download_button(
                    label=f"📥 Descargar {os.path.basename(row['Soporte'])}",
                    data=open(row["Soporte"], "rb").read(),
                    file_name=os.path.basename(row["Soporte"]),
                    mime="application/pdf",
                    key=f"download_{idx}"
                )

    # -------- TAB BUSCAR REGISTRO --------
    with tabs[2]:
        busqueda = st.text_input("Buscar cualquier campo")
        if busqueda:
            df_filtrado = df_registros[df_registros.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)]
            st.dataframe(df_filtrado)
