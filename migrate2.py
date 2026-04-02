from sqlalchemy import text
from database import engine

def actualizar_bd():
    with engine.connect() as conn:
        try:
            # Añadir columna costo si no existe
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE productos ADD COLUMN costo FLOAT DEFAULT 0.0;"))
                conn.commit()
                print("Columna 'costo' añadida a productos.")
        except Exception as e:
            print("La columna 'costo' ya existe o hubo un error:", e)
            
        try:
            # Añadir columna estado a pedidos si no existe
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE pedidos ADD COLUMN estado VARCHAR(50) DEFAULT 'Pendiente';"))
                conn.commit()
                print("Columna 'estado' añadida a pedidos.")
        except Exception as e:
            print("Error actualizando pedidos:", e)

if __name__ == "__main__":
    actualizar_bd()
