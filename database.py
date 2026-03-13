"""
DATABASE CONFIGURATION Y MODELOS ORM
========================================
Maneja la conexión a PostgreSQL (Heroku) o SQLite (desarrollo).
Define los modelos de datos usando SQLAlchemy.

CAMBIOS:
✅ Migración de JSON a base de datos SQL
✅ Modelos ORM para usuarios y transacciones
✅ Soporte PostgreSQL (Heroku) y SQLite (desarrollo)
✅ Funciones helper para consultas comunes
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ===================================================================================
# CONFIGURACION DE BASE DE DATOS
# ===================================================================================

# Detectar entorno
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Heroku: usar PostgreSQL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    db_engine_kwargs = {}
else:
    # Desarrollo local: usar SQLite
    DATABASE_URL = "sqlite:///./pibot.db"
    db_engine_kwargs = {"connect_args": {"check_same_thread": False}}

# Crear engine
engine = create_engine(DATABASE_URL, **db_engine_kwargs)

# Crear sesión factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()


# ===================================================================================
# MODELOS ORM
# ===================================================================================

class Usuario(Base):
    """
    Modelo de usuario para PiBot.
    Almacena información de usuarios y saldo de PiPesos.
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)  # Telegram user ID
    username = Column(String, nullable=True)
    saldo = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario(user_id={self.user_id}, username={self.username}, saldo={self.saldo})>"


class Transaccion(Base):
    """
    Registro de transacciones de PiPesos.
    Útil para auditoría y estadísticas.
    """
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)  # 'transferencia', 'robo', 'apuesta', 'regalo', 'quita'
    usuario_origen = Column(Integer, nullable=True)  # ID del usuario que envía
    usuario_destino = Column(Integer, nullable=True)  # ID del usuario que recibe
    cantidad = Column(Float)
    descripcion = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaccion(tipo={self.tipo}, cantidad={self.cantidad})>"


class ApuestaActiva(Base):
    """
    Registro de apuestas activas entre usuarios.
    """
    __tablename__ = "apuestas_activas"

    id = Column(Integer, primary_key=True, index=True)
    user_creator = Column(Integer, index=True)  # Usuario que crea la apuesta
    cantidad = Column(Float)
    estado = Column(String, default="pendiente")  # pendiente, aceptada, completada
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ApuestaActiva(creator={self.user_creator}, cantidad={self.cantidad})>"


# ===================================================================================
# FUNCIONES HELPER
# ===================================================================================

def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Llama esta función al iniciar el bot por primera vez.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")


def get_db():
    """
    Generador para obtener sesiones de base de datos.
    Úsalo en handlers con: session = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_usuario_o_crear(db_session, user_id: int, username: str = None):
    """
    Obtiene un usuario existente o crea uno nuevo.

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario en Telegram
        username: Username del usuario (opcional)

    Returns:
        Usuario: Objeto usuario de la BD
    """
    usuario = db_session.query(Usuario).filter(Usuario.user_id == user_id).first()

    if not usuario:
        usuario = Usuario(user_id=user_id, username=username, saldo=0.0)
        db_session.add(usuario)
        db_session.commit()

    return usuario


def obtener_saldo(db_session, user_id: int) -> float:
    """Obtiene el saldo actual de un usuario."""
    usuario = get_usuario_o_crear(db_session, user_id)
    return usuario.saldo


def transferir_puntos(
    db_session, user_origen: int, user_destino: int, cantidad: float, descripcion: str = None
) -> bool:
    """
    Transfiere puntos entre usuarios.

    Args:
        db_session: Sesión de SQLAlchemy
        user_origen: ID del usuario que envía
        user_destino: ID del usuario que recibe
        cantidad: Cantidad a transferir
        descripcion: Descripción de la transacción

    Returns:
        bool: True si la transferencia fue exitosa, False si falló
    """
    usuario_origen = get_usuario_o_crear(db_session, user_origen)
    usuario_destino = get_usuario_o_crear(db_session, user_destino)

    if usuario_origen.saldo < cantidad:
        return False  # No tiene suficientes puntos

    # Actualizar saldos
    usuario_origen.saldo -= cantidad
    usuario_destino.saldo += cantidad

    # Registrar transacción
    transaccion = Transaccion(
        tipo="transferencia",
        usuario_origen=user_origen,
        usuario_destino=user_destino,
        cantidad=cantidad,
        descripcion=descripcion or "Transferencia de puntos"
    )

    db_session.add(transaccion)
    db_session.commit()

    return True


def agregar_puntos(db_session, user_id: int, cantidad: float, descripcion: str = None):
    """
    Agrega puntos a un usuario (admin).

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario
        cantidad: Cantidad a agregar
        descripcion: Descripción de la transacción
    """
    usuario = get_usuario_o_crear(db_session, user_id)
    usuario.saldo += cantidad

    transaccion = Transaccion(
        tipo="regalo",
        usuario_destino=user_id,
        cantidad=cantidad,
        descripcion=descripcion or "Puntos agregados por admin"
    )

    db_session.add(transaccion)
    db_session.commit()


def quitar_puntos(db_session, user_id: int, cantidad: float, descripcion: str = None):
    """
    Quita puntos a un usuario (admin).

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario
        cantidad: Cantidad a quitar
        descripcion: Descripción de la transacción
    """
    usuario = get_usuario_o_crear(db_session, user_id)
    usuario.saldo = max(0, usuario.saldo - cantidad)  # No permitir saldo negativo

    transaccion = Transaccion(
        tipo="quita",
        usuario_origen=user_id,
        cantidad=cantidad,
        descripcion=descripcion or "Puntos removidos por admin"
    )

    db_session.add(transaccion)
    db_session.commit()


def crear_apuesta(db_session, user_id: int, cantidad: float) -> int:
    """
    Crea una nueva apuesta activa.

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario que crea la apuesta
        cantidad: Cantidad a apostar

    Returns:
        int: ID de la apuesta creada
    """
    apuesta = ApuestaActiva(user_creator=user_id, cantidad=cantidad)
    db_session.add(apuesta)
    db_session.commit()
    return apuesta.id


def obtener_apuesta_activa(db_session, user_id: int) -> ApuestaActiva:
    """
    Obtiene la apuesta activa de un usuario.

    Returns:
        ApuestaActiva: La apuesta si existe, None si no hay
    """
    return (
        db_session.query(ApuestaActiva)
        .filter(ApuestaActiva.user_creator == user_id, ApuestaActiva.estado == "pendiente")
        .first()
    )


def cancelar_apuesta(db_session, apuesta_id: int):
    """Cancela una apuesta activa."""
    apuesta = db_session.query(ApuestaActiva).filter(ApuestaActiva.id == apuesta_id).first()
    if apuesta:
        db_session.delete(apuesta)
        db_session.commit()


if __name__ == "__main__":
    # Script de inicialización
    init_db()


# ===================================================================================
# MODELOS ORM
# ===================================================================================

class Usuario(Base):
    """
    Modelo de usuario para PiBot.
    Almacena información de usuarios y saldo de PiPesos.
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)  # Telegram user ID
    username = Column(String, nullable=True)
    saldo = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario(user_id={self.user_id}, username={self.username}, saldo={self.saldo})>"


class Transaccion(Base):
    """
    Registro de transacciones de PiPesos.
    Útil para auditoría y estadísticas.
    """
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String)  # 'transferencia', 'robo', 'apuesta', 'regalo', 'quita'
    usuario_origen = Column(Integer, nullable=True)  # ID del usuario que envía
    usuario_destino = Column(Integer, nullable=True)  # ID del usuario que recibe
    cantidad = Column(Float)
    descripcion = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaccion(tipo={self.tipo}, cantidad={self.cantidad})>"


class ApuestaActiva(Base):
    """
    Registro de apuestas activas entre usuarios.
    """
    __tablename__ = "apuestas_activas"

    id = Column(Integer, primary_key=True, index=True)
    user_creator = Column(Integer, index=True)  # Usuario que crea la apuesta
    cantidad = Column(Float)
    estado = Column(String, default="pendiente")  # pendiente, aceptada, completada
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ApuestaActiva(creator={self.user_creator}, cantidad={self.cantidad})>"


# ===================================================================================
# FUNCIONES HELPER
# ===================================================================================

def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Llama esta función al iniciar el bot por primera vez.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")


def get_db():
    """
    Generador para obtener sesiones de base de datos.
    Úsalo en handlers con: session = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_usuario_o_crear(db_session, user_id: int, username: str = None):
    """
    Obtiene un usuario existente o crea uno nuevo.

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario en Telegram
        username: Username del usuario (opcional)

    Returns:
        Usuario: Objeto usuario de la BD
    """
    usuario = db_session.query(Usuario).filter(Usuario.user_id == user_id).first()

    if not usuario:
        usuario = Usuario(user_id=user_id, username=username, saldo=0.0)
        db_session.add(usuario)
        db_session.commit()

    return usuario


def obtener_saldo(db_session, user_id: int) -> float:
    """Obtiene el saldo actual de un usuario."""
    usuario = get_usuario_o_crear(db_session, user_id)
    return usuario.saldo


def transferir_puntos(
    db_session, user_origen: int, user_destino: int, cantidad: float, descripcion: str = None
) -> bool:
    """
    Transfiere puntos entre usuarios.

    Args:
        db_session: Sesión de SQLAlchemy
        user_origen: ID del usuario que envía
        user_destino: ID del usuario que recibe
        cantidad: Cantidad a transferir
        descripcion: Descripción de la transacción

    Returns:
        bool: True si la transferencia fue exitosa, False si falló
    """
    usuario_origen = get_usuario_o_crear(db_session, user_origen)
    usuario_destino = get_usuario_o_crear(db_session, user_destino)

    if usuario_origen.saldo < cantidad:
        return False  # No tiene suficientes puntos

    # Actualizar saldos
    usuario_origen.saldo -= cantidad
    usuario_destino.saldo += cantidad

    # Registrar transacción
    transaccion = Transaccion(
        tipo="transferencia",
        usuario_origen=user_origen,
        usuario_destino=user_destino,
        cantidad=cantidad,
        descripcion=descripcion or "Transferencia de puntos"
    )

    db_session.add(transaccion)
    db_session.commit()

    return True


def agregar_puntos(db_session, user_id: int, cantidad: float, descripcion: str = None):
    """
    Agrega puntos a un usuario (admin).

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario
        cantidad: Cantidad a agregar
        descripcion: Descripción de la transacción
    """
    usuario = get_usuario_o_crear(db_session, user_id)
    usuario.saldo += cantidad

    transaccion = Transaccion(
        tipo="regalo",
        usuario_destino=user_id,
        cantidad=cantidad,
        descripcion=descripcion or "Puntos agregados por admin"
    )

    db_session.add(transaccion)
    db_session.commit()


def quitar_puntos(db_session, user_id: int, cantidad: float, descripcion: str = None):
    """
    Quita puntos a un usuario (admin).

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario
        cantidad: Cantidad a quitar
        descripcion: Descripción de la transacción
    """
    usuario = get_usuario_o_crear(db_session, user_id)
    usuario.saldo = max(0, usuario.saldo - cantidad)  # No permitir saldo negativo

    transaccion = Transaccion(
        tipo="quita",
        usuario_origen=user_id,
        cantidad=cantidad,
        descripcion=descripcion or "Puntos removidos por admin"
    )

    db_session.add(transaccion)
    db_session.commit()


def crear_apuesta(db_session, user_id: int, cantidad: float) -> int:
    """
    Crea una nueva apuesta activa.

    Args:
        db_session: Sesión de SQLAlchemy
        user_id: ID del usuario que crea la apuesta
        cantidad: Cantidad a apostar

    Returns:
        int: ID de la apuesta creada
    """
    apuesta = ApuestaActiva(user_creator=user_id, cantidad=cantidad)
    db_session.add(apuesta)
    db_session.commit()
    return apuesta.id


def obtener_apuesta_activa(db_session, user_id: int) -> ApuestaActiva:
    """
    Obtiene la apuesta activa de un usuario.

    Returns:
        ApuestaActiva: La apuesta si existe, None si no hay
    """
    return (
        db_session.query(ApuestaActiva)
        .filter(ApuestaActiva.user_creator == user_id, ApuestaActiva.estado == "pendiente")
        .first()
    )


def cancelar_apuesta(db_session, apuesta_id: int):
    """Cancela una apuesta activa."""
    apuesta = db_session.query(ApuestaActiva).filter(ApuestaActiva.id == apuesta_id).first()
    if apuesta:
        db_session.delete(apuesta)
        db_session.commit()


if __name__ == "__main__":
    # Script de inicialización
    init_db()
