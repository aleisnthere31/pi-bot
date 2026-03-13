# handlers/moderation.py
"""
🛡️ SISTEMA DE MODERACIÓN - CONTROL DE SPAM DE MEDIAS
====================================================
Detecta y castiga usuarios que envían demasiados stickers, fotos o GIFs en poco tiempo.

CARACTERÍSTICAS:
- Límite configurable de medias por ventana de tiempo
- Baneo temporal automático
- Whitelist de temas excluidos
- Ignora mensajes anteriores al arranque del bot

CAMBIOS PRINCIPALES:
✅ Docstrings detallados
✅ Mejor manejo de tipos de datos
✅ Logging mejorado
✅ Validaciones de None
✅ Comentarios explicativos en todo el código
"""

import time
import logging
from datetime import timezone
from telegram import Update
from telegram.ext import ContextTypes

try:
    from config import EXCLUDED_CHATS, EXCLUDED_THREAD_PAIRS, MAX_MEDIA, BAN_TIME, WINDOW_TIME
except ImportError:
    # Fallback para ejecucion como paquete
    from ..config import EXCLUDED_CHATS, EXCLUDED_THREAD_PAIRS, MAX_MEDIA, BAN_TIME, WINDOW_TIME

# ===================================================================================
# 📝 LOGGING
# ===================================================================================
logger = logging.getLogger(__name__)

# ===================================================================================
# 💾 BASE DE DATOS EN MEMORIA
# ===================================================================================
# Estructura: {user_id: {"count": int, "last_time": float, "messages": [msg_ids]}}
media_count = {}

# Estructura: {user_id: tiempo_expiracion}
blacklist = {}

# Hora de inicio del bot (se establece desde main.py)
BOT_START_TIME = None


# ===================================================================================
# 🔧 FUNCIONES AUXILIARES
# ===================================================================================


def is_excluded(chat_id: int, thread_id: int | None) -> bool:
    """
    Verifica si un chat o tema está excluido de moderación.
    
    Cambio: Agregada documentación y mejor estructura lógica
    
    Args:
        chat_id (int): ID del chat/grupo
        thread_id (int | None): ID del tema (topic)
        
    Returns:
        bool: True si está excluido, False si se debe moderatear
    """
    # 1) Excluir si el chat entero está en la lista negra
    if chat_id in EXCLUDED_CHATS:
        logger.debug(f"Chat {chat_id} está completamente excluido")
        return True

    # 2) Excluir por par específico (chat_id, thread_id)
    if thread_id is not None and (chat_id, thread_id) in EXCLUDED_THREAD_PAIRS:
        logger.debug(f"Pair ({chat_id}, {thread_id}) está excluido")
        return True

    # 3) Excluir si el thread_id está directamente en EXCLUDED_CHATS
    if thread_id is not None and thread_id in EXCLUDED_CHATS:
        logger.debug(f"Thread {thread_id} está excluido")
        return True

    return False


def _cleanup_blacklist(now: float):
    """
    🔧 FUNCIÓN AUXILIAR (NUEVA)
    
    Limpia usuarios cuyo baneo temporal ha expirado.
    
    Cambio: Función agregada para mejor mantenimiento de memoria
    
    Args:
        now (float): Timestamp actual
    """
    expired_users = [user_id for user_id, expiration in blacklist.items() if now >= expiration]

    for user_id in expired_users:
        del blacklist[user_id]
        logger.info(f"Usuario {user_id} removido de blacklist (baneo expirado)")


# ===================================================================================
# 🚨 HANDLER PRINCIPAL DE MODERACIÓN
# ===================================================================================


async def moderation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 HANDLER PRINCIPAL
    
    Procesa mensajes con medias (stickers, fotos, GIFs) y aplica moderación.
    
    CAMBIOS REALIZADOS:
    ✅ Mejor estructura y documentación
    ✅ Validaciones mejoradas de None/tipos
    ✅ Logging detallado en cada paso
    ✅ Limpieza periódica de blacklist
    ✅ Comentarios explicativos
    """
    if not update.message:
        logger.debug("Mensaje sin contenido recibido, ignorando")
        return

    # ===================================================================================
    # 📋 OBTENER DATOS BÁSICOS
    # ===================================================================================
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user:
        logger.debug("Chat o usuario nulo, ignorando mensaje")
        return

    chat_id = chat.id
    thread_id = getattr(update.message, "message_thread_id", None)
    user_id = user.id
    now = time.time()

    logger.info(
        f"📨 Mensaje de media recibido: chat_id={chat_id}, thread_id={thread_id}, user_id={user_id}"
    )

    # ===================================================================================
    # ⏰ FILTRO: IGNORAR MENSAJES ANTERIORES AL ARRANQUE DEL BOT
    # ===================================================================================
    # Cambio: Mejor manejo de validación de fecha
    if BOT_START_TIME:
        msg_date = update.message.date

        try:
            # Normalizar a UTC aware si no lo es
            msg_date = msg_date.astimezone(timezone.utc)
        except Exception:
            pass

        if msg_date < BOT_START_TIME:
            logger.debug(f"Mensaje anterior al arranque del bot, ignorando")
            return

    # ===================================================================================
    # 🚫 FILTRO: EXCLUIDOS
    # ===================================================================================
    # Cambio: Se valida ANTES de registrar contadores (ahorra recursos)
    if is_excluded(chat_id, thread_id):
        logger.debug(f"Chat/Tema excluido de moderación (chat_id={chat_id}, thread_id={thread_id})")
        return

    # ===================================================================================
    # 🔪 ACCIÓN 1: VERIFICAR SI USUARIO ESTÁ EN BLACKLIST
    # ===================================================================================
    # Cambio: Limpieza periódica de blacklist
    _cleanup_blacklist(now)

    if user_id in blacklist:
        if now < blacklist[user_id]:
            # Usuario sigue baneado
            try:
                await update.message.delete()
                logger.warning(f"⛔ Usuario {user_id} en blacklist: mensaje eliminado")
            except Exception as e:
                logger.warning(f"Error borrando mensaje de usuario en blacklist: {e}")
            return
        else:
            # El baneo expiró, remover de blacklist
            del blacklist[user_id]
            logger.info(f"✅ Usuario {user_id} removido de blacklist automáticamente")

    # ===================================================================================
    # 📊 ACCIÓN 2: REGISTRAR MEDIA Y VERIFICAR LÍMITE
    # ===================================================================================
    if user_id not in media_count:
        media_count[user_id] = {"count": 0, "last_time": now, "messages": []}

    # Reiniciar contador si pasó más tiempo que WINDOW_TIME
    if now - media_count[user_id]["last_time"] > WINDOW_TIME:
        logger.debug(
            f"Reiniciando contador para usuario {user_id} (pasaron {now - media_count[user_id]['last_time']}s)"
        )
        media_count[user_id] = {"count": 0, "last_time": now, "messages": []}

    # Incrementar contador
    media_count[user_id]["count"] += 1
    media_count[user_id]["last_time"] = now
    media_count[user_id]["messages"].append(update.message.message_id)

    logger.info(
        f"📊 Usuario {user_id}: {media_count[user_id]['count']}/{MAX_MEDIA} medias "
        f"en {WINDOW_TIME}s"
    )

    # ===================================================================================
    # 🚨 ACCIÓN 3: APLICAR SANCIONES SI SE EXCEDE LÍMITE
    # ===================================================================================
    if media_count[user_id]["count"] > MAX_MEDIA:
        logger.warning(f"⛔ Usuario {user_id} EXCEDIÓ límite de medias ({MAX_MEDIA})")

        # Borrar todos los mensajes registrados del usuario
        messages_to_delete = media_count[user_id]["messages"]
        logger.info(f"Eliminando {len(messages_to_delete)} mensajes del usuario {user_id}")

        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.warning(f"Error borrando mensaje {msg_id}: {e}")

        # Poner usuario en blacklist temporal
        expiration_time = now + BAN_TIME
        blacklist[user_id] = expiration_time
        media_count[user_id] = {"count": 0, "last_time": now, "messages": []}

        # Notificar a los moderadores
        ban_minutes = BAN_TIME // 60
        user_mention = f"@{user.username}" if user.username else user.first_name

        try:
            await context.bot.send_message(
                chat_id,
                f"⚠️ {user_mention} ha sido bloqueado por enviar demasiadas medias. "
                f"Podrá volver a enviar medias en {ban_minutes} minutos.",
            )
            logger.info(f"Notificación de ban enviada para usuario {user_id}")
        except Exception as e:
            logger.warning(f"Error enviando notificación de ban: {e}")
