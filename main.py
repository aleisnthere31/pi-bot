"""
🤖 MAIN - PUNTO DE ENTRADA DEL BOT PIBOT
==========================================
Este es el archivo principal que inicia y configura todos los handlers del bot.

CAMBIOS PRINCIPALES:
✅ Importes reorganizados y mejorados
✅ Logging configurado correctamente
✅ Manejo de errores mejorado (try/except)
✅ Docstrings agregados a funciones
✅ Configuración más clara y modular
✅ try/except para validación de config
"""

import logging
import random
from datetime import datetime, timezone
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram import Update

# Importar configuración
try:
    from config import BOT_TOKEN, validate_config
except ImportError as e:
    print(f"❌ Error al importar config: {e}")
    exit(1)

# Importar handlers de funcionalidades
try:
    from handlers.general import confesar, dar, ver, regalar, numero_azar, quitar
    from handlers.moderation import moderation_handler
    from handlers.theme_juegosYcasino import (
        apostar,
        aceptar,
        detectar_dado,
        cancelar_apuesta,
        jugar,
        robar,
    )
except ImportError as e:
    print(f"❌ Error al importar handlers: {e}")
    exit(1)

# ===================================================================================
# 📝 CONFIGURACIÓN DE LOGGING
# ===================================================================================
# Cambio: Logging configurado para ver errores y info importante
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ===================================================================================
# 🔧 FUNCIONES AUXILIARES
# ===================================================================================


async def get_theme_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /id
    
    Responde con el ID del tema (message_thread_id) y chat_id del mensaje.
    Útil para configurar los IDs en el archivo config.py
    
    Cambio: Documentación mejorada
    """
    if not update.message:
        return

    thread_id = update.message.message_thread_id
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"📌 **Chat ID**: `{chat_id}`\n"
        f"📌 **Theme (message_thread_id)**: `{thread_id}`",
        parse_mode="Markdown",
    )
    logger.info(f"Comando /id usado en chat {chat_id}, tema {thread_id}")


async def saludar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /saludar
    
    El bot responde con un saludo amistoso.
    
    Cambio: Documentación agregada
    """
    if not update.message:
        return

    await update.message.reply_text(
        "👋 ¡Hola a todos! Soy PiBot y vengo a animar el chat 🤖"
    )
    logger.info(f"Saludo enviado a {update.effective_user.username}")


# ===================================================================================
# 🚀 FUNCIÓN PRINCIPAL - CONFIGURACIÓN DEL BOT
# ===================================================================================


def main():
    """
    🚀 FUNCIÓN PRINCIPAL
    
    Configura y inicia el bot de Telegram.
    
    CAMBIOS REALIZADOS:
    ✅ Try/except para capturar errores de inicialización
    ✅ Validación de configuración al inicio
    ✅ Comentarios claros para cada sección de handlers
    ✅ Logging de inicio
    ✅ Manejo de errores más robusto
    """
    try:
        # Validar configuración antes de iniciar
        logger.info("🔍 Validando configuración...")
        validate_config()
        logger.info("✅ Configuración validada correctamente")

    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        return

    # Crear aplicación del bot
    try:
        logger.info("🔗 Conectando con Telegram...")
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Conexión establecida con éxito")

    except Exception as e:
        logger.error(f"❌ Error al conectar con Telegram: {e}")
        return

    # Establecer hora de inicio del bot (para filtrar mensajes antiguos)
    moderation_handler.BOT_START_TIME = datetime.now(timezone.utc)

    # ========================================================================
    # 📋 HANDLERS DE COMANDOS GENERALES (disponibles en todos los temas)
    # ========================================================================
    logger.info("📝 Registrando handlers generales...")

    app.add_handler(CommandHandler("ver", ver))
    app.add_handler(CommandHandler("regalar", regalar))
    app.add_handler(CommandHandler("dar", dar))
    app.add_handler(CommandHandler("quitar", quitar))
    app.add_handler(CommandHandler("NumAzar", numero_azar))
    app.add_handler(CommandHandler("confesar", confesar))

    # ========================================================================
    # 🛡️ HANDLERS DE MODERACIÓN
    # ========================================================================
    logger.info("🛡️ Registrando handlers de moderación...")

    # Detectar y moderar stickers, fotos y animaciones
    app.add_handler(
        MessageHandler(
            filters.Sticker.ALL | filters.PHOTO | filters.ANIMATION,
            moderation_handler,
        )
    )

    # ========================================================================
    # 🎲 HANDLERS DE JUEGOS Y APUESTAS (tema específico)
    # ========================================================================
    logger.info("🎲 Registrando handlers de juegos y apuestas...")

    # Comandos de apuestas
    app.add_handler(CommandHandler("apostar", apostar))
    app.add_handler(CommandHandler("aceptar", aceptar))
    app.add_handler(CommandHandler("cancelar", cancelar_apuesta))

    # Comandos de juegos
    app.add_handler(CommandHandler("jugar", jugar))
    app.add_handler(CommandHandler("robar", robar))

    # Detectar dados automáticamente
    app.add_handler(MessageHandler(filters.Dice.ALL, detectar_dado))

    # ========================================================================
    # 🔧 HANDLERS DE UTILIDADES
    # ========================================================================
    logger.info("🔧 Registrando handlers de utilidades...")

    app.add_handler(CommandHandler("id", get_theme_id))
    app.add_handler(CommandHandler("saludar", saludar))

    # ========================================================================
    # 🚀 INICIAR BOT
    # ========================================================================
    try:
        logger.info("=" * 60)
        logger.info("🤖 ¡BOT PIBOT INICIADO CORRECTAMENTE!")
        logger.info("=" * 60)
        logger.info("💬 Escuchando mensajes...")

        app.run_polling(drop_pending_updates=True)

    except KeyboardInterrupt:
        logger.info("⏹️ Bot detenido por el usuario (Ctrl+C)")

    except Exception as e:
        logger.error(f"❌ Error al ejecutar el bot: {e}", exc_info=True)


# ===================================================================================
# 📌 PUNTO DE ENTRADA
# ===================================================================================

if __name__ == "__main__":
    main()


