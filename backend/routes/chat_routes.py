from flask import Blueprint, request, jsonify
from models import Chat, Usuario, Mensaje, Contrato
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

@chat_bp.route('/historial', methods=['GET'])
def historial_chats():
    usuario = request.usuario

    chats = (
        Chat.query
        .filter_by(usuario_id=usuario.id)
        .order_by(Chat.fecha_actualizacion.desc())
        .all()
    )

    respuesta = []

    for chat in chats:
        # Último mensaje (incluye usuario o bot)
        ultimo_mensaje = (
            chat.mensajes
            .order_by(Mensaje.fecha_creacion.desc())
            .first()
        )

        # ¿Tiene contrato?
        contrato = (
            chat.contratos
            .order_by(Contrato.fecha_creacion.desc())
            .first()
        )

        # ¿Tiene preliminar en metadatos?
        preliminar_info = None
        estado = "sin_documentos"

        # Detectar contrato firmado o existente
        if contrato:
            estado = "con_contrato"
        else:
            # Buscar preliminar dentro de metadatos
            # Puedes adaptar si usas otro nombre
            if chat.metadatos and (
                chat.metadatos.get("preliminar_url") or 
                chat.metadatos.get("preliminar") or
                chat.metadatos.get("borrador")
            ):
                estado = "solo_preliminar"
                preliminar_info = {
                    "archivo_url": chat.metadatos.get("preliminar_url") or chat.metadatos.get("preliminar"),
                    "version": chat.metadatos.get("preliminar_version", 1),
                    "datos": chat.metadatos.get("borrador")
                }

        respuesta.append({
            "chat_id": chat.id,
            "nombre": chat.nombre,
            "fecha_creacion": chat.fecha_creacion.isoformat(),
            "fecha_actualizacion": chat.fecha_actualizacion.isoformat(),
            "ultimo_mensaje": ultimo_mensaje.contenido if ultimo_mensaje else None,

            # El estado calculado
            "estado": estado,

            # Contrato si existe
            "contrato": {
                "id": contrato.id,
                "codigo": contrato.codigo,
                "titulo": contrato.titulo,
                "estado": contrato.estado
            } if contrato else None,

            # Preliminar si existe en metadatos
            "preliminar": preliminar_info
        })

    return jsonify({
        "status": "success",
        "message": "Historial obtenido",
        "data": respuesta
    }), 200




@chat_bp.route('/<int:chat_id>', methods=['GET'])
def obtener_chat(chat_id):

    usuario = request.usuario

    chat = Chat.query.filter_by(id=chat_id, usuario_id=usuario.id).first()

    if not chat:
        return jsonify({"error": "Chat no encontrado"}), 404

    # Obtener mensajes
    mensajes = chat.mensajes.order_by(Mensaje.fecha_creacion.asc()).all()

    # Obtener contrato asociado (si existe)
    contrato = (
        chat.contratos
        .order_by(Contrato.fecha_creacion.desc())
        .first()
    )

    return jsonify({
        "chat": {
            "id": chat.id,
            "nombre": chat.nombre,
            "estado": chat.estado,
            "metadatos": chat.metadatos,
            "fecha_creacion": chat.fecha_creacion.isoformat(),
            "fecha_actualizacion": chat.fecha_actualizacion.isoformat(),
        },
        "mensajes": [
            {
                "id": m.id,
                "remitente": m.remitente,
                "contenido": m.contenido,
                "fecha": m.fecha_creacion.isoformat(),
                "contrato_id": m.contrato_id
            } for m in mensajes
        ],
        "contrato": {
            "id": contrato.id,
            "codigo": contrato.codigo,
            "titulo": contrato.titulo,
            "estado": contrato.estado,
            "contenido": contrato.contenido,  # datos preliminares
            "archivo_original_url": contrato.archivo_original_url
        } if contrato else None
    }), 200


# Ruta para generar el documento preliminar (HTML Jinja)
@chat_bp.route('/documento', methods=['GET'])
def generar_documento():
    chat_id = request.args.get("chat_id")
    from services.generation_service import generar_documento_final
    html = generar_documento_final(chat_id)
    return html