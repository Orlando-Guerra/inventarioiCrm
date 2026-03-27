from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Para servir el HTML
import models, auth
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

# --- RUTA PARA EL FRONTEND ---

@app.get("/")
def serve_homepage():
    # Esto busca el archivo index.html en la misma carpeta
    return FileResponse("index.html")

# --- RUTAS DE SEGURIDAD ---

@app.post("/usuarios/", tags=["Seguridad"])
def registrar_usuario(username: str, password: str, db: Session = Depends(get_db)):
    existe = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    pwd_hash = auth.encriptar_password(password)
    nuevo_usuario = models.Usuario(username=username, password_hash=pwd_hash)
    db.add(nuevo_usuario)
    db.commit()
    return {"mensaje": "Usuario creado correctamente", "username": username}

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
    return {"access_token": token, "token_type": "bearer"}

# --- RUTAS DE INVENTARIO ---

@app.get("/productos/", tags=["Inventario"])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(models.Producto).all()

@app.post("/productos/", tags=["Inventario"])
def crear_producto(
    sku: str, 
    nombre: str, 
    precio: float, 
    stock: int, 
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    existe_prod = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if existe_prod:
        raise HTTPException(status_code=400, detail="El SKU ya existe")
        
    item = models.Producto(sku=sku, nombre=nombre, precio=precio, stock=stock)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"mensaje": "Producto agregado", "data": item}

@app.delete("/productos/{sku}", tags=["Inventario"])
def eliminar_producto(sku: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    item = db.query(models.Producto).filter(models.Producto.sku == sku).first()
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(item)
    db.commit()
    return {"mensaje": f"Producto {sku} eliminado"}