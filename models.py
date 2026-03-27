from sqlalchemy import Column, Integer, String, Float
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)
    precio = Column(Float)
    stock = Column(Integer)

from sqlalchemy import Column, Integer, String, Float, Boolean

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String) # Aquí guardaremos la clave encriptada