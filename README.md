# 🤖 PiBot - Sistema de Bot para Telegram

Un bot avanzado de Telegram con sistema de economía virtual, juegos de casino, moderación y múltiples funcionalidades para comunidades.

## ✨ Características Principales

### 💰 Sistema de Economía (PiPesos)
- **Moneda virtual**: PiPesos para transacciones dentro del bot
- **Comandos básicos**:
  - `/ver` - Consultar saldo actual
  - `/dar <cantidad> @usuario` - Transferir PiPesos a otro usuario
  - `/regalar <cantidad> @usuario` - Administrador regala puntos (solo admins)
  - `/quitar <cantidad> @usuario` - Administrador quita puntos (solo admins)

### 🎲 Juegos de Azar (Tema: Juegos y Casino)
- **Apuestas PvP**:
  - `/apostar <cantidad>` - Crea una apuesta
  - `/aceptar` - Acepta una apuesta activa
  - `/cancelar` - Cancela tu apuesta
  - Ambos jugadores lanzan dados, gana quien saque el número más alto

- **Juego Diario**:
  - `/jugar` - Cuesta 5 PiPesos, gana 50 si sacas 6 🎲
  - Límite: 3 veces por día

- **Robo**:
  - `/robar @usuario` - Intenta robar 1-100 PiPesos (33% de éxito)
  - Límite: 1 vez por día

### 🛡️ Moderación
- Detección automática de spam de medios (stickers, fotos, GIFs)
- Límite configurable: máximo 4 medias en 15 segundos
- Baneo temporal automático: 10 minutos
- Temas excluidos: NSFW, Exhibicionismo, Multimedia

### 📢 Confesiones Anónimas
- `/confesar [texto]` - Envía una confesión anónima al grupo (solo en privado con el bot)

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- Pip
- Token de bot de Telegram (obtener de [@BotFather](https://t.me/BotFather))

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Pi-Bot-System.git
cd Pi-Bot-System
```

### Paso 2: Crear entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno
```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env y agregar tu BOT_TOKEN y IDs de temas
nano .env  # o usa tu editor favorito
```

### Paso 5: Ejecutar el bot
```bash
python main.py
```

## 📁 Estructura del Proyecto

```
Pi-Bot-System/
├── main.py                 # Punto de entrada principal
├── config.py              # Configuración global
├── requirements.txt       # Dependencias
├── Procfile              # Configuración para Heroku
├── .env.example          # Ejemplo de variables de entorno
├── .gitignore            # Archivos ignorados por Git
├── pipesos.json          # Base de datos JSON (usuarios y saldos)
└── handlers/             # Handlers de funcionalidades
    ├── __init__.py
    ├── general.py        # Comandos generales y sistema económico
    ├── moderation.py     # Sistema de moderación
    ├── theme_juegosYcasino.py  # Juegos y apuestas
    ├── theme_doms.py     # [Futuro] Tema de dominós
    ├── theme_sums.py     # [Futuro] Tema de sumas
    └── json/             # Carpeta para archivos JSON locales
```

## 🔧 Configuración Avanzada

### Cambiar IDs de Temas
Los IDs de temas se configuran en el archivo `.env`:
```env
THEME_JUEGOS_CASINO=6791
THEME_NSFW=834
```

Obtener el ID de un tema:
1. En el grupo, usar `/id` dentro del tema
2. El bot responderá con el Theme (message_thread_id)

### Ajustar Límites de Moderación
En `.env`:
```env
MAX_MEDIA=4              # Número máximo de medias
WINDOW_TIME=15           # Segundos para el contador
BAN_TIME=600             # Segundos de baneo (600 = 10 min)
```

## 💾 Base de Datos

El bot usa **JSON local** (`pipesos.json`) para almacenar datos de usuarios:

```json
{
  "usuarios": {
    "123456789": {
      "username": "username",
      "saldo": 500
    }
  }
}
```

**Nota**: La base de datos es local. Para un bot en producción, considera migrar a una base de datos como PostgreSQL.

## 🚢 Despliegue en Heroku

1. Crear cuenta en [Heroku](https://www.heroku.com)
2. Instalar Heroku CLI
3. Ejecutar:
```bash
heroku login
heroku create tu-nombre-de-app
git push heroku main
```

El `Procfile` está configurado para ejecutar el bot automáticamente.

## 📝 Comandos Disponibles

| Comando | Descripción | Restricción |
|---------|-------------|------------|
| `/ver` | Ver saldo actual | - |
| `/dar <cant> @user` | Transferir PiPesos | - |
| `/regalar <cant> @user` | Regalar puntos | Solo admin |
| `/quitar <cant> @user` | Quitar puntos | Solo admin |
| `/NumAzar N1 N2` | Número aleatorio | - |
| `/confesar <texto>` | Confesión anónima | Privado |
| `/apostar <cant>` | Crear apuesta | Tema juegos |
| `/aceptar` | Aceptar apuesta | Tema juegos |
| `/cancelar` | Cancelar apuesta | Tema juegos |
| `/jugar` | Jugar (costo 5) | Tema juegos |
| `/robar @user` | Robar puntos | Tema juegos |
| `/id` | Ver IDs del chat/tema | - |

## 🐛 Troubleshooting

### El bot no inicia
- Verificar que el BOT_TOKEN sea válido en `.env`
- Revisar que el token no tenga espacios
- Ver logs en la consola

### Los comandos no funcionan
- Verificar que el bot sea admin en los temas
- Verificar que los IDs de temas sean correctos
- Usar `/id` para confirmar el message_thread_id

### Database corrupta
- Eliminar `pipesos.json` y el bot creará una nueva base de datos vacía
- Los usuarios se registran automáticamente cuando usan comandos
