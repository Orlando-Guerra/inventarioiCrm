from sqlalchemy import text
from database import engine

def actualizar_bd():
    with engine.connect() as conn:
        try:
            # Añadir columna rol si no existe
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN rol VARCHAR(50) DEFAULT 'vendedor';"))
            conn.commit()
            print("Columna 'rol' añadida con éxito.")
        except Exception as e:
            print("La columna 'rol' ya existe o hubo un error:", e)
        
        try:
            # Poner a 'pepito' (o el usuario inicial que haya) como admin
            conn.execute(text("UPDATE usuarios SET rol = 'admin' WHERE username = 'pepito';"))
            conn.commit()
            print("Usuario pepito ahora es admin.")
        except Exception as e:
            print("Error actualizando pepito:", e)

if __name__ == "__main__":
    actualizar_bd()
