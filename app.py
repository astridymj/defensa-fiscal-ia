import os
import json
import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client, Client

# 1. Configuración de Credenciales y Clientes
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Gestión y Defensa Tributaria - Holding", layout="wide")
st.title("⚖️ Sistema Inteligente de Defensa Fiscal y Precedentes (DIAN)")

# 2. Interfaz de Entrada para el Usuario
st.markdown("### Sube o ingresa el texto del Oficio / Requerimiento Especial de la DIAN")
texto_oficio = st.text_area("Texto del Requerimiento Fiscal:", height=200, placeholder="Ej: Requerimiento Especial No. 062382020000030...")

if st.button("Procesar, Consultar Precedentes y Generar Defensa"):
    if texto_oficio:
        with st.spinner("Paso 1: Consultando precedentes jurídicos en Supabase..."):
            # Consultar los precedentes existentes en Supabase
            try:
                response_db = supabase.table("precedentes_tributarios").select("titulo_documento, contenido_fragmento").limit(3).execute()
                precedentes_recuperados = response_db.data
            except Exception as e:
                precedentes_recuperados = []
                st.warning(f"No se pudieron cargar precedentes de Supabase: {e}")

        with st.spinner("Paso 2: Generando análisis y defensa jurídica con Google AI Studio (Gemini)..."):
            # Formatear el contexto recuperado para el prompt
            contexto_normativo = "\n".join([f"- {p['titulo_documento']}: {p['contenido_fragmento']}" for p in precedentes_recuperados])

            prompt_sistema = """
            ROL: Actúa como un Abogado Tributarista y Defensor Jurídico Senior en Colombia.
            TAREA: Analiza el requerimiento oficial de la DIAN, extrae los metadatos en JSON estricto, elabora un checklist de debido proceso y redacta el borrador formal de contestación al Requerimiento Especial protegiendo el patrimonio de la compañía.
            """

            prompt_usuario = f"""
            PRECEDENTES JURÍDICOS RECUPERADOS DE SUPABASE:
            {contexto_normativo}

            TEXTO DEL OFICIO DE LA DIAN:
            {texto_oficio}
            """

            config = types.GenerateContentConfig(
                temperature=0.3,  # Rigor técnico y jurídico
                system_instruction=prompt_sistema
            )

            # Llamada al modelo oficial con Google GenAI SDK
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt_usuario,
                config=config
            )
            
            defensa_generada = response.text

        with st.spinner("Paso 3: Actualizando la base de datos en Supabase con el nuevo caso..."):
            # Insertar el nuevo caso analizado en la tabla de Supabase para mantener el historial actualizado
            try:
                nuevo_registro = {
                    "titulo_documento": "Requerimiento Fiscal Procesado - Automatizado",
                    "contenido_fragmento": texto_oficio[:500] + "...", # Guardamos un extracto representativo
                    "metadata": {"origen": "App Web IA", "estado": "Procesado"}
                }
                supabase.table("precedentes_tributarios").insert(nuevo_registro).execute()
                st.success("¡Base de datos en Supabase actualizada exitosamente con el nuevo requerimiento!")
            except Exception as e:
                st.error(f"Error al actualizar Supabase: {e}")

        # 4. Despliegue de Resultados en la Interfaz
        st.markdown("---")
        st.subheader("📋 Resultados del Análisis y Borrador de Defensa")
        st.markdown(defensa_generada)

    else:
        st.error("Por favor, ingresa el texto del oficio fiscal para iniciar el procesamiento.")