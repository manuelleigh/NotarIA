# services/nlp_utils.py
import spacy

# Nombre del modelo que usas en todo el proyecto
SPACY_MODEL = "es_core_news_md"

# Variable global para mantener el modelo cargado
_nlp = None

def get_nlp():
    """
    Devuelve una instancia única del modelo spaCy en español.
    Si aún no se ha cargado, la carga y la reutiliza en todo el proyecto.
    """
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL)
            print(f"Modelo spaCy '{SPACY_MODEL}' cargado correctamente.")
        except OSError:
            print(f"Error: Modelo '{SPACY_MODEL}' no encontrado.")
            print("Por favor, instala el modelo con:")
            print(f"    python -m spacy download {SPACY_MODEL}")
            _nlp = None
    return _nlp
