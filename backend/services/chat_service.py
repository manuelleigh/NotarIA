import time
import json
from models import Chat, Mensaje, Usuario
from database import db
from datetime import datetime
from data.contracts_data import CONTRACTS, DEF_AFFIRMATIVES, DEF_NEGATIVES
from services.generation_service import formalizar_contrato
from services.data_processors import PROCESSOR_REGISTRY
from services.nlp_utils import get_nlp

nlp = get_nlp()

def stream_response(texto_base: str, delay: float = 0.02):
    if not texto_base:
        return
    for char in texto_base:
        yield char
        time.sleep(delay)

def procesar_mensaje(chat_id, texto_usuario, usuario_id):
    chat = Chat.query.get(chat_id)
    if not chat:
        raise ValueError("Chat no encontrado")

    # SOLUCIÓN CLAVE: Usar .copy() para que SQLAlchemy detecte el cambio en el JSON.
    contexto = (chat.metadatos or {}).copy()

    # --- ANÁLISIS DE MENSAJE ESPECIAL (con firmantes) ---
    is_signers_confirmation = texto_usuario.startswith("Okay, procede a generar el contrato con estos firmantes:")
    
    if is_signers_confirmation:
        try:
            json_str = texto_usuario.split("Okay, procede a generar el contrato con estos firmantes:")[1].strip()
            firmantes = json.loads(json_str)
            
            codigo_contrato = formalizar_contrato(chat_id, firmantes_extra=firmantes)
            contexto["estado"] = "formalizado"
            contexto["codigo_contrato"] = codigo_contrato

            respuesta = (
                f"¡Perfecto! ✅ Se ha formalizado tu contrato con todos los firmantes.\n\n"
                f"**Código de Contrato:** {codigo_contrato}"
            )
        except Exception as e:
            print(f"Error en formalización con firmantes: {e}")
            respuesta = "⚠️ Hubo un error al procesar los firmantes y formalizar el contrato. Por favor, intenta de nuevo."
    
    # --- FLUJO DE CONVERSACIÓN NORMAL ---
    elif "tipo_contrato" not in contexto:
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
            siguiente = CONTRACTS[tipo]["preguntas"][i + 1]["texto"]
            respuesta = siguiente
        else:
            contexto["estado"] = "revision"
            respuesta = (
                f"Perfecto. Ya tengo toda la información necesaria para elaborar el "
                f"contrato de **{CONTRACTS[tipo]['nombre']}**.\n\n"
                "¿Deseas que te muestre un resumen antes de generar el documento?"
            )

    elif contexto.get("estado") == "revision" and es_afirmativo(texto_usuario):
        tipo = contexto["tipo_contrato"]
        respuestas = contexto.get("respuestas", {})

        resumen = (
            f"Has solicitado un contrato de **{CONTRACTS[tipo]['nombre']}** "
            "con los siguientes detalles:\n"
        )
        for idx, pregunta in enumerate(CONTRACTS[tipo]["preguntas"]):
            key = pregunta["key"]
            respuesta_usuario = respuestas.get(key, "No proporcionada")
            resumen += f"- **{idx + 1}. {pregunta['texto']}**: {respuesta_usuario}\n"

        resumen += (
            "\n¿Confirmas que toda la información es correcta para generar el contrato preliminar?\n"
            "Responde 'sí' para confirmar o 'no' para corregir."
        )

        respuesta = resumen
        contexto["estado"] = "preliminar_confirmacion"

    elif contexto.get("estado") == "preliminar_confirmacion":
        if es_afirmativo(texto_usuario):
            contexto["estado"] = "clausulas_especiales"
            respuesta = (
                "Perfecto 👍. Antes de generar el contrato preliminar, "
                "¿deseas agregar alguna cláusula especial o condición adicional? "
                "Por ejemplo: penalidades, ampliaciones o condiciones de pago."
            )
        elif es_negativo(texto_usuario):
            respuesta = "Entendido. ¿Qué información te gustaría corregir o agregar?"
        else:
            respuesta = (
                "Por favor, responde 'sí' para confirmar o 'no' si deseas modificar algún dato."
            )

    elif contexto.get("estado") == "clausulas_especiales":
        if es_negativo(texto_usuario):
            contexto["estado"] = "generando_contrato"
            contexto["clausulas_especiales"] = []
            respuesta = "Perfecto. Procederé a generar el contrato preliminar sin cláusulas adicionales."
        elif es_afirmativo(texto_usuario):
            contexto["estado"] = "registrando_clausulas"
            respuesta = (
                "Muy bien. Escribe las cláusulas o condiciones que quieras incluir.\n"
                "Por ejemplo: 'El inquilino no podrá subarrendar el inmueble sin autorización escrita del arrendador.'"
            )
        else:
            contexto.setdefault("clausulas_especiales", [])
            contexto["clausulas_especiales"].append(texto_usuario)
            respuesta = "Cláusula registrada ✅. ¿Deseas agregar otra más o continuamos con el contrato?"

    elif contexto.get("estado") == "registrando_clausulas":
        if es_negativo(texto_usuario):
            contexto["estado"] = "generando_contrato"
            respuesta = "Entendido. Procederé a generar el contrato con las cláusulas registradas."
        else:
            contexto.setdefault("clausulas_especiales", [])
            contexto["clausulas_especiales"].append(texto_usuario)
            respuesta = "Cláusula agregada ✅. ¿Deseas incluir otra más?"

    elif contexto.get("estado") == "esperando_aprobacion_formal":
        respuesta = "Por favor, responde 'sí' para abrir el formulario de firmantes o 'no' para revisar los datos."

    elif contexto.get("estado") == "formalizado":
        respuesta = (
            f"Este chat ya generó el contrato {contexto.get('codigo_contrato')}.\n"
            "¿Deseas crear un nuevo contrato?"
        )

    else:
        respuesta = "No entendí tu solicitud. ¿Podrías ser más específico?"

    msg_usuario = Mensaje(
        chat_id=chat_id,
        contenido=texto_usuario,
        remitente="usuario",
        usuario_id=usuario_id,
        fecha_creacion=datetime.now(),
    )
    db.session.add(msg_usuario)

    msg_sistema = Mensaje(
        chat_id=chat_id,
        contenido=respuesta,
        remitente="sistema",
        fecha_creacion=datetime.now(),
    )
    db.session.add(msg_sistema)

    chat.metadatos = contexto
    db.session.commit()

    yield from stream_response(respuesta)

def texto_normalizado(texto: str) -> str:
    if not texto:
        return ""
    doc = nlp(texto.strip().lower())
    return " ".join([token.lemma_ for token in doc])

def es_afirmativo(texto: str) -> bool:
    txt_norm = texto.lower().strip().replace('.', '')
    return any(af in txt_norm.split() for af in DEF_AFFIRMATIVES)

def es_negativo(texto: str) -> bool:
    txt_norm = texto.lower().strip().replace('.', '')
    return any(neg in txt_norm.split() for neg in DEF_NEGATIVES)

def detectar_tipo_contrato(texto: str) -> str | None:
    if not texto:
        return None
    texto_lower = texto.lower()
    for tipo, info in CONTRACTS.items():
        terminos_de_busqueda = [tipo.replace('_', ' ')] + info.get("sinonimos", [])
        for termino in terminos_de_busqueda:
            if termino.lower() in texto_lower:
                return tipo
    return None
