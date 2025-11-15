from flask import Blueprint, request, jsonify
from models import Usuario
from database import db
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')
    nombre = data.get('nombre')

    if not correo or not contrasena or not nombre:
        return jsonify({"message": "Faltan campos obligatorios"}), 400

    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({"message": "El correo ya está registrado"}), 409

    nuevo_usuario = Usuario(
        correo=correo,
        nombre=nombre,
        rol_id=1, # Rol de usuario por defecto
        tipo_documento_id=1, # Tipo de documento por defecto
        numero_documento="-", # Número de documento por defecto
    )
    nuevo_usuario.set_password(contrasena)
    nuevo_usuario.generate_api_key()

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"api_key": nuevo_usuario.api_key, "usuario_id": nuevo_usuario.id}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario or not usuario.check_password(contrasena):
        return jsonify({"message": "Credenciales inválidas"}), 401

    return jsonify({"api_key": usuario.api_key, "usuario_id": usuario.id}), 200
