from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.chat_service import procesar_mensaje
from services.generation_service import generar_contrato_final, generar_contrato_preview
from services.chat_service_streaming import procesar_mensaje_streaming
from models import Chat, Usuario
from database import db
from datetime import datetime

chat_bp = Blueprint("chat_bp", __name__)

@chat_bp.route("/chat/send", methods=["POST"])
def handle_chat():
    data = request.json
    user_id = data.get("user_id")
    chat_id = data.get("chat_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"error": "Faltan datos requeridos"}), 400

    if not chat_id:
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        nuevo_chat = Chat(
            usuario_id=user_id,
            nombre=f"Contrato - {datetime.now().strftime('%Y-%m-%d')}",
            metadatos={}
        )
        db.session.add(nuevo_chat)
        db.session.commit()
        chat_id = nuevo_chat.id

    respuesta = procesar_mensaje(chat_id, message, user_id)
    return jsonify({"response": respuesta, "chat_id": chat_id})


@chat_bp.route("/chat/streaming", methods=["POST"])
def handle_chat_streaming():
    data = request.json
    contexto = data.get("contexto") # El contexto de la conversación
    texto_usuario = data.get("message")

    if not texto_usuario:
        return jsonify({"error": "Mensaje no proporcionado"}), 400

    # El generador que produce la respuesta en trozos
    def generate():
        for chunk in procesar_mensaje_streaming(contexto, texto_usuario):
            # Si es un diccionario, es el contexto actualizado al final
            if isinstance(chunk, dict):
                # Podrías querer guardar este contexto en algún lugar
                # Por ahora, solo lo usamos para la lógica de la conversación
                pass
            else:
                yield chunk # Envía el trozo de texto

    return Response(stream_with_context(generate()), mimetype='text/plain')


@chat_bp.route("/documento/preview", methods=["POST"])
def get_documento_preview():
    chat_id = request.json.get("chat_id")
    if not chat_id:
        return jsonify({"error": "ID de chat no proporcionado"}), 400

    try:
        html_preview = generar_contrato_preview(chat_id)
        return jsonify({"preview_html": html_preview})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/documento/final", methods=["POST"])
def get_documento_final():
    chat_id = request.json.get("chat_id")
    
    if not chat_id:
        return jsonify({"error": "Chat ID no proporcionado."}), 400
    
    try:
        codigo = generar_contrato_final(chat_id)
        return jsonify({"codigo_contrato": codigo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
