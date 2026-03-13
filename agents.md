# 🤖 AGENTS.MD - Guía para Agentes de IA

Este archivo documenta la arquitectura y patrones de código del PiBot para facilitar futuras modificaciones por agentes de IA.

## 📋 Descripción General del Proyecto

**PiBot** es un bot de Telegram con las siguientes características principales:
- 💰 **Sistema de Economía**: Transacciones con moneda virtual (PiPesos)
- 🎲 **Juegos de Azar**: Apuestas, robo, juego diario
- 🛡️ **Moderación**: Detección y prevención de spam de medios
- 📢 **Confesiones**: Sistema anónimo para confesiones

## 🏗️ Arquitectura

### Stack Tecnológico
- **Lenguaje**: Python 3.13.7
- **Framework Bot**: python-telegram-bot 22.6 (async)
- **Base de Datos**: JSON local (pipesos.json)
- **Configuración**: python-dotenv 1.0.0
- **API**: Telegram Bot API (HTTP)

### Flujo Principal
```
main.py (entry point)
  ↓
config.py (load environment variables)
  ↓
handlers/ (register all handlers)
  ├── general.py (economy commands)
  ├── moderation.py (media spam detection)
  └── theme_juegosYcasino.py (games)
  ↓
Application.run_polling() (listen for messages)
  ↓
Handlers process updates and send responses
```

## 📁 Estructura del Proyecto

```
Pi-Bot-System/
├── main.py                    # Entry point, handler registration
├── config.py                  # Configuration loading and validation
├── requirements.txt           # Dependencies (python-telegram-bot==22.6, python-dotenv==1.0.0)
├── .env                       # Environment variables (BOT_TOKEN, theme IDs)
├── .env.example               # Template for .env
├── .gitignore                 # Exclude sensitive files
├── pipesos.json               # JSON database (users and balances)
├── README.md                  # User documentation
├── SETUP.txt                  # Quick setup reference
├── Procfile                   # Heroku deployment
├── agents.md                  # This file
└── handlers/
    ├── __init__.py            # Handler exports
    ├── general.py             # Economy system (ver, dar, regalar, quitar, confesar, numero_azar)
    ├── moderation.py          # Media spam detection and banning
    ├── theme_juegosYcasino.py # Games (apostar, jugar, robar)
    ├── theme_doms.py          # [STUB] Future dominoes theme
    ├── theme_sums.py          # [STUB] Future sums theme
    └── json/                  # Reserved for JSON data files
```

## 🔑 Key Components

### 1. **config.py** - Configuration Management
**Purpose**: Load and validate environment variables on startup

**Key Functions**:
- `load_dotenv()` - Load variables from .env file
- `validate_config()` - Validate BOT_TOKEN and other settings
- `BOT_TOKEN` - Telegram bot token (from environment)
- `CHAT_IDS` - Dict of theme IDs configured in .env

**Important**:
- BOT_TOKEN is NEVER committed to git (protected by .gitignore)
- All theme IDs must be validated before use
- Raises ValueError if configuration is invalid

### 2. **main.py** - Bot Initialization and Handler Registration
**Purpose**: Initialize the Telegram bot and register all handlers

**Key Structure**:
```python
async def saludar(update, context)    # Example command handler
async def get_theme_id(update, context)# Utility command
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    # Register handlers
    app.add_handler(CommandHandler("command_name", handler_function))
    # Start polling
    app.run_polling(drop_pending_updates=True)
```

**Handler Registration Pattern**:
- CommandHandler for `/command` style
- MessageHandler for message content (text, media, etc.)
- Filters control when handlers trigger (e.g., `filters.Sticker.ALL`)

### 3. **handlers/general.py** - Economy System
**Purpose**: Manage PiPesos (virtual currency) and general commands

**Database Structure**:
```json
{
  "usuarios": {
    "123456789": {
      "username": "user123",
      "saldo": 500
    }
  }
}
```

**Key Functions**:
- `cargar_usuarios()` - Load users from pipesos.json, create if missing
- `guardar_usuarios(usuarios)` - Persist changes to pipesos.json
- `_buscar_usuario(user_id)` - Helper: find or create user
- `ver(update, context)` - Show user's balance `/ver`
- `dar(update, context)` - Transfer PiPesos `/dar <qty> @user`
- `regalar(update, context)` - Admin grants PiPesos `/regalar <qty> @user`
- `quitar(update, context)` - Admin removes PiPesos `/quitar <qty> @user`
- `numero_azar(update, context)` - Random number generator `/NumAzar N1 N2`
- `confesar(update, context)` - Anonymous confession `/confesar <text>`

**Important Patterns**:
- All functions load users fresh from JSON (no in-memory cache)
- User ID is extracted from `update.effective_user.id`
- Admin checks use try/except for permission verification
- Responses are in Spanish with markdown formatting

### 4. **handlers/moderation.py** - Spam Detection
**Purpose**: Detect and prevent media spam (stickers, photos, GIFs)

**Detection Logic**:
- Count media items per theme in a rolling 15-second window
- If count exceeds MAX_MEDIA (default 4), ban user for BAN_TIME (600 sec)
- EXCLUDED_CHATS bypass moderation

**Key Functions**:
- `moderation_handler(update, context)` - Main handler detecting violations
- `is_excluded(chat_id)` - Check if theme/chat is exempt
- `_cleanup_blacklist(context.bot_data)` - Remove expired bans

**Configuration** (from .env):
```env
MAX_MEDIA=4            # Max media items per window
WINDOW_TIME=15         # Seconds for rolling window
BAN_TIME=600           # Seconds to ban (600 = 10 min)
EXCLUDED_CHATS=123,456 # Theme IDs to exclude
```

### 5. **handlers/theme_juegosYcasino.py** - Games System
**Purpose**: Implement gambling games with PiPesos

**Games**:
1. **Apuestas (Betting)**
   - `/apostar <qty>` - Create a bet (stores in module-level `robar_usuarios` dict)
   - `/aceptar` - Accept pending bet, both players roll dice
   - Loser's PiPesos go to winner

2. **Jugar (Daily Game)**
   - `/jugar` - Costs 5 PiPesos, win 50 if you roll 6
   - Limited to 3 times per day

3. **Robar (Robbery)**
   - `/robar @user` - Steal 1-100 PiPesos from target (33% success rate)
   - Limited to 1 time per day

**Key Functions**:
- `apostar(update, context)` - Create bet
- `aceptar(update, context)` - Accept bet
- `detectar_dado(update, context)` - Detect dice rolls emoji
- `jugar(update, context)` - Daily game
- `robar(update, context)` - Robbery attempt
- `cancelar_apuesta(update, context)` - Cancel pending bet

**Critical Pattern**:
```python
# Global module variable to store active bets
robar_usuarios = {}  # Dict[user_id, {opponent_id, amount, etc}]
```
⚠️ **Important**: `robar_usuarios` must be declared at module level, NOT inside functions. It persists active bets across multiple function calls.

## 🔄 Common Coding Patterns

### 1. **Handler Function Signature**
```python
async def handler_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 COMMAND: /command_name
    
    Description of what this command does.
    
    Args:
        update: Telegram update object
        context: Handler context for storing data
    """
    # Implementation
```

### 2. **Accessing User Information**
```python
user_id = update.effective_user.id
username = update.effective_user.username
chat_id = update.effective_chat.id
thread_id = update.message.message_thread_id  # For topics/themes
```

### 3. **Sending Messages**
```python
# Text message
await update.message.reply_text(
    "Message text",
    parse_mode="Markdown"  # or "HTML"
)

# With inline keyboard
buttons = [[InlineKeyboardButton("Label", callback_data="action")]]
await update.message.reply_text(
    "Message",
    reply_markup=InlineKeyboardMarkup(buttons)
)
```

### 4. **Admin Verification**
```python
from telegram import ChatMember

member = await update.effective_chat.get_member(update.effective_user.id)
is_admin = member.status in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]
if not is_admin:
    await update.message.reply_text("❌ Comando solo para admins")
    return
```

### 5. **Logging**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"User {user_id} executed /command")
logger.error(f"Error: {str(e)}", exc_info=True)
```

### 6. **JSON Database Operations**
```python
import json
import os

def cargar_usuarios():
    if os.path.exists("pipesos.json"):
        with open("pipesos.json", "r") as f:
            data = json.load(f)
            return data.get("usuarios", {})
    return {}

def guardar_usuarios(usuarios):
    data = {"usuarios": usuarios}
    with open("pipesos.json", "w") as f:
        json.dump(data, f, indent=2)
```

## 📝 Important Notes for Code Modifications

### ✅ DO's
- Always validate user input before processing
- Use try/except blocks with proper error handling
- Log important events and errors
- Add docstrings to all new functions
- Update handler registration in main.py for new commands
- Keep handler functions async
- Use markdown for message formatting (user-friendly)

### ❌ DON'Ts
- Never hardcode the BOT_TOKEN
- Don't modify global variables inside functions without explicit need
- Don't forget to import required modules at the top of handlers
- Don't use relative imports like `from .. import` (use absolute imports)
- Don't remove the JSON file backup functionality
- Don't ignore exc_info=True in error logging

## 🔧 Making Changes: Step-by-Step

### Adding a New Command
1. Create handler function in appropriate handler file
2. Register handler in main.py using `app.add_handler(CommandHandler("name", function))`
3. Add docstring with 🎯 COMMAND section
4. Test with bot in running mode
5. Commit changes to git

### Modifying Database Schema
1. Update JSON structure in handler files
2. Update cargar_usuarios() and guardar_usuarios() functions
3. Add migration logic if needed for existing databases
4. Test with existing pipesos.json file
5. Document breaking changes if any

### Adding a New Theme Handler
1. Create new file: handlers/theme_name.py
2. Import in handlers/__init__.py and main.py
3. Register handlers in main.py
4. Add theme ID to .env.example
5. Update README.md with new commands

## 🚀 Testing Checklist

Before committing changes:
- ✅ All imports resolve without errors
- ✅ BOT_TOKEN loads from .env
- ✅ All handlers register successfully
- ✅ Bot connects to Telegram API
- ✅ Test at least one command works end-to-end
- ✅ No sensitive data in commits
- ✅ Docstrings on all public functions
- ✅ Logging for important operations

## 📚 Key Files Reference

| File | Purpose | When to Modify |
|------|---------|-----------------|
| main.py | Bot initialization | Adding new handlers |
| config.py | Configuration | Adding new env variables |
| handlers/general.py | Economy | Adding economy features |
| handlers/moderation.py | Spam detection | Changing moderation rules |
| handlers/theme_juegosYcasino.py | Games | Adding new games |
| requirements.txt | Dependencies | Upgrading libraries |
| .env.example | Config template | Adding new env vars |

## 🔗 Useful Resources

- **python-telegram-bot Documentation**: https://docs.python-telegram-bot.org/
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **python-dotenv Documentation**: https://python-dotenv.readthedocs.io/

## ⚙️ Environment Variables Reference

```env
BOT_TOKEN=your_token_here
THEME_JUEGOS_CASINO=6791              # Theme ID for games
THEME_NSFW=834                        # NSFW theme (excluded from moderation)
THEME_EXHIBICIONISMO=123              # Another excluded theme
THEME_MULTIMEDIA=456                  # Another excluded theme
MAX_MEDIA=4                           # Moderation limit
WINDOW_TIME=15                        # Seconds for moderation window
BAN_TIME=600                          # Seconds to ban
EXCLUDED_CHATS=834,123,456            # Comma-separated excluded theme IDs
```

---

**Last Updated**: March 12, 2026
**Python Version**: 3.13.7
**python-telegram-bot Version**: 22.6
