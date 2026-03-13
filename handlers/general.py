"""
💰 HANDLERS GENERALES - SISTEMA DE ECONOMÍA
=============================================
Contiene todos los comandos relacionados con el sistema de PiPesos:
- Ver saldo
- Transferencias entre usuarios
- Reparto de puntos (admins)
- Confesiones anónimas
- Utilidades (número aleatorio)

CAMBIOS PRINCIPALES:
✅ Docstrings detallados en todas las funciones
✅ Mejor manejo de errores
✅ Función auxiliar _buscar_usuario() para evitar duplicación de código
✅ Logging agregado para debugging
✅ Validaciones mejoradas
✅ Comentarios claros en todo el código
"""

import json
import os
import random
import logging
from types import SimpleNamespace
from telegram import Update
from telegram.ext import ContextTypes

try:
    from config import CHAT_IDS
except ImportError:
    # Fallback para ejecución como paquete
    from ..config import CHAT_IDS

# ===================================================================================
# 📝 LOGGING
# ===================================================================================
logger = logging.getLogger(__name__)

# ===================================================================================
# 📁 CONFIGURACIÓN DE BASE DE DATOS
# ===================================================================================
RUTA_USUARIOS = "pipesos.json"


# ===================================================================================
# 🔧 FUNCIONES AUXILIARES
# ===================================================================================


def cargar_usuarios() -> dict:
    """
    Carga el archivo JSON de usuarios y devuelve un diccionario plano.
    
    Formato esperado: {"usuarios": {"ID": {"username": "...", "saldo": X}}}
    
    Cambio: Agregada validación y logging mejorado
    
    Returns:
        dict: {"user_id": {"username": "...", "saldo": 0}, ...}
    """
    if not os.path.exists(RUTA_USUARIOS):
        logger.debug(f"Archivo {RUTA_USUARIOS} no existe, retornando dict vacío")
        return {}

    try:
        with open(RUTA_USUARIOS, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Si viene envuelto {"usuarios": {...}} -> devolver el inner dict
        if isinstance(data, dict) and "usuarios" in data:
            if isinstance(data["usuarios"], dict):
                return data["usuarios"]

        # Si ya está en plano {id: {...}} -> devolverlo
        if isinstance(data, dict):
            return data

        return {}

    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error al cargar usuarios: {e}")
        return {}


def guardar_usuarios(usuarios: dict) -> bool:
    """
    Guarda el diccionario de usuarios en JSON.
    
    Cambio: Usa archivo temporal para evitar corrupción. Retorna bool de éxito.
    
    Args:
        usuarios (dict): Diccionario de usuarios a guardar
        
    Returns:
        bool: True si se guardó exitosamente, False si hubo error
    """
    try:
        payload = {"usuarios": usuarios}
        tmp = RUTA_USUARIOS + ".tmp"

        # Guardar en archivo temporal primero (seguridad)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        # Reemplazar archivo original
        os.replace(tmp, RUTA_USUARIOS)
        logger.debug(f"Usuarios guardados exitosamente")
        return True

    except Exception as e:
        logger.error(f"Error al guardar usuarios: {e}")
        return False


def existe_usuario(id_usuario: int) -> int | bool:
    """
    Verifica si un usuario existe y retorna su saldo.
    
    Args:
        id_usuario (int): ID de Telegram del usuario
        
    Returns:
        int | bool: El saldo si existe, False si no existe
    """
    usuarios = cargar_usuarios()
    id_str = str(id_usuario)

    if id_str not in usuarios:
        return False

    return usuarios[id_str]["saldo"]


def agregar_usuario(id_usuario: int, cantidad: int, username: str) -> bool:
    """
    Agrega un usuario nuevo al sistema con saldo inicial.
    
    Cambio: Ahora retorna bool de éxito. Agregado logging.
    
    Args:
        id_usuario (int): ID de Telegram
        cantidad (int): Saldo inicial en PiPesos
        username (str): Username del usuario
        
    Returns:
        bool: True si se agregó exitosamente
    """
    usuarios = cargar_usuarios()
    id_str = str(id_usuario)

    usuarios[id_str] = {"username": username, "saldo": cantidad}

    success = guardar_usuarios(usuarios)
    logger.info(f"Usuario {username} ({id_usuario}) agregado con saldo {cantidad}")
    return success


def dar_puntos(user_id: int, username: str, cantidad: int) -> bool:
    """
    Suma puntos a un usuario.
    
    Cambio: Mejor manejo de errores. Retorna bool. Agregado logging.
    
    Args:
        user_id (int): ID del usuario
        username (str): Username del usuario
        cantidad (int): Cantidad a sumar
        
    Returns:
        bool: True si se ejecutó correctamente
    """
    usuarios = cargar_usuarios()
    id_str = str(user_id)

    if id_str not in usuarios:
        usuarios[id_str] = {"username": username, "saldo": 0}

    usuarios[id_str]["saldo"] += cantidad
    logger.info(f"{username} gana {cantidad} PiPesos (Total: {usuarios[id_str]['saldo']})")
    return guardar_usuarios(usuarios)


def quitar_puntos(user_id: int, username: str, cantidad: int) -> bool:
    """
    Resta puntos a un usuario (nunca por debajo de 0).
    
    Cambio: Mejor manejo de errores. Retorna bool. Agregado logging.
    
    Args:
        user_id (int): ID del usuario
        username (str): Username del usuario
        cantidad (int): Cantidad a restar
        
    Returns:
        bool: True si se ejecutó correctamente
    """
    usuarios = cargar_usuarios()
    id_str = str(user_id)

    if id_str not in usuarios:
        usuarios[id_str] = {"username": username, "saldo": 0}

    saldo_anterior = usuarios[id_str]["saldo"]
    usuarios[id_str]["saldo"] = max(0, usuarios[id_str]["saldo"] - cantidad)

    logger.info(
        f"{username} pierde {cantidad} PiPesos ({saldo_anterior} -> {usuarios[id_str]['saldo']})"
    )
    return guardar_usuarios(usuarios)


async def verificar_admin(id_usuario: int, update: Update) -> bool:
    """
    Verifica si un usuario es administrador del chat actual.
    
    Cambio: Agregado logging
    
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


def _buscar_usuario(username: str) -> SimpleNamespace | None:
    """
    🔧 FUNCIÓN AUXILIAR (NUEVA)
    
    Busca un usuario en la base de datos por username.
    
    Cambio: Función creada para evitar duplicación de código en /dar, /regalar, etc.
    
    Args:
        username (str): Username a buscar (sin @)
        
    Returns:
        SimpleNamespace | None: Objeto con id y username, o None si no existe
    """
    usuarios = cargar_usuarios()
    username_clean = username.lstrip("@").lower()

    for uid, info in usuarios.items():
        if (info.get("username") or "").lower() == username_clean:
            return SimpleNamespace(id=int(uid), username=info.get("username"))

    return None


# ===================================================================================
# 📋 COMANDOS
# ===================================================================================


async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /ver
    
    Muestra el saldo actual del usuario en PiPesos.
    Si no existe, lo registra con saldo 0.
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    username = user.username or user.first_name
    saldo = existe_usuario(user.id)

    if saldo is False:
        # Registrar usuario nuevo con saldo 0
        agregar_usuario(user.id, 0, username)
        saldo = 0
        logger.info(f"Nuevo usuario registrado: {username} ({user.id})")

    await update.message.reply_text(f"💰 {username}, tienes {saldo} PiPesos.")


async def regalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /regalar <cantidad> [@usuario]
    
    Solo admins. Regala PiPesos a un usuario.
    
    Cambio: Uso de función auxiliar _buscar_usuario()
    """
    if not update.message or not update.effective_user:
        return

    sender = update.effective_user

    # 🔐 Verificar admin
    if not await verificar_admin(sender.id, update):
        await update.message.reply_text("⚠️ Solo los administradores pueden usar este comando.")
        logger.info(f"{sender.username} intentó /regalar sin ser admin")
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /regalar <cantidad> [@usuario] o respondiendo a un mensaje."
        )
        return

    try:
        cantidad = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ La cantidad debe ser un número.")
        return

    if cantidad <= 0:
        await update.message.reply_text("⚠️ La cantidad debe ser mayor a 0.")
        return

    receptor = None

    if len(context.args) >= 2:
        # Buscar por mención
        receptor = _buscar_usuario(context.args[1])

    elif update.message.reply_to_message:
        # Buscar por reply
        receptor = update.message.reply_to_message.from_user

    if not receptor:
        await update.message.reply_text("⚠️ No se encontró al usuario receptor.")
        return

    dar_puntos(receptor.id, receptor.username or receptor.first_name, cantidad)

    await update.message.reply_text(
        f"🎁 @{sender.username or sender.first_name} regaló {cantidad} PiPesos a "
        f"@{receptor.username or receptor.first_name}"
    )


async def dar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /dar <cantidad> [@usuario]
    
    Transfiere PiPesos a otro usuario si tienes saldo suficiente.
    
    Cambio: Uso de función auxiliar _buscar_usuario()
    """
    if not update.message or not update.effective_user:
        return

    sender = update.effective_user

    if not context.args:
        await update.message.reply_text(
            "Uso: /dar <cantidad> [@usuario] o respondiendo a un mensaje."
        )
        return

    try:
        cantidad = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ La cantidad debe ser un número.")
        return

    if cantidad <= 0:
        await update.message.reply_text("⚠️ La cantidad debe ser mayor a 0.")
        return

    receptor = None

    if len(context.args) >= 2:
        # Buscar por mención
        receptor = _buscar_usuario(context.args[1])

    elif update.message.reply_to_message:
        # Buscar por reply
        receptor = update.message.reply_to_message.from_user

    if not receptor:
        await update.message.reply_text("⚠️ No se encontró al usuario receptor.")
        return

    # Verificar saldo del emisor
    usuarios = cargar_usuarios()
    sender_id_str = str(sender.id)

    if sender_id_str not in usuarios:
        usuarios[sender_id_str] = {"username": sender.username or sender.first_name, "saldo": 0}

    if usuarios[sender_id_str]["saldo"] < cantidad:
        await update.message.reply_text(
            f"💸 Saldo insuficiente. Tienes {usuarios[sender_id_str]['saldo']} PiPesos."
        )
        return

    # Ejecutar transferencia
    quitar_puntos(sender.id, sender.username or sender.first_name, cantidad)
    dar_puntos(receptor.id, receptor.username or receptor.first_name, cantidad)

    await update.message.reply_text(
        f"🤝 @{sender.username or sender.first_name} dio {cantidad} PiPesos a "
        f"@{receptor.username or receptor.first_name}"
    )


async def numero_azar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /NumAzar <N1> <N2>
    
    Genera un número aleatorio entre N1 y N2.
    Útil para juegos y sorteos.
    """
    if not update.message:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: /NumAzar N1 N2\nEjemplo: /NumAzar 5 15",
            reply_to_message_id=update.message.message_id,
        )
        return

    try:
        n1 = int(context.args[0])
        n2 = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ Los parámetros deben ser números enteros.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Asegurar que n1 < n2
    if n1 > n2:
        n1, n2 = n2, n1

    resultado = random.randint(n1, n2)

    await update.message.reply_text(
        f"🎲 Número al azar entre {n1} y {n2}: **{resultado}**",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id,
    )


async def quitar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /quitar <cantidad> [@usuario]
    
    Solo admins. Quita PiPesos a un usuario.
    
    Cambio: Uso de función auxiliar _buscar_usuario()
    """
    if not update.message or not update.effective_user:
        return

    sender = update.effective_user

    # Verificar que quien lo ejecuta es admin
    if not await verificar_admin(sender.id, update):
        await update.message.reply_text("⚠️ Solo los administradores pueden usar este comando.")
        logger.info(f"{sender.username} intentó /quitar sin ser admin")
        return

    # Verificar que haya al menos un argumento (cantidad)
    if len(context.args) < 1:
        await update.message.reply_text("Uso: /quitar <cantidad> [@usuario] o responder a un mensaje")
        return

    # Intentar convertir la cantidad
    try:
        cantidad = int(context.args[0])
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ La cantidad debe ser un número mayor que 0.")
        return

    receptor = None

    if len(context.args) >= 2:
        # Buscar por mención
        receptor = _buscar_usuario(context.args[1])

        if receptor is None:
            await update.message.reply_text(
                f"⚠️ No se encontró ningún usuario con el nombre @{context.args[1]}."
            )
            return

    elif update.message.reply_to_message:
        # Buscar por reply
        receptor = update.message.reply_to_message.from_user

    else:
        await update.message.reply_text("⚠️ Debes responder a un mensaje o mencionar a un usuario.")
        return

    # Quitar puntos
    quitar_puntos(receptor.id, receptor.username or receptor.first_name, cantidad)

    await update.message.reply_text(f"✅ Se han quitado {cantidad} PiPesos a @{receptor.username}.")


async def confesar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /confesar [texto]
    
    Envía una confesión anónima al tema de confesiones.
    Solo funciona en privado con el bot.
    """
    if not update.message:
        return

    user = update.effective_user

    # Verificar que es privado
    if update.message.chat.type != "private":
        await update.message.reply_text("⚠️ Este comando solo funciona en privado con el bot.")
        logger.info(f"{user.username} intentó /confesar en grupo")
        return

    # Obtener el texto de la confesión
    if not context.args:
        await update.message.reply_text(
            "✍️ Escribe tu confesión después del comando.\n"
            "Ejemplo: /confesar Me gusta cantar en la ducha 🎶"
        )
        return

    confesion = " ".join(context.args)

    try:
        # Enviar al grupo de confesiones de forma anónima
        await context.bot.send_message(
            chat_id=CHAT_IDS["confesiones"],
            message_thread_id=CHAT_IDS["confesiones_topic"],
            text=f"📢 Confesión anónima:\n\n{confesion}",
        )

        # Confirmar al usuario en privado
        await update.message.reply_text("✅ Tu confesión ha sido enviada de manera anónima.")
        logger.info(f"Confesión enviada por {user.username} ({user.id})")

    except Exception as e:
        logger.error(f"Error al enviar confesión: {e}")
        await update.message.reply_text(
            "❌ Error al enviar la confesión. Contacta con un administrador."
        )