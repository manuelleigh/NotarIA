import time
from data.contracts_data import CONTRACTS, DEF_AFFIRMATIVES, DEF_NEGATIVES
from services.nlp_utils import get_nlp

# Inicializamos el modelo NLP (spaCy)
nlp = get_nlp()

# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL: flujo de conversación con streaming
# ------------------------------------------------------------
def procesar_mensaje_streaming(contexto, texto_usuario):
    """
    Genera respuestas de chatbot en formato streaming (yield) para una experiencia interactiva.
    No interactúa con la base de datos, solo recibe y devuelve el contexto.
    """
    contexto = contexto or {}

    # Función generadora para simular el efecto de "escribiendo"
    def stream_response(texto_base, delay=0.02):
        for char in texto_base:
            yield char
            time.sleep(delay)

    # 🧩 1. Detectar el tipo de contrato
    if "tipo_contrato" not in contexto:
        tipo = detectar_tipo_contrato(texto_usuario)
        if tipo:
            contexto["tipo_contrato"] = tipo
            contexto["estado"] = "solicitando_datos"
            contexto["pregunta_actual"] = 0
            contexto["respuestas"] = {}
            
            primera_pregunta = CONTRACTS[tipo]["preguntas"][0]["texto"]
            respuesta = (
                f"He detectado que deseas elaborar un **{CONTRACTS[tipo]['nombre']}**. "
                f"¿Podrías responderme la siguiente pregunta?\n\n{primera_pregunta}"
            )
        else:
            respuesta = (
                "¿Podrías especificar qué tipo de contrato deseas elaborar? "
                "Por ejemplo: arrendamiento, compraventa o prestación de servicios."
            )
        
        yield from stream_response(respuesta)

    # 🧩 2. Recolectando respuestas
    elif contexto.get("estado") == "solicitando_datos":
        tipo = contexto["tipo_contrato"]
        i = contexto.get("pregunta_actual", 0)
        respuestas = contexto.get("respuestas", {})
        
        pregunta_actual = CONTRACTS[tipo]["preguntas"][i]
        clave_semantica = pregunta_actual["key"]
        respuestas[clave_semantica] = texto_usuario
        contexto["respuestas"] = respuestas

        if i + 1 < len(CONTRACTS[tipo]["preguntas"]):
            contexto["pregunta_actual"] = i + 1
            siguiente_pregunta = CONTRACTS[tipo]["preguntas"][i + 1]["texto"]
            yield from stream_response(siguiente_pregunta)
        else:
            contexto["estado"] = "revision"
            respuesta = (
                f"Perfecto. Ya tengo toda la información para el **{CONTRACTS[tipo]['nombre']}**. "
                "¿Quieres ver un resumen antes de generar el borrador?"
            )
            yield from stream_response(respuesta)

    # 🧩 3. Revisión y confirmación
    elif contexto.get("estado") == "revision":
        if es_afirmativo(texto_usuario):
            tipo = contexto["tipo_contrato"]
            respuestas = contexto.get("respuestas", {})
            resumen = f"**Resumen del {CONTRACTS[tipo]['nombre']}**:\n"
            yield from stream_response(resumen)
            
            for idx, preg in enumerate(CONTRACTS[tipo]["preguntas"]):
                key = preg["key"]
                res = respuestas.get(key, "N/A")
                linea = f"- **{preg['texto']}**: {res}\n"
                yield from stream_response(linea, delay=0.03)
            
            confirmacion = "\n¿Confirmas que la información es correcta? Responde 'sí' o 'no'."
            contexto["estado"] = "preliminar_confirmacion"
            yield from stream_response(confirmacion)
        else:
            contexto["estado"] = "clausulas_especiales"
            respuesta = "Ok. ¿Deseas agregar alguna cláusula especial?"
            yield from stream_response(respuesta)

    # 🧩 4. Confirmación final
    elif contexto.get("estado") == "preliminar_confirmacion":
        if es_afirmativo(texto_usuario):
            contexto["estado"] = "clausulas_especiales"
            respuesta = "¡Genial! ¿Deseas añadir alguna cláusula especial?"
            yield from stream_response(respuesta)
        else:
            contexto["estado"] = "solicitando_datos"
            contexto["pregunta_actual"] = 0 # Reiniciar para corrección
            contexto["respuestas"] = {}
            respuesta = "Entendido. Empecemos de nuevo. ¿Cuál es el objeto del contrato?"
            yield from stream_response(respuesta)

    # 🧩 X. Flujo simplificado para cláusulas (ejemplo)
    elif contexto.get("estado") == "clausulas_especiales":
        contexto["estado"] = "generando_contrato"
        respuesta = "Perfecto. Generando el borrador del contrato..."
        yield from stream_response(respuesta)

    else:
        yield from stream_response("No he entendido tu respuesta. ¿Podrías reformularla?")

    # Al final, devolvemos el contexto actualizado
    yield {"__contexto_actualizado__": contexto}

# ------------------------------------------------------------
# UTILIDADES (adaptadas de chat_service.py)
# ------------------------------------------------------------
def texto_normalizado(texto: str) -> str:
    if not texto:
        return ""
    doc = nlp(texto.strip().lower())
    return " ".join([token.lemma_ for token in doc])

def es_afirmativo(texto: str) -> bool:
    txt = texto_normalizado(texto)
    return txt in DEF_AFFIRMATIVES or txt.startswith("si ")

def es_negativo(texto: str) -> bool:
    txt = texto_normalizado(texto)
    return txt in DEF_NEGATIVES or txt.startswith("no ")

def detectar_tipo_contrato(texto: str) -> str | None:
    if not texto:
        return None
    doc_texto = nlp(texto.lower())
    for tipo, info in CONTRACTS.items():
        sinonimos = info.get("sinonimos", [])
        if any(s in texto.lower() for s in sinonimos):
            return tipo
        # Optional: Add semantic similarity check if needed
    return None
