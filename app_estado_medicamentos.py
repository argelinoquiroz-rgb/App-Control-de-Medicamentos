import streamlit as st
import pandas as pd
import os

# ==============================
# ARCHIVO DE USUARIOS
# ==============================
USERS_FILE = "usuarios.csv"

# Crear CSV si no existe
if not os.path.exists(USERS_FILE):
    df = pd.DataFrame(columns=["usuario", "password", "rol"])
    df.loc[0] = ["admin", "1234", "admin"]  # usuario inicial
    df.to_csv(USERS_FILE, index=False)

# Cargar CSV
usuarios_df = pd.read_csv(USERS_FILE)
usuarios_df.columns = usuarios_df.columns.str.strip().str.lower()  # normalizar nombres de columnas

# ==============================
# LOGIN
# ==============================
st.title("🔐 Control de Estado de Medicamentos - Login")

menu = ["Iniciar sesión", "Registrar nuevo usuario"]
choice = st.sidebar.selectbox("Menú", menu)

if choice == "Iniciar sesión":
    st.subheader("Iniciar sesión")

    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        # Buscar usuario
        user_row = usuarios_df[(usuarios_df["usuario"] == username) & (usuarios_df["password"] == password)]

        if not user_row.empty:
            st.success(f"¡Bienvenido {username}!")
            st.session_state["usuario"] = username
            # Aquí colocas tu app principal o dashboard
            st.write("✅ Aquí va el contenido protegido de la app")
        else:
            st.error("❌ Usuario o contraseña incorrectos")

# ==============================
# REGISTRO DE USUARIOS
# ==============================
elif choice == "Registrar nuevo usuario":
    st.subheader("Registrar nuevo usuario")

    new_user = st.text_input("Nuevo usuario")
    new_password = st.text_input("Contraseña", type="password")
    confirm_password = st.text_input("Confirmar contraseña", type="password")
    rol = st.selectbox("Rol", ["usuario", "admin"])

    if st.button("Registrar"):
        if new_user.strip() == "" or new_password.strip() == "":
            st.error("Todos los campos son obligatorios")
        elif new_password != confirm_password:
            st.error("❌ Las contraseñas no coinciden")
        elif new_user in usuarios_df["usuario"].values:
            st.error("❌ Este usuario ya existe")
        else:
            # Agregar nuevo usuario
            usuarios_df = usuarios_df.append(
                {"usuario": new_user, "password": new_password, "rol": rol}, ignore_index=True
            )
            usuarios_df.to_csv(USERS_FILE, index=False)
            st.success(f"✅ Usuario '{new_user}' registrado correctamente")
