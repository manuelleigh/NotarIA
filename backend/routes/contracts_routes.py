from flask import Blueprint, request, jsonify
from models import Contrato
from database import db

contratos_bp = Blueprint('contratos', __name__, url_prefix='/contratos')


# Middleware: reutilizamos la validación usada en chat
@contratos_bp.before_request
def validar_token_contratos():

    if request.method == 'OPTIONS':
        return {'message': 'ok'}, 200

    api_key = request.headers.get("Authorization")
    if not api_key:
        return jsonify({"error": "Token requerido"}), 401

    api_key = api_key.replace("Bearer ", "").strip()
    from models import Usuario
    usuario = Usuario.query.filter_by(api_key=api_key).first()

    if not usuario:
        return jsonify({"error": "Token inválido o usuario no autorizado"}), 403

    request.usuario = usuario


# ------------------------------------------------------------
# ENDPOINT: Obtener todos los contratos generados por el usuario
# ------------------------------------------------------------
@contratos_bp.route('', methods=['GET'])
def listar_contratos_usuario():

    usuario = request.usuario

    contratos = (
        Contrato.query
        .filter_by(creador_id=usuario.id)
        .order_by(Contrato.fecha_creacion.desc())
        .all()
    )

    lista = []
    for c in contratos:
        lista.append({
            "id": c.id,
            "codigo": c.codigo,
            "titulo": c.titulo,
            "descripcion": c.descripcion,
            "estado": c.estado,
            "fecha_creacion": c.fecha_creacion.isoformat(),
            "fecha_firma": c.fecha_firma.isoformat() if c.fecha_firma else None,
            "tipo_contrato_id": c.tipo_contrato_id,
            "chat_id": c.chat_id,
            "archivo_original_url": c.archivo_original_url,
            "archivo_firmado_url": c.archivo_firmado_url
        })

    return jsonify({
        "total": len(lista),
        "contratos": lista
    }), 200
