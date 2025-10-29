from models import Chat, Mensaje, Usuario
from database import db
from datetime import datetime
from data.contracts_data import CONTRACTS, DEF_AFFIRMATIVES, DEF_NEGATIVES
from services.generation_service import formalizar_contrato
from services.data_processors import PROCESSOR_REGISTRY
from services.nlp_utils import get_nlp

# Inicializamos el modelo NLP (spaCy)
nlp = get_nlp()


# ------------------------------------------------------------
# FUNCIÓN PRINCIPAL: flujo de conversación del chatbot legal
# ------------------------------------------------------------
def procesar_mensaje(chat_id, texto_usuario, usuario_id):
    """
    Controla el flujo conversacional:
    - Detecta el tipo de contrato
    - Recolecta respuestas
    - Solicita confirmaciones
    - Genera contrato preliminar o formalizado
    """
    chat = Chat.query.get(chat_id)
    if not chat:
        raise ValueError("Chat no encontrado")

    contexto = chat.metadatos or {}

    # 🧩 1. Detectar el tipo de contrato (inicio de conversación)
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

    # 🧩 2. Recolectando respuestas del usuario
    elif contexto.get("estado") == "solicitando_datos":
        tipo = contexto["tipo_contrato"]
        i = contexto.get("pregunta_actual", 0)
        respuestas = contexto.get("respuestas", {})

        pregunta_actual = CONTRACTS[tipo]["preguntas"][i]
        clave_semantica = pregunta_actual["key"]
        respuestas[clave_semantica] = texto_usuario
        contexto["respuestas"] = respuestas

        # Pasar a la siguiente pregunta o finalizar la recolección
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

    # 🧩 3. Mostrar resumen para revisión
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

    # 🧩 4. Confirmación antes de generar el contrato
    elif contexto.get("estado") == "preliminar_confirmacion":
        txt_norm = texto_normalizado(texto_usuario)

        if es_afirmativo(txt_norm):
            contexto["estado"] = "clausulas_especiales"
            respuesta = (
                "Perfecto 👍. Antes de generar el contrato preliminar, "
                "¿deseas agregar alguna cláusula especial o condición adicional? "
                "Por ejemplo: penalidades, ampliaciones o condiciones de pago."
            )
        elif es_negativo(txt_norm):
            respuesta = "Entendido. ¿Qué información te gustaría corregir o agregar?"
        else:
            respuesta = (
                "Por favor, responde 'sí' para confirmar o 'no' si deseas modificar algún dato."
            )

    # 🧩 5. Registro de cláusulas especiales
    elif contexto.get("estado") == "clausulas_especiales":
        txt_norm = texto_normalizado(texto_usuario)

        if es_negativo(txt_norm):
            contexto["estado"] = "generando_contrato"
            contexto["clausulas_especiales"] = []
            respuesta = "Perfecto. Procederé a generar el contrato preliminar sin cláusulas adicionales."
        elif es_afirmativo(txt_norm):
            contexto["estado"] = "registrando_clausulas"
            respuesta = (
                "Muy bien. Escribe las cláusulas o condiciones que quieras incluir.\n"
                "Por ejemplo: 'El inquilino no podrá subarrendar el inmueble sin autorización escrita del arrendador.'"
            )
        else:
            contexto.setdefault("clausulas_especiales", [])
            contexto["clausulas_especiales"].append(texto_usuario)
            respuesta = "Cláusula registrada ✅. ¿Deseas agregar otra más o continuamos con el contrato?"

    # 🧩 6. Registro múltiple de cláusulas
    elif contexto.get("estado") == "registrando_clausulas":
        txt_norm = texto_normalizado(texto_usuario)
        if es_negativo(txt_norm):
            clausulas = contexto.get("clausulas_especiales", [])
            contexto["clausulas_validadas"] = [revisar_clausula(c) for c in clausulas]
            contexto["estado"] = "generando_contrato"
            respuesta = "Entendido. Procederé a generar el contrato con las cláusulas registradas."
        else:
            contexto.setdefault("clausulas_especiales", [])
            contexto["clausulas_especiales"].append(texto_usuario)
            respuesta = "Cláusula agregada ✅. ¿Deseas incluir otra más?"

    # 🧩 7. Estado generando contrato (trigger para /documento)
    elif contexto.get("estado") == "generando_contrato":
        respuesta = (
            "Perfecto. Estoy generando el documento preliminar. "
            "Un momento por favor..."
        )

    # 🧩 8. Esperando aprobación formal
    elif contexto.get("estado") == "esperando_aprobacion_formal":
        txt_norm = texto_normalizado(texto_usuario)

        if es_afirmativo(txt_norm):
            try:
                codigo_contrato = formalizar_contrato(chat_id)
                contexto["estado"] = "formalizado"
                contexto["codigo_contrato"] = codigo_contrato

                respuesta = (
                    f"¡Perfecto! ✅ Se ha formalizado tu contrato.\n\n"
                    f"**Código de Contrato:** {codigo_contrato}\n\n"
                    "¿Deseas que prepare el envío a la plataforma de firma (Keynua)?"
                )
            except Exception as e:
                print(f"Error en formalización: {e}")
                respuesta = "⚠️ Error al intentar formalizar el contrato. Intenta nuevamente."
        elif es_negativo(txt_norm):
            contexto["estado"] = "revision"
            respuesta = "Entendido. Volvamos a la revisión. ¿Deseas ver el resumen de nuevo?"
        else:
            respuesta = "Por favor, responde 'sí' para aprobar o 'no' para revisar."

    # 🧩 9. Estado final (contrato ya formalizado)
    elif contexto.get("estado") == "formalizado":
        respuesta = (
            f"Este chat ya generó el contrato {contexto.get('codigo_contrato')}.\n"
            "¿Deseas crear un nuevo contrato?"
        )
        contexto = {}

    else:
        respuesta = "No entendí tu solicitud. ¿Deseas crear un nuevo contrato?"

    # --- Guardar mensajes ---
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

    # Actualizar metadatos
    chat.metadatos = contexto
    db.session.commit()

    return respuesta


# ------------------------------------------------------------
# PROCESAMIENTO DE DATOS DEL CONTRATO
# ------------------------------------------------------------
def procesar_datos_contrato(tipo_contrato: str, respuestas_usuario: dict) -> dict:
    """
    Usa los procesadores definidos en data_processors.py según el tipo de contrato.
    Retorna un diccionario estructurado listo para usar en las plantillas Jinja2.
    """
    if tipo_contrato not in CONTRACTS:
        raise ValueError(f"Tipo de contrato no reconocido: {tipo_contrato}")

    contrato_config = CONTRACTS[tipo_contrato]
    datos_procesados = {}

    for campo in contrato_config.get("preguntas", []):
        nombre_campo = campo["key"]
        tipo_dato = campo.get("tipo_dato")
        valor_usuario = respuestas_usuario.get(nombre_campo, "")

        procesador = PROCESSOR_REGISTRY.get(tipo_dato)
        if procesador:
            try:
                resultado = procesador(valor_usuario)
                datos_procesados[nombre_campo] = resultado
            except Exception as e:
                print(f"⚠️ Error procesando campo '{nombre_campo}': {e}")
                datos_procesados[nombre_campo] = valor_usuario
        else:
            datos_procesados[nombre_campo] = valor_usuario

    # Si existe un procesador global para el tipo de contrato
    procesador_contrato = PROCESSOR_REGISTRY.get(tipo_contrato)
    if procesador_contrato:
        try:
            datos_finales = procesador_contrato(datos_procesados)
        except Exception as e:
            print(f"⚠️ Error aplicando procesador del contrato '{tipo_contrato}': {e}")
            datos_finales = datos_procesados
    else:
        datos_finales = datos_procesados

    return datos_finales


# ------------------------------------------------------------
# UTILIDADES NLP
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


def revisar_clausula(clausula: str) -> str:
    clausula_lower = clausula.lower()
    if "violencia" in clausula_lower or "ilegal" in clausula_lower:
        return "⚠️ Esta cláusula parece contener términos inapropiados o no válidos legalmente."
    elif "pena" in clausula_lower or "multa" in clausula_lower:
        return "✔️ Cláusula de penalidad detectada. Se incluirá con redacción formal estándar."
    else:
        return "✔️ Cláusula revisada y considerada válida."


def detectar_tipo_contrato(texto: str) -> str | None:
    """
    Usa NLP para detectar el tipo de contrato (por sinonimia o similitud semántica).
    """
    if not texto:
        return None

    doc_texto = nlp(texto.lower())
    lemmas_texto = [token.lemma_ for token in doc_texto]

    for tipo, info in CONTRACTS.items():
        sinonimos = info.get("sinonimos", [])
        lemmas_sinonimos = [token.lemma_ for s in sinonimos for token in nlp(s.lower())]

        if any(s in lemmas_texto for s in lemmas_sinonimos):
            return tipo

        # Similaridad semántica si no hay coincidencia directa
        for token in doc_texto:
            for sinonimo in sinonimos:
                similitud = token.similarity(nlp(sinonimo))
                if similitud >= 0.75:
                    return tipo

    return None