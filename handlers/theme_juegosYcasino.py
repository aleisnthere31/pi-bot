"""
🎲 SISTEMA DE JUEGOS Y APUESTAS - TEMA EXCLUSIVE
================================================
Contiene todos los juegos y apuestas disponibles en el tema "Juegos y Casino":

JUEGOS DISPONIBLES:
1. /apostar <cantidad> - Apuesta PvP con dados
2. /aceptar - Acepta una apuesta activa
3. /cancelar - Cancela tu apuesta
4. /jugar - Juego diario (costo 5, ganancia 50)
5. /robar @usuario - Intenta robar dinero (33% éxito)

CAMBIOS PRINCIPALES:
✅ Documentación completa con docstrings
✅ FIX CRÍTICO: robar_usuarios ahora es variable GLOBAL (no se reinicia)
✅ Mejor manejo de tipos y validaciones
✅ Logging agregado para debugging
✅ Funciones auxiliares para evitar duplicación
✅ Comentarios explicativos en todo el código
✅ Mejor estructura y organización
"""

import asyncio
import random
import logging
from datetime import datetime
from types import SimpleNamespace
from telegram import Update
from telegram.ext import ContextTypes

try:
    from handlers.general import (
        cargar_usuarios,
        guardar_usuarios,
        dar_puntos,
        quitar_puntos,
        existe_usuario,
        agregar_usuario,
    )
    from config import CHAT_IDS
except ImportError:
    # Fallback para ejecucion como paquete
    from .general import (
        cargar_usuarios,
        guardar_usuarios,
        dar_puntos,
        quitar_puntos,
        existe_usuario,
        agregar_usuario,
    )
    from ..config import CHAT_IDS

# ===================================================================================
# 📝 LOGGING
# ===================================================================================
logger = logging.getLogger(__name__)

# ===================================================================================
# 💾 BASE DE DATOS EN MEMORIA
# ===================================================================================
# Diccionario de apuestas activas
# Estructura: {thread_id: {"apostador_id": int, "rival_id": int, ...}}
active_bets = {}

# FIX CRÍTICO: Este diccionario DEBE estar aquí (nivel de módulo)
# y NO reiniciarse en cada llamada a /robar
# Estructura: {user_id: "YYYY-MM-DD"} (última fecha que usó /robar)
robar_usuarios = {}


# ===================================================================================
# 🔧 FUNCIONES AUXILIARES
# ===================================================================================


def _buscar_usuario_por_mention(mention: str) -> SimpleNamespace | None:
    """
    🔧 FUNCIÓN AUXILIAR
    
    Busca un usuario en la base de datos por su mención (@username).
    
    Cambio: Función auxiliar reutilizable en /robar y otros comandos
    
    Args:
        mention (str): Username a buscar (con o sin @)
        
    Returns:
        SimpleNamespace | None: Usuario encontrado o None
    """
    usuarios = cargar_usuarios()
    mention_clean = mention.lstrip("@").strip().lower()

    for uid, info in usuarios.items():
        if (info.get("username") or "").strip().lower() == mention_clean:
            return SimpleNamespace(
                id=int(uid),
                username=info.get("username")
            )

    return None


def _check_tema_juegos(thread_id: int | None) -> bool:
    """
    🔧 FUNCIÓN AUXILIAR
    
    Verifica si el mensaje está en el tema "Juegos y Casino".
    
    Cambio: Función reutilizable para validación de tema
    
    Args:
        thread_id (int | None): ID del tema actual
        
    Returns:
        bool: True si está en el tema correcto, False si no
    """
    if thread_id != CHAT_IDS["theme_juegosYcasino"]:
        return False
    return True


# ===================================================================================
# 🎲 APUESTAS PvP CON DADOS
# ===================================================================================


async def apostar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /apostar <cantidad>
    
    Crea una apuesta PvP. Otro jugador puede /aceptar en 60 segundos.
    Ambos lanzan dados y el que saque más alto gana.
    
    Cambio: Documentación y logging mejorado
    """
    if not update.message or not update.effective_user:
        return

    thread_id = update.message.message_thread_id
    user = update.effective_user

    # 📌 VALIDACIÓN 1: Solo en tema de Juegos y Casino
    if not _check_tema_juegos(thread_id):
        await update.message.reply_text(
            "⚠️ Este comando solo está permitido en el tema Juegos y Casino."
        )
        logger.warning(f"Usuario {user.id} intentó /apostar fuera del tema correcto")
        return

    # 📌 VALIDACIÓN 2: Parámetros correctos
    if len(context.args) < 1:
        await update.message.reply_text("Uso: /apostar <cantidad>")
        return

    try:
        cantidad = int(context.args[0])
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ La cantidad debe ser un número mayor que 0.")
        return

    # 📌 VALIDACIÓN 3: No hay apuesta activa
    if thread_id in active_bets:
        await update.message.reply_text("⚠️ Ya hay una apuesta activa en este tema.")
        return

    # 📌 VALIDACIÓN 4: Usuario existe y tiene saldo
    saldo = existe_usuario(user.id)

    if saldo is False:
        await update.message.reply_text(
            "⚠️ No tienes cuenta registrada. Usa /ver para registrarte."
        )
        return

    if saldo < cantidad:
        await update.message.reply_text(f"💸 Saldo insuficiente. Tu saldo es {saldo} PiPesos.")
        return

    # ✅ CREAR APUESTA
    active_bets[thread_id] = {
        "apostador_id": user.id,
        "apostador_username": user.username or user.first_name,
        "rival_id": None,
        "rival_username": None,
        "cantidad": cantidad,
        "dados": {"apostador": None, "rival": None},
        "activa": True,
    }

    logger.info(f"Apuesta creada: {user.username} apuesta {cantidad} PiPesos en tema {thread_id}")

    await update.message.reply_text(
        f"🎲 @{user.username or user.first_name} ha creado una apuesta de {cantidad} PiPesos.\n"
        "Cualquier jugador puede escribir /aceptar para unirse en los próximos 60 segundos."
    )

    # 📌 AUTO-CANCELACIÓN EN 60 SEGUNDOS
    async def auto_cancel():
        await asyncio.sleep(60)
        bet = active_bets.get(thread_id)
        if bet and bet["activa"] and bet["rival_id"] is None:
            del active_bets[thread_id]
            logger.info(f"Apuesta en tema {thread_id} cancelada automáticamente por timeout")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Tiempo agotado. La apuesta fue cancelada automáticamente.",
                message_thread_id=thread_id,
            )

    asyncio.create_task(auto_cancel())


async def aceptar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /aceptar
    
    Acepta una apuesta activa. Ambos jugadores deben lanzar dados después.
    
    Cambio: Documentación y logging mejorado
    """
    if not update.message or not update.effective_user:
        return

    thread_id = update.message.message_thread_id
    user = update.effective_user

    # 📌 VALIDACIÓN 1: Existe apuesta activa
    bet = active_bets.get(thread_id)
    if not bet:
        await update.message.reply_text("⚠️ No hay apuestas activas para aceptar en este tema.")
        return

    # 📌 VALIDACIÓN 2: La apuesta no ha sido aceptada ya
    if bet["rival_id"] is not None:
        await update.message.reply_text("⚠️ Esta apuesta ya fue aceptada por otro jugador.")
        return

    # 📌 VALIDACIÓN 3: No aceptar tu propia apuesta
    if user.id == bet["apostador_id"]:
        await update.message.reply_text("⚠️ No puedes aceptar tu propia apuesta.")
        logger.warning(f"Usuario {user.id} intentó aceptar su propia apuesta")
        return

    # 📌 VALIDACIÓN 4: Usuario existe en sistema
    saldo = existe_usuario(user.id)
    if saldo is False:
        agregar_usuario(user.id, 0, user.username or user.first_name)
        logger.info(f"Usuario {user.id} registrado automáticamente")
        saldo = 0

    # 📌 VALIDACIÓN 5: Usuario tiene saldo suficiente
    if saldo < bet["cantidad"]:
        await update.message.reply_text(f"💸 Saldo insuficiente. Tu saldo es {saldo} PiPesos.")
        return

    # ✅ ACEPTAR APUESTA
    bet["rival_id"] = user.id
    bet["rival_username"] = user.username or user.first_name

    logger.info(
        f"Apuesta aceptada: {bet['apostador_username']} vs {user.username} "
        f"por {bet['cantidad']} PiPesos"
    )

    await update.message.reply_text(
        f"✅ @{user.username or user.first_name} ha aceptado la apuesta de "
        f"@{bet['apostador_username']}.\n\n"
        f"🎲 ¡Ambos deben lanzar el dado para continuar!"
    )


async def cancelar_apuesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /cancelar
    
    Cancela la apuesta activa.
    Solo el que la creó puede cancelar.
    
    Cambio: Documentación mejorada
    """
    if not update.message or not update.effective_user:
        return

    thread_id = update.message.message_thread_id
    user = update.effective_user

    # 📌 VALIDACIÓN 1: Existe apuesta activa
    bet = active_bets.get(thread_id)
    if not bet:
        await update.message.reply_text("⚠️ No hay apuesta activa para cancelar en este tema.")
        return

    # 📌 VALIDACIÓN 2: Solo el creador puede cancelar
    if user.id != bet["apostador_id"]:
        await update.message.reply_text("⚠️ Solo quien creó la apuesta puede cancelarla.")
        logger.warning(
            f"Usuario {user.id} intentó cancelar apuesta creada por {bet['apostador_id']}"
        )
        return

    # ✅ CANCELAR APUESTA
    del active_bets[thread_id]
    logger.info(f"Apuesta en tema {thread_id} cancelada por {user.username}")

    await update.message.reply_text(f"❌ @{user.username or user.first_name} canceló la apuesta.")


async def detectar_dado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 HANDLER AUTOMÁTICO: Detecta dados en apuestas
    
    Se activa automáticamente cuando alguien lanza un dado.
    Determina al ganador cuando ambos han lanzado.
    
    Cambio: Documentación y manejo de errores mejorado
    """
    msg = update.message
    if not msg or not msg.dice:
        return

    thread_id = msg.message_thread_id
    bet = active_bets.get(thread_id)
    if not bet:
        return  # No hay apuesta activa

    user = msg.from_user
    jugador = None

    # Determinar cuál jugador lanzó
    if user.id == bet["apostador_id"]:
        jugador = "apostador"
    elif user.id == bet["rival_id"]:
        jugador = "rival"
    else:
        return  # Quien lanzó no es parte de la apuesta

    # Registrar resultado
    valor = msg.dice.value
    bet["dados"][jugador] = valor

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎲 @{user.username or user.first_name} ha lanzado el dado y sacó {valor}",
        message_thread_id=thread_id,
    )

    logger.info(f"Dado lanzado: {user.username} sacó {valor}")

    # ========================================================================
    # Si ambos ya lanzaron, DETERMINAR GANADOR
    # ========================================================================
    if bet["dados"]["apostador"] is not None and bet["dados"]["rival"] is not None:
        ap = bet["dados"]["apostador"]
        rv = bet["dados"]["rival"]

        apostador_id = bet["apostador_id"]
        rival_id = bet["rival_id"]
        cantidad = bet["cantidad"]

        # Verificar que ambos usuarios existan
        if not existe_usuario(apostador_id) or not existe_usuario(rival_id):
            logger.error(f"Error: Usuario no existe en BD. Apostador: {apostador_id}, Rival: {rival_id}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Error: No se encontraron los datos de uno o ambos jugadores en el sistema.",
                message_thread_id=thread_id,
            )
            del active_bets[thread_id]
            return

        # Determinar ganador
        if ap > rv:
            resultado = f"🏆 @{bet['apostador_username']} gana la apuesta de {cantidad} PiPesos!"
            dar_puntos(apostador_id, bet["apostador_username"], cantidad)
            quitar_puntos(rival_id, bet["rival_username"], cantidad)
            logger.info(f"Apuesta ganada por {bet['apostador_username']}")

        elif rv > ap:
            resultado = f"🏆 @{bet['rival_username']} gana la apuesta de {cantidad} PiPesos!"
            dar_puntos(rival_id, bet["rival_username"], cantidad)
            quitar_puntos(apostador_id, bet["apostador_username"], cantidad)
            logger.info(f"Apuesta ganada por {bet['rival_username']}")

        else:
            resultado = "🤝 ¡Empate! Nadie gana ni pierde."
            logger.info(f"Apuesta en tema {thread_id} resultó en empate")

        # Enviar resultado
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=resultado,
            message_thread_id=thread_id,
        )

        # Finalizar apuesta
        del active_bets[thread_id]


# ===================================================================================
# 🎮 JUEGO DIARIO
# ===================================================================================


async def jugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /jugar
    
    Juego diario: Cuesta 5 PiPesos, si sacas 6 ganas 50 PiPesos.
    Límite: 3 veces por día.
    
    Cambio: Documentación y logging mejorado
    """
    if not update.message or not update.effective_user:
        return

    thread_id = update.message.message_thread_id
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    # 📌 VALIDACIÓN 1: Solo en tema de Juegos y Casino
    if not _check_tema_juegos(thread_id):
        await update.message.reply_text(
            "⚠️ Este comando solo está permitido en el tema Juegos y Casino."
        )
        return

    # ✅ Cargar o crear usuario
    usuarios = cargar_usuarios()
    user_id_str = str(user_id)

    if user_id_str not in usuarios:
        usuarios[user_id_str] = {
            "username": username,
            "saldo": 0,
            "jugar_veces": 0,
            "jugar_fecha": "",
        }
        guardar_usuarios(usuarios)
        logger.info(f"Usuario {username} registrado con /jugar")

    user_data = usuarios[user_id_str]
    saldo_actual = user_data["saldo"]

    # 📌 VALIDACIÓN 2: Reiniciar contador diario
    hoy = datetime.now().strftime("%Y-%m-%d")
    if user_data.get("jugar_fecha") != hoy:
        user_data["jugar_fecha"] = hoy
        user_data["jugar_veces"] = 0
        guardar_usuarios(usuarios)
        logger.debug(f"Contador diario reiniciado para {username}")

    # 📌 VALIDACIÓN 3: Límite de 3 veces por día
    if user_data["jugar_veces"] >= 3:
        await update.message.reply_text(
            "⚠️ Ya has jugado 3 veces hoy. Inténtalo de nuevo mañana."
        )
        logger.info(f"{username} intentó /jugar pero ya agotó su límite diario")
        return

    # 📌 VALIDACIÓN 4: Tiene saldo suficiente
    if saldo_actual < 5:
        await update.message.reply_text(
            f"⚠️ No tienes suficiente saldo para jugar (mínimo 5 PiPesos).\n"
            f"Saldo actual: {saldo_actual} PiPesos"
        )
        return

    # ✅ EJECUTAR JUEGO: Restar costo
    quitar_puntos(user_id, username, 5)
    user_data["jugar_veces"] += 1
    guardar_usuarios(usuarios)

    # 🎲 Lanzar dado
    dice_message = await context.bot.send_dice(
        chat_id=update.effective_chat.id,
        emoji="🎲",
        message_thread_id=thread_id,
    )
    valor = dice_message.dice.value

    # Determinar resultado
    if valor == 6:
        dar_puntos(user_id, username, 50)
        resultado = f"🎉 ¡Ganaste! Sacaste un 6 🎲\n💰 Se te acreditaron 50 PiPesos."
        logger.info(f"{username} ganó con /jugar (sacó 6)")
    else:
        resultado = f"😔 Sacaste {valor}, perdiste."
        logger.debug(f"{username} perdió con /jugar (sacó {valor})")

    # Obtener saldo actualizado
    usuarios = cargar_usuarios()
    nuevo_saldo = usuarios[user_id_str]["saldo"]

    await update.message.reply_text(
        f"{resultado}\nSaldo actual: {nuevo_saldo} PiPesos\n"
        f"🔄 Veces jugadas hoy: {user_data['jugar_veces']}/3"
    )


# ===================================================================================
# 💰 COMANDO DE ROBO
# ===================================================================================


async def robar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMANDO: /robar @usuario
    
    Intenta robar dinero a otro usuario.
    - Probabilidad de éxito: 33% (1 de 3)
    - Cantidad: 1-100 PiPesos
    - Límite: 1 intento por día
    
    Cambio: FIX CRÍTICO - robar_usuarios ahora es GLOBAL
    Documentación y logging mejorado
    """
    if not update.message or not update.effective_user:
        return

    thread_id = update.message.message_thread_id
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    # 📌 VALIDACIÓN 1: Solo en tema de Juegos y Casino
    if not _check_tema_juegos(thread_id):
        await update.message.reply_text(
            "⚠️ Este comando solo se puede usar en el tema Juegos y Casino."
        )
        return

    # 📌 VALIDACIÓN 2: Parámetros correctos
    if len(context.args) < 1:
        await update.message.reply_text("⚠️ Uso incorrecto. Debes usar /robar @Usuario.")
        return

    # 📌 VALIDACIÓN 3: Buscar usuario objetivo
    receptor = _buscar_usuario_por_mention(context.args[0])

    if receptor is None:
        await update.message.reply_text(f"⚠️ No se encontró al usuario @{context.args[0]}.")
        return

    # 📌 VALIDACIÓN 4: Control de uso diario
    hoy = datetime.now().strftime("%Y-%m-%d")
    if robar_usuarios.get(user_id) == hoy:
        await update.message.reply_text("⚠️ Solo puedes usar /robar 1 vez al día.")
        logger.info(f"{username} intentó /robar pero ya lo usó hoy")
        return

    # Registrar uso diario
    robar_usuarios[user_id] = hoy

    # ✅ EJECUTAR ROBO: 33% de probabilidad (1 de 3)
    exito = random.choice([True, False, False])

    if exito:
        # Robo exitoso
        cantidad_robada = random.randint(1, 100)
        saldo_receptor = existe_usuario(receptor.id)

        # No robar más de lo que tiene
        if cantidad_robada > saldo_receptor:
            cantidad_robada = saldo_receptor

        quitar_puntos(receptor.id, receptor.username, cantidad_robada)
        dar_puntos(user_id, username, cantidad_robada)

        logger.info(f"{username} robó {cantidad_robada} PiPesos a {receptor.username}")

        await update.message.reply_text(
            f"🎉 @{username} logró robar a @{receptor.username} "
            f"exitosamente {cantidad_robada} PiPesos"
        )

    else:
        # Robo fallido
        logger.info(f"{username} intentó robar a {receptor.username} pero falló")

        await update.message.reply_text(
            f"💨 @{username} intentó robar a @{receptor.username}, pero falló."
        )