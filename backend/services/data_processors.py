import re
from data.contracts_data import DEF_AFFIRMATIVES, DEF_NEGATIVES
from num2words import num2words
from datetime import datetime
import requests
from datetime import datetime, timedelta
from dateutil import parser

from services.nlp_utils import get_nlp
nlp = get_nlp()

# --- 1. Definición de Funciones de Procesamiento (Reutilizables) ---

def procesar_persona_dni(texto):
    """
    Extrae 'Nombre Completo' y 'DNI' (8 dígitos) de un string.
    Retorna: {"nombre_completo": str, "dni": str}
    """
    dni_match = re.search(r'(\d{8})', texto)
    dni = dni_match.group(1) if dni_match else None
    nombre = texto
    
    if dni:
        # Remover el DNI del texto para obtener el nombre
        nombre = texto.replace(dni, "").strip()
        # Limpiar puntuación común al final del nombre
        nombre = re.sub(r'[\.,;]$', '', nombre).strip()
        
    return {"nombre_completo": nombre, "dni": dni}

def procesar_persona_empresa(texto):
    """
    Extrae nombre/razón social y un documento (DNI de 8 o RUC de 11 dígitos).
    Da prioridad al RUC si ambos patrones coinciden.
    Retorna: {"nombre_razon_social": str, "documento_tipo": str, "documento_numero": str}
    """
    ruc_match = re.search(r'(\d{11})', texto)
    dni_match = re.search(r'(\d{8})', texto)
    
    doc_numero = None
    doc_tipo = None
    nombre = texto

    if ruc_match:
        doc_numero = ruc_match.group(1)
        doc_tipo = "RUC"
    elif dni_match:
        doc_numero = dni_match.group(1)
        doc_tipo = "DNI"

    if doc_numero:
        nombre = texto.replace(doc_numero, "").strip()
        nombre = re.sub(r'[\.,;]$', '', nombre).strip()
        
    return {
        "nombre_razon_social": nombre, 
        "documento_tipo": doc_tipo, 
        "documento_numero": doc_numero
    }

def procesar_direccion_descripcion(texto):
    """
    Procesa un texto que describe una dirección.
    Retorna: {"direccion_completa": str}
    """
    return {"direccion_completa": texto.strip()}

def procesar_objeto_descripcion(texto):
    """
    Procesa un texto que describe el objeto del contrato (ej. el bien).
    Retorna: {"descripcion": str}
    """
    return {"descripcion": texto.strip()}

def procesar_rango_fecha(texto):
    """
    Extrae fecha de inicio y fin desde un string ("Desde X hasta Y").
    Usa dateparser para entender lenguaje natural.
    Retorna: {"fecha_inicio": str, "fecha_fin": str, "fecha_inicio_larga": str, "fecha_fin_larga": str}
    """
    partes = re.split(r'\s+(hasta|al)\s+', texto, maxsplit=1, flags=re.IGNORECASE)
    fecha_inicio_str = partes[0].replace("Desde el", "").strip()
    fecha_fin_str = partes[2].strip() if len(partes) > 2 else None

    # Configuración para parsear fechas en español (Día/Mes/Año)
    settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'future'}
    
    f_inicio = dateparser.parse(fecha_inicio_str, languages=['es'], settings=settings)
    
    # Si no se da año para la fecha fin, infiere el de la fecha inicio
    if f_inicio and fecha_fin_str:
        f_fin = dateparser.parse(fecha_fin_str, languages=['es'], settings=settings)
        if f_fin and f_inicio.year > f_fin.year:
             f_fin = f_fin.replace(year=f_inicio.year)
    else:
        f_fin = None

    def format_fecha_larga(fecha_obj):
        if not fecha_obj: return ""
        # Cargar locale en español para nombres de meses
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            pass # Fallback a formato por defecto si locale falla
        return fecha_obj.strftime("%d de %B de %Y")

    return {
        "fecha_inicio": f_inicio.strftime("%Y-%m-%d") if f_inicio else None,
        "fecha_fin": f_fin.strftime("%Y-%m-%d") if f_fin else None,
        "fecha_inicio_larga": format_fecha_larga(f_inicio),
        "fecha_fin_larga": format_fecha_larga(f_fin)
    }

def procesar_monto_renta_garantia(texto):
    """
    Extrae montos de alquiler (renta) y garantía de un string.
    Retorna: {"monto_alquiler_num": float, "monto_alquiler_texto": str, 
              "monto_garantia_num": float, "monto_garantia_texto": str, "moneda": str}
    """
    monto_alquiler = 0.0
    monto_garantia = 0.0
    moneda = "soles" # Moneda por defecto

    # Buscar moneda (soles o dólares)
    if "dólares" in texto.lower() or "dolares" in texto.lower() or "usd" in texto.lower():
        moneda = "dólares"

    # Extraer renta (ej: "400 soles mensuales", "renta de 400")
    match_alquiler = re.search(r'(\d+[\d\.,]*)\s*.*(mensual|renta)', texto, re.IGNORECASE)
    if not match_alquiler:
         # Fallback si no dice "mensual" (ej: "se pagan 400")
         match_alquiler = re.search(r'(\d+[\d\.,]*)', texto)
         
    if match_alquiler:
        monto_alquiler = float(match_alquiler.group(1).replace(",", ""))

    # Extraer garantía (ej: "garantia de 200", "200 de garantia")
    match_garantia = re.search(r'(garantia|adelanto)\s*(de|)\s*(\d+[\d\.,]*)', texto, re.IGNORECASE)
    if match_garantia:
        monto_garantia = float(match_garantia.group(3).replace(",", ""))
    else:
        # Fallback (ej: "200 de garantia")
        match_garantia_alt = re.search(r'(\d+[\d\.,]*)\s*.*(garantia|adelanto)', texto, re.IGNORECASE)
        if match_garantia_alt:
             monto_garantia = float(match_garantia_alt.group(1).replace(",", ""))

    # Convertir a texto formal
    # Nota: num2words 'to=currency' es limitado. 'to=spell' es más universal.
    alquiler_texto = num2words(monto_alquiler, lang='es')
    garantia_texto = num2words(monto_garantia, lang='es')

    return {
        "monto_alquiler_num": monto_alquiler,
        "monto_alquiler_texto": f"{alquiler_texto.capitalize()} y 00/100 {moneda}",
        "monto_garantia_num": monto_garantia,
        "monto_garantia_texto": f"{garantia_texto.capitalize()} y 00/100 {moneda}",
        "moneda": moneda.capitalize()
    }

def procesar_texto_simple(texto):
    """
    Simplemente retorna el texto limpio.
    Retorna: str
    """
    return texto.strip()

def procesar_monto_condiciones(texto):
    """
    Extrae un monto principal y el texto completo de las condiciones.
    Retorna: {"monto_num": float, "monto_texto": str, "condiciones": str}
    """
    monto_num = 0.0
    moneda = "soles"
    
    if "dólares" in texto.lower() or "dolares" in texto.lower() or "usd" in texto.lower():
        moneda = "dólares"

    # Extraer el primer número que aparezca
    match_monto = re.search(r'(\d+[\d\.,]*)', texto)
    if match_monto:
        monto_num = float(match_monto.group(1).replace(",", ""))

    monto_texto = f"{num2words(monto_num, lang='es').capitalize()} y 00/100 {moneda}"

    return {
        "monto_num": monto_num,
        "monto_texto": monto_texto,
        "condiciones": texto.strip() # Guardamos toda la descripción
    }

def procesar_lugar_fecha(texto):
    """
    Intenta extraer un lugar y una fecha de un string.
    Usa dateparser.search para encontrar la fecha y asume que el resto es el lugar.
    Retorna: {"lugar": str, "fecha": str, "fecha_larga": str}
    """
    settings = {'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'future'}
    
    # Buscar fechas en el texto
    dates = search_dates(texto, languages=['es'], settings=settings)
    
    fecha_str_encontrada = ""
    fecha_obj = None
    lugar = texto.strip()

    if dates:
        # Tomar la primera fecha encontrada
        fecha_str_encontrada, fecha_obj = dates[0]
        # Quitar la fecha del string para obtener el lugar
        lugar = lugar.replace(fecha_str_encontrada, "").strip()
        # Limpiar conectores ("en", "el", ",", "para")
        lugar = re.sub(r'^(en|el|para|del)\s*|[\.,;]$', '', lugar).strip()

    def format_fecha_larga(fecha_obj):
        if not fecha_obj: return ""
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            pass
        return fecha_obj.strftime("%d de %B de %Y")

    return {
        "lugar": lugar,
        "fecha": fecha_obj.strftime("%Y-%m-%d") if fecha_obj else None,
        "fecha_larga": format_fecha_larga(fecha_obj)
    }

def procesar_monto_simple(texto):
    """
    Extrae un único monto de un string.
    Retorna: {"monto_num": float, "monto_texto": str, "moneda": str}
    """
    monto_num = 0.0
    moneda = "soles"
    
    if "dólares" in texto.lower() or "dolares" in texto.lower() or "usd" in texto.lower():
        moneda = "dólares"

    match_monto = re.search(r'(\d+[\d\.,]*)', texto)
    if match_monto:
        monto_num = float(match_monto.group(1).replace(",", ""))

    monto_texto = f"{num2words(monto_num, lang='es').capitalize()} y 00/100 {moneda}"

    return {
        "monto_num": monto_num,
        "monto_texto": monto_texto,
        "moneda": moneda.capitalize()
    }

def procesar_interes(texto):
    """
    Determina si se generan intereses y extrae el porcentaje.
    Retorna: {"genera_interes": bool, "porcentaje": float}
    """
    texto_lower = texto.lower()
    genera_interes = True
    porcentaje = 0.0

    if texto_lower in DEF_NEGATIVES or "no genera" in texto_lower:
        genera_interes = False
    
    # Buscar porcentaje (ej: "5%", "5 por ciento")
    match_pct = re.search(r'(\d+[\d\.]*)', texto_lower)
    if match_pct:
        porcentaje = float(match_pct.group(1))

    return {"genera_interes": genera_interes, "porcentaje": porcentaje}

def procesar_arrendamiento(datos: dict) -> dict:
    """
    Procesa los datos recolectados del contrato de arrendamiento
    y los estructura según la plantilla Jinja2 'arrendamiento_base.html'.
    """
    def monto_a_letras(valor):
        try:
            valor = float(valor)
            return num2words(int(valor), lang="es").upper()
        except:
            return str(valor).upper()

    # --- ARRRENDADOR ---
    arrendador_texto = datos.get("arrendador", "")
    match_arr = re.search(r"(.+?),\s*DNI\s*(\d+).+domicilio\s*en\s*(.+)", arrendador_texto, re.I)
    arrendador = {
        "nombre": match_arr.group(1).strip() if match_arr else arrendador_texto,
        "dni": match_arr.group(2) if match_arr else "",
        "domicilio": match_arr.group(3).strip() if match_arr else "",
        "tratamiento": "EL ARRENDADOR"
    }

    # --- ARRENDATARIO ---
    arrendatario_texto = datos.get("arrendatario", "")
    match_ate = re.search(r"(.+?),\s*DNI\s*(\d+).+domicilio\s*en\s*(.+)", arrendatario_texto, re.I)
    arrendatario = {
        "nombre": match_ate.group(1).strip() if match_ate else arrendatario_texto,
        "dni": match_ate.group(2) if match_ate else "",
        "domicilio": match_ate.group(3).strip() if match_ate else "",
        "tratamiento": "EL ARRENDATARIO"
    }

    # --- INMUEBLE ---
    inm_texto = datos.get("inmueble", "")
    inmueble = {
        "direccion": re.search(r"(Av\.|Jr\.|Calle|Mz|Urbanización|[A-Za-z\s]+)\s+[^\d]*\d*", inm_texto).group(0).strip() if re.search(r"(Av\.|Jr\.|Calle|Mz|Urbanización|[A-Za-z\s]+)\s+[^\d]*\d*", inm_texto) else inm_texto,
        "distrito": re.search(r"distrito\s+([A-Za-záéíóúñ\s]+)", inm_texto, re.I).group(1).strip().title() if "distrito" in inm_texto.lower() else "",
        "provincia": re.search(r"provincia\s+([A-Za-záéíóúñ\s]+)", inm_texto, re.I).group(1).strip().title() if "provincia" in inm_texto.lower() else "",
        "departamento": re.search(r"departamento\s+([A-Za-záéíóúñ\s]+)", inm_texto, re.I).group(1).strip().title() if "departamento" in inm_texto.lower() else "",
        "partida_electronica": re.search(r"partida\s*(\d+)", inm_texto, re.I).group(1) if "partida" in inm_texto.lower() else "",
        "zona_registral": re.search(r"zona\s+registral\s+(.+)", inm_texto, re.I).group(1).strip().title() if "zona" in inm_texto.lower() else "",
        "destino": datos.get("inmueble_destino", "").lower()
    }

    # --- PLAZO ---
    plazo_texto = datos.get("plazo", "")
    match_plazo = re.search(
        r"(\d+)\s*años?.*?(\d{1,2}/\d{1,2}/\d{4}).*?(\d{1,2}/\d{1,2}/\d{4}).*?(\d+)\s*d[ií]as.*?(\d+)\s*mes",
        plazo_texto, re.I
    )
    plazo = {
        "anios_letras": num2words(int(match_plazo.group(1)), lang="es").upper() if match_plazo else "",
        "anios_numeros": match_plazo.group(1) if match_plazo else "",
        "fecha_inicio": match_plazo.group(2) if match_plazo else "",
        "fecha_fin": match_plazo.group(3) if match_plazo else "",
        "preaviso_dias_letras": num2words(int(match_plazo.group(4)), lang="es").upper() if match_plazo else "",
        "preaviso_dias_numeros": match_plazo.group(4) if match_plazo else "",
        "penalidad_meses_letras": num2words(int(match_plazo.group(5)), lang="es").upper() if match_plazo else ""
    }

    # --- RENTA ---
    renta = datos.get("renta", {})

    # --- PAGO ---
    pago_texto = datos.get("pago", "")
    pago = {
        "dia_limite_texto": re.search(r"(primer|segundo|tercer|cuarto|quinto|sexto|s[eé]ptimo)", pago_texto, re.I).group(1).upper() if re.search(r"(primer|segundo|tercer|cuarto|quinto|sexto|s[eé]ptimo)", pago_texto, re.I) else "QUINTO",
        "meses_incumplimiento_resolucion": re.search(r"(\d+)\s*mes", pago_texto, re.I).group(1) if "mes" in pago_texto.lower() else "2",
        "cuenta": {
            "tipo": re.search(r"(ahorros|corriente)", pago_texto, re.I).group(1).upper() if re.search(r"(ahorros|corriente)", pago_texto, re.I) else "CUENTA DE AHORROS",
            "numero": re.search(r"(\d[\d-]+)", pago_texto).group(1) if re.search(r"(\d[\d-]+)", pago_texto) else "",
            "banco": re.search(r"(BCP|BBVA|INTERBANK|SCOTIABANK|BANCO|FINANCIERA)\s*[A-Z]*", pago_texto, re.I).group(1).upper() if re.search(r"(BCP|BBVA|INTERBANK|SCOTIABANK|BANCO|FINANCIERA)", pago_texto, re.I) else ""
        }
    }

    # --- OTROS CAMPOS ---
    subarriendo_texto = datos.get("subarriendo", "").strip().lower()
    subarriendo = {"permitido": subarriendo_texto in ["si", "sí", "yes", "permitido"]}

    jurisdiccion = {"distrito_judicial": datos.get("jurisdiccion", "").title()}
    contrato = {}

    try:
        ciudad, fecha = [x.strip() for x in datos.get("contrato", "").split(",")]
        contrato = {"ciudad_firma": ciudad, "fecha_firma": fecha}
    except:
        contrato = {"ciudad_firma": "", "fecha_firma": ""}

    # --- Resultado final ---
    return {
        "arrendador": arrendador,
        "arrendatario": arrendatario,
        "inmueble": inmueble,
        "plazo": plazo,
        "renta": renta,
        "pago": pago,
        "subarriendo": subarriendo,
        "jurisdiccion": jurisdiccion,
        "contrato": contrato
    }

def procesar_renta(valor: str) -> dict:
    """
    Procesa la descripción de la renta escrita por el usuario y la convierte
    en una estructura compatible con la plantilla Jinja2 del contrato.

    Ejemplo de entrada:
        "Se van a pagar 400 soles mensuales y se dará una garantía de 200 soles"

    Ejemplo de salida:
        {
            "tramo1": {
                "monto_letras": "Cuatrocientos",
                "monto_numeros": 400,
                "periodo": "mensuales"
            },
            "moneda_simbolo": "S/",
            "garantia": {
                "monto_letras": "Doscientos",
                "monto_numeros": 200
            }
        }
    """
    if not valor:
        return {
            "tramo1": {
                "monto_letras": "No especificado",
                "monto_numeros": 0,
                "periodo": "mensual"
            },
            "moneda_simbolo": "S/",
            "garantia": {"monto_letras": "No especificada", "monto_numeros": 0}
        }

    texto = valor.lower()
    moneda = "S/"
    periodo = "mensuales" if "mensuales" in texto else "mensual"

    # 🔍 Buscar el primer monto de pago (renta)
    match_renta = re.search(r"(\d+(?:\.\d+)?)\s*(?:soles?)", texto)
    monto_renta = float(match_renta.group(1)) if match_renta else 0
    monto_letras = num2words(int(monto_renta), lang='es').capitalize() if monto_renta else "No especificado"

    # 🔍 Buscar posible monto de garantía
    match_garantia = re.search(r"garant[ií]a.*?(\d+(?:\.\d+)?)\s*(?:soles?)", texto)
    monto_garantia = float(match_garantia.group(1)) if match_garantia else 0
    monto_garantia_letras = num2words(int(monto_garantia), lang='es').capitalize() if monto_garantia else "No especificada"

    # Estructura final compatible con Jinja
    return {
        "tramo1": {
            "monto_letras": monto_letras,
            "monto_numeros": int(monto_renta),
            "periodo": periodo
        },
        "moneda_simbolo": moneda,
        "garantia": {
            "monto_letras": monto_garantia_letras,
            "monto_numeros": int(monto_garantia)
        }
    }

def procesar_pago(valor: str) -> dict:
    """
    Procesa el texto del pago para extraer información estructurada:
    - descripción libre del pago
    - día límite de pago
    - meses de incumplimiento antes de resolución
    - datos de cuenta bancaria (tipo, número, banco)
    """

    texto = valor.strip().lower()

    # --- 1. Día de pago ---
    match_dia = re.search(r'\b(\d{1,2})\b\s*(?:de\s*cada\s*mes|día|dia)?', texto)
    if match_dia:
        dia_num = int(match_dia.group(1))
        dia_texto = num2words(dia_num, lang='es').capitalize()
    else:
        dia_num = 5
        dia_texto = "Quinto"  # valor por defecto

    # --- 2. Meses de incumplimiento (ej: “2 meses de deuda”) ---
    match_meses = re.search(r'(\d+)\s*mes', texto)
    if match_meses:
        meses_num = int(match_meses.group(1))
        meses_texto = num2words(meses_num, lang='es').capitalize()
    else:
        meses_num = 2
        meses_texto = "Dos"

    # --- 3. Número de cuenta bancaria ---
    cuenta_match = re.search(r'(\d{8,20})', texto)
    cuenta_numero = cuenta_match.group(1) if cuenta_match else "No especificado"

    # --- 4. Tipo de cuenta ---
    if "ahorro" in texto:
        cuenta_tipo = "Cuenta de Ahorros"
    elif "corriente" in texto:
        cuenta_tipo = "Cuenta Corriente"
    else:
        cuenta_tipo = "Cuenta bancaria"

    # --- 5. Banco ---
    bancos = ["BCP", "BBVA", "Interbank", "Scotiabank", "BanBif", "Banco de la Nación"]
    cuenta_banco = next((b for b in bancos if b.lower() in texto), "No especificado")

    # --- 6. Construcción del resultado ---
    return {
        "descripcion": valor.strip(),
        "dia_limite_numero": dia_num,
        "dia_limite_texto": dia_texto,
        "meses_incumplimiento_resolucion": meses_texto,
        "cuenta": {
            "tipo": cuenta_tipo,
            "numero": cuenta_numero,
            "banco": cuenta_banco
        }
    }

def procesar_persona_con_dni_direccion(valor: str) -> dict:
    """
    Procesa un texto como:
      "Manuel Ernesto Leigh Ramirez 76854553 Calle Leoncio Prado 162"
    y devuelve:
    {
      "nombre": "Manuel Ernesto Leigh Ramirez",
      "dni": "76854553",
      "direccion": "Calle Leoncio Prado 162"
    }
    """
    texto = valor.strip()
    # Buscar DNI de 8 dígitos
    match = re.search(r'\b(\d{8})\b', texto)
    if match:
        dni = match.group(1)
    else:
        dni = ""
    # Dividir nombre vs lo demás
    partes = texto.split(dni) if dni else [texto]
    
    nombre = partes[0].strip() if partes else texto
    direccion = partes[1].strip() if len(partes) > 1 else ""
    
    return {
        "nombre": nombre,
        "dni": dni,
        "direccion": direccion
    }

def procesar_inmueble(texto: str):
    """
    Procesa una descripción del inmueble usando la API de Nominatim (OpenStreetMap).
    Ejemplo: "Calle Leoncio Prado 166, en Sullana, Sullana, Piura"
    Devuelve un diccionario estructurado con dirección, distrito, provincia y departamento.
    """
    texto_original = texto.strip()
    texto_busqueda = limpiar_direccion(texto_original)

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": texto_busqueda, "format": "json", "addressdetails": 1}
    headers = {"User-Agent": "ChatNotarial/1.0"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.json():
            data = resp.json()[0]["address"]
            return {
                "direccion": texto_busqueda,
                "distrito": data.get("city_district") or data.get("suburb") or data.get("town") or data.get("city") or "",
                "provincia": data.get("county") or data.get("state_district") or data.get("region") or "",
                "departamento": data.get("state") or "",
                "pais": data.get("country", "Perú"),
                "texto_busqueda": texto_busqueda
            }
        else:
            return _fallback_inmueble(texto_original)

    except Exception as e:
        print(f"⚠️ Error en procesar_inmueble (API Nominatim): {e}")
        return _fallback_inmueble(texto_original)

def _fallback_inmueble(texto: str):
    """
    Fallback local (sin API). Divide la cadena por comas.
    """
    partes = [p.strip().replace("en ", "").replace("En ", "") for p in texto.split(",") if p.strip()]
    resultado = {
        "direccion": "",
        "distrito": "",
        "provincia": "",
        "departamento": ""
    }

    if len(partes) >= 4:
        resultado["direccion"], resultado["distrito"], resultado["provincia"], resultado["departamento"] = partes[:4]
    elif len(partes) == 3:
        resultado["direccion"], resultado["distrito"], resultado["provincia"] = partes
    elif len(partes) == 2:
        resultado["direccion"], resultado["distrito"] = partes
    elif len(partes) == 1:
        resultado["direccion"] = partes[0]

    return resultado

def limpiar_direccion(texto_original: str) -> str:
    """
    Limpia una dirección del usuario para dejarla en formato corto.
    Ejemplo:
      Entrada: "Calle Leoncio Prado 166, en Sullana, Sullana, Piura"
      Salida:  "Calle Leoncio Prado 166 Sullana"
    """
    if not texto_original:
        return ""
    
    texto = re.sub(r"\b[Ee]n\b", "", texto_original)

    # 2️⃣ Reemplazar comas por espacios y limpiar espacios extra
    texto = texto.replace(",", " ")
    texto = re.sub(r"\s+", " ", texto).strip()

    # 3️⃣ Quitar palabras duplicadas (ej: "Sullana Sullana")
    partes = texto.split(" ")
    partes_unicas = []
    for palabra in partes:
        if palabra.lower() not in [p.lower() for p in partes_unicas]:
            partes_unicas.append(palabra)
    texto = " ".join(partes_unicas)
    partes = texto.split()
    if len(partes) >= 4:
        ultimas = partes[-3:]
        if all(re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$", p) for p in ultimas):
            texto = " ".join(partes[:-2])

    return texto.strip()

def procesar_plazo(valor: str) -> dict:
    """
    Procesa expresiones como:
      - "Desde el 30 de Octubre de 2025 por 6 meses"
      - "Del 1 de enero al 30 de junio de 2025"
    """
    texto = valor.strip()
    fecha_inicio, fecha_fin = "", ""
    meses_duracion = 0
    anios_duracion = 0

    # --- Diccionario de meses en español a inglés ---
    meses_es = {
        "enero": "January", "febrero": "February", "marzo": "March", "abril": "April",
        "mayo": "May", "junio": "June", "julio": "July", "agosto": "August",
        "septiembre": "September", "setiembre": "September", "octubre": "October",
        "noviembre": "November", "diciembre": "December"
    }

    def traducir_mes(fecha_texto: str):
        for esp, eng in meses_es.items():
            fecha_texto = re.sub(rf"\b{esp}\b", eng, fecha_texto, flags=re.IGNORECASE)
        return fecha_texto

    # --- Caso 1: "Del ... al ..." ---
    match_rango = re.search(r"(?i)del\s+(.*?)\s+al\s+(.*)", texto)
    if match_rango:
        fecha_inicio = match_rango.group(1).strip()
        fecha_fin = match_rango.group(2).strip()

    # --- Caso 2: "Desde el ... por X meses/años" ---
    else:
        match_desde = re.search(r"(?i)desde\s+el\s+(.*?)\s+por\s+(\d+)\s*(mes(?:es)?|año(?:s)?)", texto)
        if match_desde:
            fecha_inicio = match_desde.group(1).strip()
            cantidad = int(match_desde.group(2))
            unidad = match_desde.group(3).lower()
            if "año" in unidad:
                anios_duracion = cantidad
            else:
                meses_duracion = cantidad

            # Calcular fecha fin con meses traducidos
            try:
                fecha_inicio_en = traducir_mes(fecha_inicio)
                fecha_inicio_dt = parser.parse(fecha_inicio_en, dayfirst=True)
                if anios_duracion:
                    fecha_fin_dt = fecha_inicio_dt.replace(year=fecha_inicio_dt.year + anios_duracion)
                else:
                    fecha_fin_dt = fecha_inicio_dt + timedelta(days=meses_duracion * 30)
                fecha_fin = fecha_fin_dt.strftime("%d de %B de %Y").capitalize()
            except Exception as e:
                print(f"Error calculando fecha fin: {e}")

    # --- Valores por defecto ---
    preaviso_dias = 30
    penalidad_meses = 2

    return {
        "fecha_inicio": fecha_inicio or "No especificada",
        "fecha_fin": fecha_fin or "No especificada",
        "anios_numeros": anios_duracion,
        "anios_letras": num2words(anios_duracion, lang="es").capitalize() if anios_duracion else "Cero",
        "meses_numeros": meses_duracion,
        "meses_letras": num2words(meses_duracion, lang="es").capitalize() if meses_duracion else "Cero",
        "preaviso_dias_numeros": preaviso_dias,
        "preaviso_dias_letras": num2words(preaviso_dias, lang="es").capitalize(),
        "penalidad_meses_letras": num2words(penalidad_meses, lang="es").capitalize()
    }

# --- 2. El Registro de Procesadores ---

PROCESSOR_REGISTRY = {
    # Contratos generales
    "mutuo": procesar_monto_simple,
    "reconocimiento_deuda": procesar_monto_simple,
    "arrendamiento": procesar_arrendamiento,

    # Tipos de dato usados en varios contratos
    "persona_dni": procesar_persona_dni,
    "persona_empresa": procesar_persona_empresa,
    "direccion_descripcion": procesar_direccion_descripcion,
    "objeto_descripcion": procesar_objeto_descripcion,
    "texto_simple": procesar_texto_simple,
    "lugar_fecha": procesar_lugar_fecha,
    "interes": procesar_interes,

    # Datos específicos de arrendamiento
    "rango_fecha": procesar_rango_fecha,
    "monto_renta_garantia": procesar_monto_renta_garantia,
    "renta": procesar_renta,
    "pago": procesar_pago,
    "arrendador": procesar_persona_con_dni_direccion,
    "arrendatario": procesar_persona_con_dni_direccion,
    "inmueble": procesar_inmueble,
    "plazo": procesar_plazo,
    
    # Datos de prestación de servicios
    "monto_condiciones": procesar_monto_condiciones,

    # Mutuo o simples
    "monto_simple": procesar_monto_simple,
}
