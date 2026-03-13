"""
CONFIGURACION GLOBAL DEL BOT PIBOT
====================================
Este modulo contiene todas las configuraciones del bot incluyendo:
- Token de autenticacion
- IDs de temas y chats
- Parametros de moderacion
- Chats excluidos de ciertas funciones

NOTA IMPORTANTE: Usa variables de entorno (.env) para el BOT_TOKEN
"""

import os
from dotenv import load_dotenv

# CARGA DE VARIABLES DE ENTORNO
load_dotenv()

# ===================================================================================
# TOKENS Y AUTENTICACION
# ===================================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_token_here")
# ADVERTENCIA: Nunca commitear el token a GitHub. Usar .env en produccion

# ===================================================================================
# CONFIGURACION DE MODERACION
# ===================================================================================
# Maximo numero de medias (stickers, fotos, GIFs) permitidas en WINDOW_TIME segundos
MAX_MEDIA = int(os.getenv("MAX_MEDIA", 4))

# Ventana de tiempo en segundos para contar medias
WINDOW_TIME = int(os.getenv("WINDOW_TIME", 15))

# Duracion del baneo temporal en segundos (600 = 10 minutos)
BAN_TIME = int(os.getenv("BAN_TIME", 600))

# ===================================================================================
# IDS DE TEMAS Y CHATS
# ===================================================================================
# Mapeo de nombres simbolicos a IDs reales de temas (topics)
# Los IDs se obtienen usando /id dentro de cada tema
CHAT_IDS = {
    # Temas generales
    "theme_presentaciones": int(os.getenv("THEME_PRESENTACIONES", 3)),
    "theme_Anuncios": int(os.getenv("THEME_ANUNCIOS", 125337)),
    "theme_biblioteca": int(os.getenv("THEME_BIBLIOTECA", 28816)),
    "theme_escuela": int(os.getenv("THEME_ESCUELA", 28809)),
    
    # Tema de juegos y apuestas (IMPORTANTE: restricciones especiales)
    "theme_juegosYcasino": int(os.getenv("THEME_JUEGOS_CASINO", 6791)),
    
    # Otros temas
    "theme_relatos": int(os.getenv("THEME_RELATOS", 50746)),
    "theme_NSFW": int(os.getenv("THEME_NSFW", 834)),
    "theme_Exhibicionismo": int(os.getenv("THEME_EXHIBICIONISMO", 4)),
    "theme_busquedas": int(os.getenv("THEME_BUSQUEDAS", 2)),
    "theme_postulaciones": int(os.getenv("THEME_POSTULACIONES", 202530)),
    "theme_multimedia": int(os.getenv("THEME_MULTIMEDIA", 50054)),
    
    # Grupo y tema de confesiones (anonimas)
    "confesiones": int(os.getenv("CONFESIONES_GROUP_ID", -1002894647510)),
    "confesiones_topic": int(os.getenv("CONFESIONES_TOPIC_ID", 7781))
}

# ===================================================================================
# CHATS Y TEMAS EXCLUIDOS
# ===================================================================================
# Estos temas NO participaran en la moderacion de medias
# (Contiene temas sensibles donde pueden compartir contenido sin restricciones)
EXCLUDED_CHATS = {
    CHAT_IDS["theme_NSFW"],           # Contenido adulto
    CHAT_IDS["theme_Exhibicionismo"],  # Contenido de naturaleza explicita
    CHAT_IDS["theme_multimedia"]       # Zona para compartir medias
}

# Pares especificos (chat_id, thread_id) que estan excluidos de moderacion
# Se puede agregar aqui para excepciones puntuales
EXCLUDED_THREAD_PAIRS = set()

# ===================================================================================
# VALIDACION DE CONFIGURACION
# ===================================================================================
def validate_config():
    """
    Valida que todas las configuraciones necesarias sean validas.
    
    Cambios: Se agrego esta funcion para validacion temprana de errores.
    """
    if BOT_TOKEN == "your_token_here":
        raise ValueError(
            "ERROR: BOT_TOKEN no configurado. "
            "Por favor, copia .env.example a .env y agrega tu token."
        )
    
    if len(str(BOT_TOKEN).split(":")) != 2:
        raise ValueError(
            "ERROR: BOT_TOKEN tiene formato invalido. "
            "Debe tener el formato: ID:TOKEN"
        )
    
    if MAX_MEDIA <= 0:
        raise ValueError("ERROR: MAX_MEDIA debe ser mayor a 0")
    
    if WINDOW_TIME <= 0:
        raise ValueError("ERROR: WINDOW_TIME debe ser mayor a 0")
    
    if BAN_TIME <= 0:
        raise ValueError("ERROR: BAN_TIME debe ser mayor a 0")

# Ejecutar validacion al importar el modulo
try:
    validate_config()
except ValueError as e:
    print(f"ERROR: {e}")
    exit(1)