from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

# Configuración secreta
SECRET_KEY = "MI_LLAVE_SUPER_SECRETA_123"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encriptar_password(password):
    return pwd_context.hash(password)

def verificar_password(password_plano, password_hasheado):
    return pwd_context.verify(password_plano, password_hasheado)
def crear_token_acceso(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=30)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)