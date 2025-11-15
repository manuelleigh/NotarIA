from flask import Blueprint, request, jsonify, url_for
from models import Usuario
from database import db
from werkzeug.security import generate_password_hash
from services.email_service import send_password_reset_email
from datetime import datetime

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
        rol_id=1, 
        tipo_documento_id=1, 
        numero_documento="-",
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


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    correo = data.get('correo')

    usuario = Usuario.query.filter_by(correo=correo).first()
    if not usuario:
        # Aún si el usuario no existe, devolvemos una respuesta genérica
        # para no revelar qué correos están registrados en el sistema.
        return jsonify({"message": "Si tu correo está registrado, recibirás un enlace para restablecer tu contraseña."}), 200

    # Generar token y guardarlo en la base de datos
    usuario.generate_reset_token()
    db.session.commit()

    # Construir el enlace de reseteo (esto asume que tu frontend tiene una ruta /reset-password)
    # Asegúrate de configurar la URL base de tu frontend, por ejemplo, desde una variable de entorno.
    FRONTEND_URL = "http://localhost:3000" # O la URL de producción
    reset_link = f"{FRONTEND_URL}/reset-password?token={usuario.reset_token}"

    # Enviar el correo
    success, message = send_password_reset_email(usuario.correo, usuario.nombre, reset_link)

    if not success:
        # Si el correo falla, es importante no revelar el error al cliente.
        # Registra el error internamente, pero el usuario no debe saberlo.
        print(f"Error interno al enviar correo a {usuario.correo}: {message}")
        # Devolvemos un mensaje genérico para no dar pistas sobre el estado del sistema.

    return jsonify({"message": "Si tu correo está registrado, recibirás un enlace para restablecer tu contraseña."}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    nueva_contrasena = data.get('nueva_contrasena')

    if not token or not nueva_contrasena:
        return jsonify({"message": "Faltan el token y la nueva contraseña."}), 400

    # Buscar usuario por el token
    usuario = Usuario.query.filter_by(reset_token=token).first()

    # Validar que el token sea correcto y no haya expirado
    if not usuario or usuario.reset_token_expiration < datetime.utcnow():
        return jsonify({"message": "El token es inválido o ha expirado."}), 400

    # Actualizar contraseña
    usuario.set_password(nueva_contrasena)
    
    # Anular el token para que no pueda ser reutilizado
    usuario.reset_token = None
    usuario.reset_token_expiration = None
    
    db.session.commit()

    return jsonify({"message": "Tu contraseña ha sido actualizada exitosamente."}), 200
