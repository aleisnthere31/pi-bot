"""
TEST - Verificar que el bot puede conectarse a Telegram
=========================================================
Este script hace pruebas básicas para asegurar que todo está configurado.
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("TEST DEL BOT PIBOT")
print("=" * 60)

# 1. CARGAR VARIABLES DE ENTORNO
print("\n1. Cargando variables de entorno...")
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "TU_TOKEN_AQUI":
    print("   [FAIL] BOT_TOKEN no esta configurado en .env")
    sys.exit(1)

print(f"   [OK] BOT_TOKEN cargado: {BOT_TOKEN[:20]}...")

# 2. VERIFICAR IMPORTS
print("\n2. Verificando imports...")
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, filters
    print("   [OK] telegram importado correctamente")
except ImportError as e:
    print(f"   [FAIL] Error importando telegram: {e}")
    sys.exit(1)

# 3. VERIFICAR CONFIG
print("\n3. Verificando configuracion...")
try:
    from config import BOT_TOKEN as CONFIG_TOKEN, CHAT_IDS
    print("   [OK] config importado correctamente")
    print(f"   - BOT_TOKEN: {CONFIG_TOKEN[:20]}...")
    print(f"   - Temas cargados: {len(CHAT_IDS)} temas")
except Exception as e:
    print(f"   [FAIL] Error cargando config: {e}")
    sys.exit(1)

# 4. VERIFICAR HANDLERS
print("\n4. Verificando handlers...")
try:
    from handlers.general import ver, dar, regalar, quitar
    from handlers.moderation import moderation_handler
    from handlers.theme_juegosYcasino import apostar, aceptar, jugar, robar
    print("   [OK] Todos los handlers cargados")
except Exception as e:
    print(f"   [FAIL] Error cargando handlers: {e}")
    sys.exit(1)

# 5. CREAR APLICACION
print("\n5. Creando aplicacion del bot...")
try:
    app = Application.builder().token(BOT_TOKEN).build()
    print("   [OK] Aplicacion creada exitosamente")
except Exception as e:
    print(f"   [FAIL] Error creando aplicacion: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE!")
print("=" * 60)
print("\nPara ejecutar el bot, usa:")
print("   python main.py")
print("\nEl bot se ejecutara en modo polling y esperara mensajes.")
print("=" * 60 + "\n")
