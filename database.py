from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Reemplaza esto con la URL que te dé el servicio de base de datos (luego te digo dónde sacarla)
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_pAjYxV9PlS3C@ep-sparkling-resonance-anq027vt-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función para obtener la sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()