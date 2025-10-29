import os
import jinja2
from models import Chat, TipoContrato, Firmante, Contrato, TipoDocumento, Rol
from database import db
from data.contracts_data import CONTRACTS, CLAUSULAS_MAPEADAS
from services.data_processors import PROCESSOR_REGISTRY

from services.nlp_utils import get_nlp
nlp = get_nlp()

# --- Configuración de Jinja2 ---
try:
    script_dir = os.path.dirname(__file__)
    template_path = os.path.join(script_dir, '..', 'templates')
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path),
        autoescape=jinja2.select_autoescape(['html', 'xml'])
    )
except Exception as e:
    print(f"Error cargando el entorno Jinja2: {e}")
    jinja_env = None

def _procesar_clausulas_especiales(lista_clausulas_raw):
    """
    Toma la lista de cláusulas en lenguaje natural del usuario y
    las mapea a cláusulas formales o las incluye como "ad-hoc".
    """
    clausulas_formales = []
    if not nlp:
        print("spaCy no está cargado. Omitiendo categorización de cláusulas.")
        return []

    doc_clausulas = [nlp(c.lower()) for c in lista_clausulas_raw]

    for i, doc in enumerate(doc_clausulas):
        raw_text = lista_clausulas_raw[i]
        found = False
        
        # 1. Intentar mapear a una cláusula estándar
        for key, data in CLAUSULAS_MAPEADAS.items():
            # Usar lemas (forma base de la palabra) para mejor coincidencia
            lemmas_doc = {token.lemma_ for token in doc}
            lemmas_keywords = {nlp(k)[0].lemma_ for k in data["keywords"]}
            
            # Si hay una intersección de palabras clave
            if lemmas_doc.intersection(lemmas_keywords):
                clausulas_formales.append({
                    "titulo": data["titulo"],
                    "texto": data["texto"],
                    "origen_usuario": raw_text # Guardamos lo que dijo el usuario
                })
                found = True
                break
        
        # 2. Si no se mapea, agregar como cláusula "ad-hoc"
        if not found:
            clausulas_formales.append({
                "titulo": "Cláusula Adicional (A solicitud)",
                "texto": raw_text,
                "origen_usuario": raw_text
            })
            
    return clausulas_formales

def generar_documento_final(chat_id):
    """
    Función de orquestación para el PRELIMINAR (HTML).
    1. Procesa los datos crudos.
    2. GUARDA el JSON limpio en chat.metadatos["contexto_limpio"].
    3. CAMBIA el estado del chat a "esperando_aprobacion_formal".
    4. Renderiza la plantilla Jinja2 para la vista previa.
    """
    if not jinja_env:
        raise RuntimeError("El entorno de plantillas Jinja2 no está inicializado.")

    chat = Chat.query.get(chat_id)
    if not chat:
        raise ValueError("Chat no encontrado")

    metadata = chat.metadatos

    # --- 1. Caso: recarga de contrato ya generado ---
    if metadata.get("estado") == "esperando_aprobacion_formal":
        contexto_jinja, plantilla_alias = procesar_datos_crudos(metadata, chat, actualizar_estado=False)

    # --- 2. Caso: primera generación ---
    elif metadata.get("estado") == "generando_contrato":
        contexto_jinja, plantilla_alias = procesar_datos_crudos(metadata, chat, actualizar_estado=True)

    else:
        raise ValueError(f"El chat no está en estado 'generando_contrato', sino en '{metadata.get('estado')}'")

    # --- 3. Renderizar Plantilla Jinja2 (Vista Previa) ---
    print("🧩 Contexto renta:", contexto_jinja.get("renta"))

    try:
        template_name = f"{plantilla_alias}.html"
        template = jinja_env.get_template(template_name)
        html_final = template.render(**contexto_jinja)
        return html_final

    except jinja2.exceptions.TemplateNotFound:
        raise FileNotFoundError(f"No se encontró la plantilla: {template_name}")
    except Exception as e:
        raise RuntimeError(f"Error al renderizar la plantilla Jinja2: {str(e)}")


def procesar_datos_crudos(metadata, chat, actualizar_estado=True):
    tipo_contrato = metadata["tipo_contrato"]
    respuestas_raw = metadata["respuestas"]
    clausulas_raw = metadata.get("clausulas_especiales", [])
    contrato_info = CONTRACTS[tipo_contrato]

    # --- 2. Procesar Datos Crudos (Build Context) ---
    contexto_jinja = {}
    for pregunta_info in contrato_info["preguntas"]:
        key = pregunta_info["key"]
        tipo_dato = pregunta_info["tipo_dato"]
        raw_value = respuestas_raw.get(key)
        
        if not raw_value:
            continue

        processor_func = PROCESSOR_REGISTRY.get(tipo_dato)
        
        if processor_func:
            try:
                contexto_jinja[key] = processor_func(raw_value)
            except Exception as e:
                print(f"Error procesando {key}: {e}")
                contexto_jinja[key] = {"error": str(e)}
        else:
            contexto_jinja[key] = raw_value

    # --- 3. Procesar Cláusulas Especiales ---
    contexto_jinja["clausulas_adicionales"] = _procesar_clausulas_especiales(clausulas_raw)

    # --- 4. Añadir Metadatos Finales ---
    contexto_jinja["titulo_contrato"] = contrato_info["nombre"]
    plantilla_alias = contrato_info["plantilla_alias"]

    # --- 4.1 Procesar arrendador y arrendatario con tratamiento fijo ---
    if "arrendador" in respuestas_raw:
        contexto_jinja["arrendador"]["tratamiento"] = "EL ARRENDADOR"

    if "arrendatario" in respuestas_raw:
        contexto_jinja["arrendatario"]["tratamiento"] = "EL ARRENDATARIO"

    # --- 5. Guardar contexto y cambiar estado (solo si es la primera generación) ---
    if actualizar_estado:
        try:
            chat.metadatos["contexto_limpio"] = contexto_jinja
            chat.metadatos["estado"] = "esperando_aprobacion_formal"
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise RuntimeError(f"Error al actualizar estado del chat: {str(e)}")
    else:
        chat.metadatos["contexto_limpio"] = contexto_jinja
        db.session.commit()

    return contexto_jinja, plantilla_alias




# --- FUNCIÓN 2: FORMALIZAR CONTRATO (NUEVA) ---

def _generar_codigo_contrato():
    """Genera un código único para el contrato."""
    now = datetime.utcnow()
    count = Contrato.query.filter(db.func.DATE(Contrato.fecha_creacion) == now.date()).count() + 1
    return f"CONT-{now.year}-{now.month:02d}-{now.day:02d}-{count:04d}"

def formalizar_contrato(chat_id):
    """
    Función de formalización (Escritura en BBDD).
    1. Lee el "contexto_limpio" guardado en el chat.
    2. Crea el registro "Contrato" en la BBDD.
    3. Crea los registros "Firmante" asociados.
    4. Devuelve el código del nuevo contrato.
    """
    chat = Chat.query.get(chat_id)
    if not chat or chat.metadatos.get("estado") != "esperando_aprobacion_formal":
        raise ValueError("El chat no está en estado de aprobación.")

    contexto_limpio = chat.metadatos.get("contexto_limpio")
    if not contexto_limpio:
        raise ValueError("No se encontró el 'contexto_limpio' para formalizar.")
        
    tipo_contrato_alias = CONTRACTS[chat.metadatos["tipo_contrato"]]["plantilla_alias"]
    titulo_contrato = contexto_limpio.get("titulo_contrato", "Contrato sin título")

    try:
        # 1. Buscar el TipoContrato en la BBDD
        # Asumimos que 'plantilla_alias' mapea al campo 'plantilla' en TipoContrato
        tipo_contrato_db = TipoContrato.query.filter_by(plantilla=tipo_contrato_alias).first()
        if not tipo_contrato_db:
            # Fallback por si no existe, crea uno (o puedes lanzar error)
            print(f"Advertencia: No se encontró TipoContrato para {tipo_contrato_alias}, creando uno nuevo.")
            tipo_contrato_db = TipoContrato(descripcion=titulo_contrato, plantilla=tipo_contrato_alias)
            db.session.add(tipo_contrato_db)
            db.session.flush() # Para obtener el ID

        # 2. Crear el Contrato
        nuevo_contrato = Contrato(
            codigo = _generar_codigo_contrato(),
            titulo = titulo_contrato,
            creador_id = chat.usuario_id,
            chat_id = chat.id,
            tipo_contrato_id = tipo_contrato_db.id,
            estado = "borrador", # Estado inicial del modelo Contrato
            contenido = contexto_limpio # ¡Aquí se guarda el JSON limpio!
        )
        db.session.add(nuevo_contrato)
        db.session.flush() # Para obtener el nuevo_contrato.id

        # 3. Crear los Firmantes
        contrato_info = CONTRACTS[chat.metadatos["tipo_contrato"]]
        
        tipo_doc_dni = TipoDocumento.query.filter_by(descripcion="DNI").one_or_none()
        if not tipo_doc_dni:
            print("Advertencia: TipoDocumento 'DNI' no encontrado en la BBDD.")

        for pregunta in contrato_info["preguntas"]:
            if pregunta.get("es_firmante"):
                key = pregunta["key"]
                rol_nombre = pregunta["rol_firmante"]
                
                # Buscar el Rol en la BBDD
                rol_db = db.session.query(Rol).filter_by(nombre=rol_nombre).first()
                if not rol_db:
                    print(f"Creando Rol faltante: {rol_nombre}")
                    rol_db = Rol(nombre=rol_nombre)
                    db.session.add(rol_db)
                    db.session.flush() # Para obtener el ID
                
                # Obtener datos del firmante del JSON limpio
                firmante_data = contexto_limpio.get(key)
                if not firmante_data:
                    print(f"Advertencia: Faltan datos para el firmante '{key}'")
                    continue
                
                # Extraer datos según el tipo_dato
                nombre_firmante = firmante_data.get("nombre_completo") or firmante_data.get("nombre_razon_social")
                doc_firmante = firmante_data.get("dni") or firmante_data.get("documento_numero")
                
                # NOTA: Tu chat no pide email/teléfono. Son NULL aquí.
                # Deberías añadir pasos al chat para pedir email/teléfono antes de formalizar.
                
                nuevo_firmante = Firmante(
                    contrato_id = nuevo_contrato.id,
                    nombre = nombre_firmante,
                    numero_documento = doc_firmante,
                    tipo_documento_id = tipo_doc_dni.id if tipo_doc_dni else None,
                    rol_firmante_id = rol_db.id,
                    estado = "INVITADO"
                    # correo y telefono quedan null
                )
                db.session.add(nuevo_firmante)

        # 4. Confirmar la transacción
        chat.metadatos["estado"] = "formalizado" # Estado final del chat
        chat.metadatos["contrato_id_generado"] = nuevo_contrato.id
        db.session.commit()
        
        return nuevo_contrato.codigo

    except Exception as e:
        db.session.rollback()
        # Revertir estado del chat si la formalización falla
        chat.metadatos["estado"] = "esperando_aprobacion_formal"
        db.session.commit()
        raise RuntimeError(f"Error al formalizar el contrato: {str(e)}")