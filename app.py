import os
import json
import io
import time
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client, Client

# 1. Configuración de Credenciales de forma segura desde Streamlit Secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Gestión y Defensa Tributaria - Holding", layout="wide")
st.title("⚖️ Sistema Inteligente de Defensa Fiscal y Precedentes (DIAN)")

# 2. Interfaz para Subir el Archivo PDF del Requerimiento
st.markdown("### Sube el archivo PDF del Requerimiento u Oficio de la DIAN")
archivo_pdf = st.file_uploader("Selecciona el archivo PDF", type=["pdf"])

if archivo_pdf is not None:
    st.success(f"Archivo cargado exitosamente: {archivo_pdf.name}")
    
    if st.button("Procesar PDF, Consultar Precedentes y Generar Defensa"):
        with st.spinner("Subiendo archivo a Google AI Studio..."):
            try:
                bytes_pdf = archivo_pdf.getvalue()
                pdf_file_like = io.BytesIO(bytes_pdf)
                pdf_file_like.name = archivo_pdf.name
                
                archivo_subido = client.files.upload(
                    file=pdf_file_like,
                    config=types.UploadFileConfig(
                        mime_type="application/pdf",
                        display_name=archivo_pdf.name
                    )
                )
            except Exception as e:
                st.error(f"Error al subir el archivo a Google AI Studio: {e}")
                st.stop()

        # Esperar a que el archivo esté listo en los servidores de Google
        with st.spinner("Esperando a que Google AI Studio procese el documento PDF..."):
            while archivo_subido.state.name == "PROCESSING":
                time.sleep(2)
                archivo_subido = client.files.get(name=archivo_subido.name)
            
            if archivo_subido.state.name != "ACTIVE":
                st.error(f"El archivo falló en el procesamiento de Google. Estado: {archivo_subido.state.name}")
                st.stop()

        with st.spinner("Paso 1: Consultando precedentes jurídicos en Supabase..."):
            try:
                response_db = supabase.table("precedentes_tributarios").select("titulo_documento, contenido_fragmento").limit(3).execute()
                precedentes_recuperados = response_db.data
            except Exception as e:
                precedentes_recuperados = []
                st.warning(f"No se pudieron cargar precedentes de Supabase: {e}")

        with st.spinner("Paso 2: Generando análisis y defensa jurídica con Gemini (Google AI Studio)..."):
            contexto_normativo = "\n".join([f"- {p['titulo_documento']}: {p['contenido_fragmento']}" for p in precedentes_recuperados])

            prompt_sistema = """
            ROL: Actúa como un Abogado Tributarista y Defensor Jurídico Senior en Colombia.
            TAREA: Analiza el requerimiento oficial de la DIAN adjunto en el PDF, extrae los metadatos en JSON estricto, elabora un checklist de debido proceso y redacta el borrador formal de contestación al Requerimiento Especial protegiendo el patrimonio de la compañía.
            """

            prompt_usuario = f"""
            PRECEDENTES JURÍDICOS RECUPERADOS DE SUPABASE:
            {contexto_normativo}

            Por favor, analiza el archivo PDF adjunto de la DIAN basándote en los precedentes anteriores y genera el JSON de metadatos, el checklist y el borrador de defensa.
            """

            config = types.GenerateContentConfig(
                temperature=0.3,  # Rigor técnico y jurídico
                system_instruction=prompt_sistema
            )

            try:
                # Buscamos de forma dinámica un modelo compatible disponible en la cuenta
                modelo_seleccionado = 'gemini-1.5-flash'
                for m in client.models.list():
                    if 'flash' in m.name and 'generateContent' in m.supported_generation_methods:
                        modelo_seleccionado = m.name
                        break

                response = client.models.generate_content(
                    model=modelo_seleccionado,
                    contents=[archivo_subido, prompt_usuario],
                    config=config
                )
                defensa_generada = response.text
            except Exception as e:
                st.error(f"Error en la generación con Gemini: {e}")
                st.stop()

        with st.spinner("Paso 3: Actualizando la base de datos en Supabase con el nuevo caso..."):
            try:
                nuevo_registro = {
                    "titulo_documento": f"PDF Procesado: {archivo_pdf.name}",
                    "contenido_fragmento": "Requerimiento fiscal procesado mediante carga de PDF en la aplicación web.",
                    "metadata": {"origen": "App Web PDF", "estado": "Procesado"}
                }
                supabase.table("precedentes_tributarios").insert(nuevo_registro).execute()
                st.success("¡Base de datos en Supabase actualizada exitosamente con el registro del PDF!")
            except Exception as e:
                st.error(f"Error al actualizar Supabase: {e}")

        # 3. Visualización de Resultados
        st.markdown("---")
        st.subheader("📋 Resultados del Análisis y Borrador de Defensa")
        st.markdown(defensa_generada)
else:
    st.info("Por favor, carga un archivo PDF para habilitar el procesamiento del requerimiento de la DIAN.")
