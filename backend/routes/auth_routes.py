from flask import Blueprint, request, jsonify
from models import Usuario
from database import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# @auth_bp.route('/register', methods=['POST'])
# def register():
#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')

#     if Usuario.query.filter_by(username=username).first():
#         return jsonify({"message": "Usuario ya existe"}), 400

#     hashed_password = generate_password_hash(password, method='sha256')
#     new_user = Usuario(username=username, password=hashed_password)

#     return jsonify({"message": "Usuario registrado exitosamente"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario or not usuario.check_password(contrasena):
        return jsonify({"message": "Credenciales inválidas"}), 401

    return jsonify({"api_key": usuario.api_key, "usuario_id": usuario.id}), 200