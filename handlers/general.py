"""
💰 HANDLERS GENERALES - SISTEMA DE ECONOMÍA
=============================================
Contiene todos los comandos relacionados con el sistema de PiPesos.
Usa SQLite/PostgreSQL con SQLAlchemy (migración desde JSON)

CAMBIOS PRINCIPALES:
✅ Migración de JSON a base de datos (SQLite en dev, PostgreSQL en Heroku)
✅ Uso de modelo ORM de SQLAlchemy
✅ Mejor rendimiento y escalabilidad
✅ Transacciones ACID
✅ Mismo conjunto de comandos que antes
"""

import random
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal, get_usuario_o_crear, transferir_puntos, agregar_puntos, quitar_puntos

try:
    from config import CHAT_IDS
except ImportError:
    from ..config import CHAT_IDS

# ===================================================================================
# 📝 LOGGING
# ===================================================================================
logger = logging.getLogger(__name__)


# ===================================================================================
# 🔧 FUNCIONES AUXILIARES
# ===================================================================================

async def verificar_admin(id_usuario: int, update: Update) -> bool:
    """
    Verifica si un usuario es administrador del chat actual.
    
    Args:
        id_usuario (int): ID del usuario a verificar
        update (Update): Evento de Telegram
        
    Returns:
        bool: True si es admin, False si no
    """
    try:
        chat_id = update.effective_chat.id
        admins = await update.effective_chat.get_administrators()

        for admin in admins:
            if admin.user.id == id_usuario:
                logger.debug(f"Usuario {id_usuario} es admin en chat {chat_id}")
                return True

        logger.debug(f"Usuario {id_usuario} NO es admin en chat {chat_id}")
        return False

    except Exception as e:
        logger.error(f"Error verificando admin: {e}")
        return False


# ===================================================================================
# 💰 COMANDOS DE ECONOMÍA
# ===================================================================================

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /ver
    
    Muestra el saldo actual de PiPesos del usuario.
    Si no existe, lo registra automáticamente con saldo 0.
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    username = user.username or user.first_name

    try:
        db = SessionLocal()
        usuario = get_usuario_o_crear(db, user.id, username)
        saldo = usuario.saldo
        db.close()

        await update.message.reply_text(
            f"💰 **Tu saldo actual:**\n"
            f"`{saldo:,.0f} PiPesos`",
            parse_mode="Markdown"
        )

        logger.info(f"Usuario {username} ({user.id}) consultó saldo: {saldo}")

    except Exception as e:
        logger.error(f"Error en /ver: {e}")
        await update.message.reply_text("❌ Error al consultar saldo")


async def dar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /dar
    
    Transfiere PiPesos a otro usuario.
    Formato: `/dar <cantidad> @usuario`
    También funciona respondiendo a un mensaje.
    """
    if not update.message or not update.effective_user:
        return

    user_origen = update.effective_user
    username_origen = user_origen.username or user_origen.first_name

    # Parsear argumentos
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Uso: `/dar <cantidad> @usuario`",
            parse_mode="Markdown"
        )
        return

    try:
        cantidad = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ La cantidad debe ser un número válido")
        return

    if cantidad <= 0:
        await update.message.reply_text("❌ La cantidad debe ser mayor a 0")
        return

    # Buscar usuario destino
    user_destino = None
    if len(context.args) >= 2:
        # Intenta interpretar como mención
        username_destino = context.args[1].replace("@", "")
        # Nota: Sin acceso a la BD de nombres de usuario de Telegram, esto es limitado
        # Para un uso real, necesitarías guardar usernames en BD cuando interactúan
        await update.message.reply_text("❌ Por favor, responde a un mensaje del usuario al que quieres transferir")
        return
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        user_destino = update.message.reply_to_message.from_user

    if not user_destino:
        await update.message.reply_text("❌ Debes responder a un mensaje del usuario")
        return

    try:
        db = SessionLocal()
        
        # Transferir puntos
        exito = transferir_puntos(
            db, 
            user_origen.id, 
            user_destino.id, 
            cantidad, 
            f"Transferencia de {username_origen}"
        )

        if exito:
            await update.message.reply_text(
                f"✅ Transferencia exitosa\n"
                f"Enviaste `{cantidad:,.0f} PiPesos` a @{user_destino.username or user_destino.first_name}",
                parse_mode="Markdown"
            )
            logger.info(f"{username_origen} transfirió {cantidad} a {user_destino.username}")
        else:
            await update.message.reply_text(
                f"❌ No tienes suficientes PiPesos.\n"
                f"Necesitas: `{cantidad:,.0f}` - Tienes menos",
                parse_mode="Markdown"
            )

        db.close()

    except Exception as e:
        logger.error(f"Error en /dar: {e}")
        await update.message.reply_text("❌ Error al procesar la transferencia")


async def regalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /regalar
    
    Solo Admins - Regala PiPesos a un usuario.
    Formato: `/regalar <cantidad> @usuario`
    También funciona respondiendo a un mensaje.
    """
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    # Verificar permisos de admin
    is_admin = await verificar_admin(user_id, update)
    if not is_admin:
        await update.message.reply_text("❌ Este comando solo lo pueden usar administradores")
        return

    # Parsear argumentos
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Uso: `/regalar <cantidad> @usuario`",
            parse_mode="Markdown"
        )
        return

    try:
        cantidad = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ La cantidad debe ser un número válido")
        return

    if cantidad <= 0:
        await update.message.reply_text("❌ La cantidad debe ser mayor a 0")
        return

    # Buscar usuario destino
    user_destino = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        user_destino = update.message.reply_to_message.from_user
    elif len(context.args) >= 2:
        await update.message.reply_text("💡 Para regalos, responde al mensaje del usuario")
        return

    if not user_destino:
        await update.message.reply_text("❌ Debes responder a un mensaje del usuario")
        return

    try:
        db = SessionLocal()
        agregar_puntos(db, user_destino.id, cantidad, f"Regalado por admin {username}")           
        await update.message.reply_text(
            f"✅ Regalaste `{cantidad:,.0f} PiPesos` a @{user_destino.username or user_destino.first_name}",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {username} regaló {cantidad} a {user_destino.username}")
        db.close()

    except Exception as e:
        logger.error(f"Error en /regalar: {e}")
        await update.message.reply_text("❌ Error al procesar el regalo")


async def quitar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /quitar
    
    Solo Admin - Quita PiPesos a un usuario.
    Formato: `/quitar <cantidad> @usuario`
    También funciona respondiendo a un mensaje.
    """
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    # Verificar permisos de admin
    is_admin = await verificar_admin(user_id, update)
    if not is_admin:
        await update.message.reply_text("❌ Este comando solo lo pueden usar administradores")
        return

    # Parsear argumentos
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Uso: `/quitar <cantidad> @usuario`",
            parse_mode="Markdown"
        )
        return

    try:
        cantidad = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ La cantidad debe ser un número válido")
        return

    if cantidad <= 0:
        await update.message.reply_text("❌ La cantidad debe ser mayor a 0")
        return

    # Buscar usuario destino
    user_destino = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        user_destino = update.message.reply_to_message.from_user
    elif len(context.args) >= 2:
        await update.message.reply_text("💡 Para remover puntos, responde al mensaje del usuario")
        return

    if not user_destino:
        await update.message.reply_text("❌ Debes responder a un mensaje del usuario")
        return

    try:
        db = SessionLocal()
        quitar_puntos(db, user_destino.id, cantidad, f"Removido por admin {username}")

        await update.message.reply_text(
            f"✅ Quitaste `{cantidad:,.0f} PiPesos` a @{user_destino.username or user_destino.first_name}",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {username} quitó {cantidad} a {user_destino.username}")
        db.close()

    except Exception as e:
        logger.error(f"Error en /quitar: {e}")
        await update.message.reply_text("❌ Error al procesar la acción")


async def numero_azar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /NumAzar
    
    Genera un número aleatorio entre dos valores.
    Formato: `/NumAzar <min> <max>`
    """
    if not update.message:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Uso: `/NumAzar <min> <max>`",
            parse_mode="Markdown"
        )
        return

    try:
        min_val = int(context.args[0])
        max_val = int(context.args[1])

        if min_val >= max_val:
            await update.message.reply_text(
                "❌ El valor mínimo debe ser menor al máximo"
            )
            return

        numero = random.randint(min_val, max_val)

        await update.message.reply_text(
            f"🎲 **Número aleatorio entre {min_val} y {max_val}:**\n\n"
            f"`{numero}`",
            parse_mode="Markdown"
        )
        logger.info(f"Número aleatorio generado: {numero} ({min_val}-{max_val})")

    except ValueError:
        await update.message.reply_text("❌ Los valores deben ser números enteros")


async def confesar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /confesar
    
    Envía una confesión anónima al grupo de confesiones.
    Solo funciona en privado con el bot.
    Formato: `/confesar <tu confesión>`
    """
    if not update.message:
        return

    # Verificar que sea privado
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "❌ Este comando solo funciona en privado con el bot.\n"
            "Envíame un mensaje privado a través de mi perfil."
        )
        return

    # Obtener confesión
    if not context.args:
        await update.message.reply_text(
            "❌ Debes escribir tu confesión.\n"
            "Formato: `/confesar Tu confesión aquí`",
            parse_mode="Markdown"
        )
        return

    confesion = " ".join(context.args)

    try:
        # Enviar al grupo de confesiones
        grupo_id = CHAT_IDS.get("confesiones", -1002894647510)
        topic_id = CHAT_IDS.get("confesiones_topic", 7781)

        msg = f"🤫 **Confesión anónima:**\n\n_{confesion}_"

        await context.bot.send_message(
            chat_id=grupo_id,
            message_thread_id=topic_id,
            text=msg,
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "✅ Tu confesión fue enviada de forma anónima",
            parse_mode="Markdown"
        )
        logger.info(f"Confesión anónima enviada: {confesion[:50]}...")

    except Exception as e:
        logger.error(f"Error enviando confesión: {e}")
        await update.message.reply_text(
            "❌ Error al enviar la confesión. Intenta más tarde."
        )
