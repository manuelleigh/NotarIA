from flask import Blueprint, request, jsonify
from models import Chat, Usuario
from database import db
from services.chat_service import procesar_mensaje

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


# ✅ Middleware opcional: Validar token antes de procesar el mensaje
@chat_bp.before_request
def validar_token_chat():
    
    if request.method == 'OPTIONS':
        return {'message': 'ok'}, 200
    
    if request.path == '/chat/documento':
        return None
    
    api_key = request.headers.get("Authorization")
    if not api_key:
        return jsonify({"error": "Token requerido"}), 401

    api_key = api_key.replace("Bearer ", "").strip()
    usuario = Usuario.query.filter_by(api_key=api_key).first()
    if not usuario:
        return jsonify({"error": "Token inválido o usuario no autorizado"}), 403

    request.usuario = usuario


# Ruta principal: manejar conversación
@chat_bp.route('', methods=['POST'])
def manejar_chat():
    data = request.get_json()

    if not data or "mensaje" not in data:
        return jsonify({"error": "El campo 'mensaje' es obligatorio"}), 400

    mensaje = data["mensaje"].strip()
    chat_id = data.get("chat_id")

    # 1️. Si no hay chat_id, crear un nuevo chat
    if not chat_id:
        nuevo_chat = Chat(
            nombre="Nuevo chat legal",
            usuario_id=request.usuario.id,
            fecha_creacion=db.func.now(),
            metadatos={}
        )
        db.session.add(nuevo_chat)
        db.session.commit()
        chat_id = nuevo_chat.id

    try:
        # 2️. Procesar el mensaje con la lógica del servicio
        respuesta = procesar_mensaje(chat_id, mensaje, request.usuario.id)

        # 3️. Recuperar estado actualizado del chat
        chat = Chat.query.get(chat_id)
        contexto = chat.metadatos or {}

        return jsonify({
            "chat_id": chat_id,
            "respuesta": respuesta,
            "estado": contexto.get("estado"),
            "tipo_contrato": contexto.get("tipo_contrato"),
            "pregunta_actual": contexto.get("pregunta_actual"),
            "respuestas": contexto.get("respuestas", {}),
            "clausulas_especiales": contexto.get("clausulas_especiales", []),
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Ocurrió un error al procesar el mensaje: {str(e)}"}), 500


# Ruta para generar el documento preliminar (HTML Jinja)
@chat_bp.route('/documento', methods=['GET'])
def generar_documento():
    chat_id = request.args.get("chat_id")
    from services.generation_service import generar_documento_final
    html = generar_documento_final(chat_id)
    return html