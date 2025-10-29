from models import Usuario, Rol, TipoEvidencia, TipoContrato, TipoDocumento
from database import db
from werkzeug.security import generate_password_hash

def seed_data():
    # ======== ROLES ========
    roles_data = [
        {"nombre": "administrador"},
        {"nombre": "cliente"},
        {"nombre": "firmante"},
        {"nombre": "auditador"}
    ]

    for rol in roles_data:
        if not Rol.query.filter_by(nombre=rol["nombre"]).first():
            db.session.add(Rol(**rol))

    db.session.commit()

    # ======== TIPOS DE EVIDENCIA ========
    evidencias_data = [
        {"descripcion": "PDF firmado"},
        {"descripcion": "Hash SHA-256"},
        {"descripcion": "Sello TSA"},
        {"descripcion": "IP y User Agent"},
        {"descripcion": "Video de validacion"},
        {"descripcion": "Blockchain"}
    ]

    for ev in evidencias_data:
        if not TipoEvidencia.query.filter_by(descripcion=ev["descripcion"]).first():
            db.session.add(TipoEvidencia(**ev))
    
    db.session.commit()

    # ======== TIPOS DE CONTRATO ========
    tipos_contrato_data = [
        # A. Contratos civiles y comerciales
        {"descripcion": "arrendamiento", "plantilla": "arrendamiento_template"},
        {"descripcion": "prestacion_servicios", "plantilla": "prestacion_servicios_template"},
        {"descripcion": "compraventa_bienes_muebles", "plantilla": "compraventa_bienes_muebles_template"},
        {"descripcion": "comodato", "plantilla": "comodato_template"},
        {"descripcion": "mutuo", "plantilla": "mutuo_template"},
        {"descripcion": "reconocimiento_deuda", "plantilla": "reconocimiento_deuda_template"},
        {"descripcion": "trabajo_privado", "plantilla": "trabajo_privado_template"},
        {"descripcion": "carta_poder", "plantilla": "carta_poder_template"},
        {"descripcion": "asociacion_en_participacion", "plantilla": "asociacion_en_participacion_template"},
        {"descripcion": "confidencialidad", "plantilla": "confidencialidad_template"},
        {"descripcion": "franquicia", "plantilla": "franquicia_template"},
        {"descripcion": "publicidad", "plantilla": "publicidad_template"},
    ]


    for tc in tipos_contrato_data:
        if not TipoContrato.query.filter_by(descripcion=tc["descripcion"]).first():
            db.session.add(TipoContrato(**tc))

    db.session.commit()
    
    # ======== TIPO DE DOCUMENTO ========
    tipos_documento_data = [
        {"descripcion": "DNI"},
        {"descripcion": "Pasaporte"},
        {"descripcion": "Carnet de extranjeria"},
        {"descripcion": "RUC"}
    ]
    for td in tipos_documento_data:
        if not TipoDocumento.query.filter_by(descripcion=td["descripcion"]).first():
            db.session.add(TipoDocumento(**td))
    
    # ======== USUARIO ADMIN POR DEFECTO ========
    admin_email = "manuelleigh@notaria.pe"
    admin_password = "leigh2810"
    admin_existente = Usuario.query.filter_by(correo=admin_email).first()

    if not admin_existente:
        rol_admin = Rol.query.filter_by(nombre="administrador").first()
        tipo_documento_admin = TipoDocumento.query.filter_by(descripcion="DNI").first()

        admin = Usuario(
            nombre="Manuel Leigh",
            correo=admin_email,
            numero_documento="76854553",
            
            tipo_documento_id=tipo_documento_admin.id,
            rol_id=rol_admin.id
        )

        admin.set_password(admin_password)
        admin.generate_api_key()
        db.session.add(admin)
        db.session.commit()
        print(f"Usuario administrador creado: {admin_email} / Contraseña: {admin_password}")
    else:
        print("El usuario administrador ya existe, no se duplicó.")

    # ======== USUARIO DE PRUEBA ========
    rol_demo = Rol.query.filter_by(nombre="cliente").first()
    tipo_documento_demo = TipoDocumento.query.filter_by(descripcion="DNI").first()
    test_user = Usuario(
        nombre='Usuario Prueba',
        correo='prueba@gmail.com',
        numero_documento='12345678',
        
        tipo_documento_id=tipo_documento_demo.id,
        rol_id=rol_demo.id,        
    )
    
    test_user.set_password('prueba1234')
    test_user.generate_api_key()    
    
    db.session.add(test_user)
    db.session.commit()

    print("Datos iniciales cargados correctamente.")
