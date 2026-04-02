from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)
    costo = Column(Float, default=0.0)
    precio = Column(Float)
    stock = Column(Integer)

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_sku = Column(String, ForeignKey("productos.sku"))
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    concepto = Column(String) # Ej: Venta Pedido #5, Ajuste manual
    descarga = Column(Float, default=0.0)
    saldo = Column(Float, default=0.0)
    carga = Column(Float, default=0.0)

    producto = relationship("Producto")

class Cliente(Base):
    __tablename__ = "clientes"

    identificacion = Column(String, primary_key=True, index=True) # V2773333
    nombre = Column(String)
    apellido = Column(String)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String) # Aquí guardaremos la clave encriptada
    rol = Column(String, default="vendedor") # Puede ser 'admin' o 'vendedor'

    pedidos = relationship("Pedido", back_populates="vendedor")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String) # Nombre guardado localmente (legado)
    cliente_id = Column(String, ForeignKey("clientes.identificacion"), nullable=True)
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"))
    total = Column(Float)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    estado = Column(String, default="Pendiente") # "Pendiente" o "Facturado"

    cliente_rel = relationship("Cliente")
    vendedor = relationship("Usuario", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")

class DetallePedido(Base):
    __tablename__ = "detalles_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"))
    producto_sku = Column(String, ForeignKey("productos.sku"))
    cantidad = Column(Integer)
    precio_unitario = Column(Float)
    subtotal = Column(Float)

    pedido = relationship("Pedido", back_populates="detalles")
    producto = relationship("Producto")