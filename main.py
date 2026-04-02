from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Para servir el HTML
import models, auth
from database import engine, get_db
from pydantic import BaseModel
from typing import List, Optional
from jose import jwt, JWTError

class ItemPedido(BaseModel):
    sku: str
    cantidad: int

class PedidoCreate(BaseModel):
    cliente: str
    cliente_id: Optional[str] = None
    detalles: List[ItemPedido]
from database import engine, get_db

from fastapi.staticfiles import StaticFiles

# Crea las tablas en Neon
models.Base.metadata.create_all(bind=engine)

# Solo una declaración de app con todo lo necesario
app = FastAPI(title="Sistema de Inventario Pro")

# Esto permite que FastAPI lea archivos como style.css automáticamente
app.mount("/static", StaticFiles(directory="."), name="static")

# Configuración de CORS (Fundamental para el index.html)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

# --- RUTA PARA EL FRONTEND ---

@app.get("/")
def serve_homepage():
    # Esto busca el archivo index.html en la misma carpeta
    return FileResponse("index.html")

@app.get("/style.css")
def serve_css():
    return FileResponse("style.css")

# --- RUTAS DE SEGURIDAD ---

@app.post("/usuarios/", tags=["Seguridad"])
def registrar_usuario(username: str, password: str, rol: str = "vendedor", db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear usuarios")
    existe = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    pwd_hash = auth.encriptar_password(password)
    nuevo_usuario = models.Usuario(username=username, password_hash=pwd_hash, rol=rol)
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario creado correctamente", "username": username}

@app.get("/usuarios/", tags=["Seguridad"])
def listar_usuarios(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    return db.query(models.Usuario).all()

@app.post("/login", tags=["Seguridad"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not usuario or not auth.verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.crear_token_acceso(data={"sub": usuario.username})
    return {"access_token": token, "token_type": "bearer", "rol": usuario.rol, "username": usuario.username}

# --- RUTAS DE INVENTARIO ---

@app.get("/productos/", tags=["Inventario"])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(models.Producto).all()

@app.post("/productos/", tags=["Inventario"])
def crear_producto(
    sku: str, 
    nombre: str, 
    costo: float,
    precio: float, 
    stock: int, 
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para crear productos")
    existe_prod = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if existe_prod:
        raise HTTPException(status_code=400, detail="El SKU ya existe")
        
    item = models.Producto(sku=sku, nombre=nombre, costo=costo, precio=precio, stock=stock)
    db.add(item)
    db.commit()
    db.refresh(item)
    
    if stock > 0:
        mov = models.MovimientoInventario(producto_sku=sku, concepto="Inventario Inicial", carga=stock, saldo=stock)
        db.add(mov)
        db.commit()
        
    return {"mensaje": "Producto agregado", "data": item}

class ProductoUpdate(BaseModel):
    nombre: str
    costo: float
    precio: float

@app.put("/productos/{sku}", tags=["Inventario"])
def actualizar_producto(sku: str, prod_data: ProductoUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    prod = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    prod.nombre = prod_data.nombre
    prod.costo = prod_data.costo
    prod.precio = prod_data.precio
    db.commit()
    db.refresh(prod)
    return {"mensaje": "Producto actualizado", "data": prod}

class AjusteStock(BaseModel):
    tipo: str # "carga", "descarga", "ajuste"
    cantidad: int

@app.post("/productos/{sku}/ajustar", tags=["Inventario"])
def ajustar_stock(sku: str, ajuste: AjusteStock, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    prod = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    saldo_anterior = prod.stock
    carga = 0
    descarga = 0
    concepto = "Ajuste manual"
    
    if ajuste.tipo == "carga":
        prod.stock += ajuste.cantidad
        carga = ajuste.cantidad
        concepto = f"CAR - Por: {current_user.username} - Cant: {ajuste.cantidad}"
    elif ajuste.tipo == "descarga":
        prod.stock -= ajuste.cantidad
        if prod.stock < 0: prod.stock = 0
        descarga = saldo_anterior - prod.stock
        concepto = f"DES - Por: {current_user.username} - Cant: {descarga}"
    elif ajuste.tipo == "ajuste":
        diferencia = ajuste.cantidad - prod.stock
        signo = "+" if diferencia > 0 else ""
        if ajuste.cantidad > prod.stock:
            carga = diferencia
        else:
            descarga = abs(diferencia)
        prod.stock = ajuste.cantidad
        concepto = f"AJU - Por: {current_user.username} (Dif: {signo}{diferencia})"
    else:
        raise HTTPException(status_code=400, detail="Tipo de ajuste inválido")
        
    db.commit()
    db.refresh(prod)
    
    mov = models.MovimientoInventario(producto_sku=sku, concepto=concepto, carga=carga, descarga=descarga, saldo=prod.stock)
    db.add(mov)
    db.commit()
    
    return {"mensaje": "Stock actualizado", "nuevo_stock": prod.stock}

@app.delete("/productos/{sku}", tags=["Inventario"])
def eliminar_producto(sku: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado para borrar productos")

    item = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    db.query(models.MovimientoInventario).filter(models.MovimientoInventario.producto_sku == sku).delete()
    db.query(models.DetallePedido).filter(models.DetallePedido.producto_sku == sku).delete()
    
    db.delete(item)
    db.commit()
    return {"mensaje": f"Producto {sku} eliminado"}

# --- RUTAS DE PEDIDOS ---

@app.post("/pedidos/", tags=["Pedidos"])
def crear_pedido(pedido: PedidoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    total = 0
    detalles_db = []
    
    for item in pedido.detalles:
        producto = db.query(models.Producto).filter(models.Producto.sku == item.sku).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.sku} no encontrado")
        if producto.stock < item.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {producto.nombre}")
        
        subtotal = item.cantidad * producto.precio
        total += subtotal
        producto.stock -= item.cantidad
        
        detalle = models.DetallePedido(
            producto_sku=item.sku,
            cantidad=item.cantidad,
            precio_unitario=producto.precio,
            subtotal=subtotal
        )
        detalles_db.append(detalle)
    
    nuevo_pedido = models.Pedido(cliente=pedido.cliente, cliente_id=pedido.cliente_id, vendedor_id=current_user.id, total=total)
    db.add(nuevo_pedido)
    db.commit()
    db.refresh(nuevo_pedido)
    
    for det in detalles_db:
        det.pedido_id = nuevo_pedido.id
        db.add(det)
        
        # Registrar movimiento de inventario (Kardex)
        prod = db.query(models.Producto).filter(models.Producto.sku == det.producto_sku).first()
        if prod:
            mov = models.MovimientoInventario(
                producto_sku=det.producto_sku,
                concepto=f"FAC #{nuevo_pedido.id} - {nuevo_pedido.cliente} - Cant: {det.cantidad}",
                descarga=det.cantidad,
                saldo=prod.stock
            )
            db.add(mov)
    
    db.commit()
    return {"mensaje": "Pedido procesado", "pedido_id": nuevo_pedido.id, "total": total}

@app.get("/pedidos/", tags=["Pedidos"])
def listar_pedidos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Admin ve todo, Cajero ve todo, Vendedor ve lo suyo
    if current_user.rol in ["admin", "cajero"]:
        pedidos = db.query(models.Pedido).order_by(models.Pedido.id.desc()).all()
    else:
        pedidos = db.query(models.Pedido).filter(models.Pedido.vendedor_id == current_user.id).order_by(models.Pedido.id.desc()).all()
    
    resultado = []
    for p in pedidos:
        detalles = db.query(models.DetallePedido).filter(models.DetallePedido.pedido_id == p.id).all()
        detalles_lista = []
        for d in detalles:
            prod = db.query(models.Producto).filter(models.Producto.sku == d.producto_sku).first()
            detalles_lista.append({
                "sku": d.producto_sku,
                "nombre": prod.nombre if prod else "Desconocido",
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.subtotal
            })
        resultado.append({
            "id": p.id,
            "cliente": p.cliente,
            "vendedor": p.vendedor.username if p.vendedor else "Desconocido",
            "total": p.total,
            "estado": p.estado,
            "fecha": p.fecha.strftime("%Y-%m-%d %H:%M:%S") if p.fecha else "",
            "detalles": detalles_lista
        })
    return resultado

@app.post("/pedidos/{pedido_id}/facturar", tags=["Pedidos"])
def facturar_pedido(pedido_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol not in ["admin", "cajero"]:
        raise HTTPException(status_code=403, detail="No autorizado para facturar")
    
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
        
    pedido.estado = "Facturado"
    db.commit()
    return {"mensaje": "Pedido facturado exitosamente"}

# --- RUTAS DE CLIENTES ---

class ClienteCreate(BaseModel):
    identificacion: str
    nombre: str
    apellido: str

@app.get("/clientes/{identificacion}", tags=["Clientes"])
def obtener_cliente(identificacion: str, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.identificacion == identificacion).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"identificacion": cliente.identificacion, "nombre": cliente.nombre, "apellido": cliente.apellido}

@app.post("/clientes/", tags=["Clientes"])
def registrar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    existe = db.query(models.Cliente).filter(models.Cliente.identificacion == cliente.identificacion).first()
    if existe:
        raise HTTPException(status_code=400, detail="El cliente ya existe")
    
    nuevo_cliente = models.Cliente(identificacion=cliente.identificacion, nombre=cliente.nombre, apellido=cliente.apellido)
    db.add(nuevo_cliente)
    db.commit()
    return {"mensaje": "Cliente registrado exitosamente"}

class ClienteUpdate(BaseModel):
    nombre: str
    apellido: str

@app.put("/clientes/{identificacion}", tags=["Clientes"])
def actualizar_cliente(identificacion: str, datos: ClienteUpdate, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.identificacion == identificacion).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    cliente.nombre = datos.nombre
    cliente.apellido = datos.apellido
    db.commit()
    db.refresh(cliente)
    return {"mensaje": "Cliente actualizado", "data": {"nombre": cliente.nombre, "apellido": cliente.apellido}}

# --- RUTAS DE REPORTES ---

@app.get("/reportes/movimientos/{sku}", tags=["Reportes"])
def reporte_movimientos(sku: str, desde: Optional[str] = None, hasta: Optional[str] = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    query = db.query(models.MovimientoInventario).filter(models.MovimientoInventario.producto_sku.ilike(sku))
    
    import datetime
    if desde:
        # Compensar diferencia local vs UTC
        fecha_desde = datetime.datetime.strptime(desde, "%Y-%m-%d") - datetime.timedelta(days=1)
        query = query.filter(models.MovimientoInventario.fecha >= fecha_desde)
    if hasta:
        # Compensar diferencia local vs UTC (UTC siempre es en el futuro respecto a latam)
        fecha_hasta = datetime.datetime.strptime(hasta, "%Y-%m-%d") + datetime.timedelta(days=2)
        query = query.filter(models.MovimientoInventario.fecha < fecha_hasta)
        
    movs = query.order_by(models.MovimientoInventario.id.asc()).all()
    
    resultado = []
    for m in movs:
        resultado.append({
            "fecha": m.fecha.strftime("%Y-%m-%d %H:%M"),
            "concepto": m.concepto,
            "descarga": m.descarga,
            "saldo": m.saldo,
            "carga": m.carga
        })
    return resultado

@app.get("/reportes/clientes/{identificacion}", tags=["Reportes"])
def reporte_compras_cliente(identificacion: str, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
        
    cliente = db.query(models.Cliente).filter(models.Cliente.identificacion == identificacion).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    pedidos = db.query(models.Pedido).filter(models.Pedido.cliente_id == identificacion).order_by(models.Pedido.id.desc()).all()
    
    resultado = {
        "cliente": f"{cliente.nombre} {cliente.apellido}",
        "compras": []
    }
    
    for p in pedidos:
        resultado["compras"].append({
            "id": p.id,
            "fecha": p.fecha.strftime("%Y-%m-%d %H:%M:%S") if p.fecha else "",
            "total": p.total,
            "estado": p.estado,
            "vendedor": p.vendedor.username if p.vendedor else "Desconocido"
        })
        
    return resultado