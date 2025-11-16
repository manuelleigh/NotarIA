from flask import Blueprint, request, jsonify, Response, stream_with_context
from sqlalchemy import desc
from database import db
from datetime import datetime

# Models
from models import Usuario, Chat, Mensaje, Contrato

# Services
from services.chat_service import procesar_mensaje   # ← ahora este es streaming
from services.generation_service import generar_documento_final, formalizar_contrato

chat_bp = Blueprint("chat_bp", __name__)

def get_user_from_api_key():
    """Extrae el usuario a partir del token Bearer en las cabeceras."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    api_key = auth_header.split(" ")[1]
    return Usuario.query.filter_by(api_key=api_key).first()

# ---------------------------------------------------------------------
# HISTORIAL
# ---------------------------------------------------------------------
@chat_bp.route("/chat/historial", methods=["GET"])
def get_historial():
    usuario = get_user_from_api_key()
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401

    chats = Chat.query.filter_by(usuario_id=usuario.id).order_by(desc(Chat.fecha_creacion)).all()
    
    historial = []
    for chat in chats:
        ultimo_mensaje_obj = Mensaje.query.filter_by(chat_id=chat.id).order_by(desc(Mensaje.fecha_creacion)).first()
        contrato_asociado = Contrato.query.filter_by(chat_id=chat.id).first()
        historial.append({
            "chat_id": chat.id,
            "nombre": chat.nombre,
            "contrato": contrato_asociado is not None,
            "ultimo_mensaje": ultimo_mensaje_obj.contenido if ultimo_mensaje_obj else None,
            "metadatos": chat.metadatos,
        })

    return jsonify({"data": historial})

# ---------------------------------------------------------------------
# DETALLE DEL CHAT
# ---------------------------------------------------------------------
@chat_bp.route("/chat/<int:chat_id>", methods=["GET"])
def get_chat_detalle(chat_id):
    usuario = get_user_from_api_key()
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401

    chat = Chat.query.filter_by(id=chat_id, usuario_id=usuario.id).first()
    if not chat:
        return jsonify({"error": "Chat no encontrado"}), 404

    mensajes = Mensaje.query.filter_by(chat_id=chat_id).order_by(Mensaje.fecha_creacion).all()
    contrato = Contrato.query.filter_by(chat_id=chat_id).first()

    return jsonify({
        "chat": {"id": chat.id, "nombre": chat.nombre, "metadatos": chat.metadatos},
        "mensajes": [
            {
                "id": m.id,
                "contenido": m.contenido,
                "remitente": m.remitente,
                "fecha_creacion": m.fecha_creacion
            }
            for m in mensajes
        ],
        "contrato": {"id": contrato.id} if contrato else None,
    })

# ---------------------------------------------------------------------
# CHAT STREAMING (FLUJO DE CONVERSACIÓN)
# ---------------------------------------------------------------------
@chat_bp.route("/chat/streaming", methods=["POST"])
def handle_chat_streaming():
    usuario = get_user_from_api_key()
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    mensaje = data.get("mensaje")
    chat_id = data.get("chat_id")

    if not mensaje:
        return jsonify({"error": "Mensaje no proporcionado"}), 400

    # Si no existe chat, crear uno
    if not chat_id:
        nuevo_chat = Chat(
            usuario_id=usuario.id,
            nombre=data.get("nombre", f"Contrato - {datetime.now().strftime('%Y-%m-%d')}"),
            metadatos={}
        )
        db.session.add(nuevo_chat)
        db.session.commit()
        chat_id = nuevo_chat.id

    def generate():
        # Streaming real: cada chunk (caracter) se envía al cliente
        for chunk in procesar_mensaje(chat_id, mensaje, usuario.id):
            yield chunk

    return Response(stream_with_context(generate()), mimetype="text/plain")

# ---------------------------------------------------------------------
# DOCUMENTO HTML PREVIEW 
# ---------------------------------------------------------------------
@chat_bp.route("/chat/documento", methods=["GET"])
def get_documento_preview_html():
    chat_id = request.args.get("chat_id")
    if not chat_id:
        return jsonify({"error": "ID de chat no proporcionado"}), 400
    try:
        html_preview = generar_documento_final(chat_id)
        return Response(html_preview, mimetype='text/html')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# FORMALIZAR DOCUMENTO FINAL
# ---------------------------------------------------------------------
@chat_bp.route("/documento/final", methods=["POST"])
def formalize_documento():
    chat_id = request.json.get("chat_id")
    if not chat_id:
        return jsonify({"error": "Chat ID no proporcionado"}), 400
    try:
        codigo = formalizar_contrato(chat_id)
        return jsonify({"codigo_contrato": codigo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
