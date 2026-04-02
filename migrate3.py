import datetime
from sqlalchemy import text
from database import engine

def actualizar_bd():
    with engine.connect() as conn:
        try:
            # Crear tabla clientes
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS clientes (
                    identificacion VARCHAR PRIMARY KEY,
                    nombre VARCHAR,
                    apellido VARCHAR
                )
            """))
            conn.commit()
            print("Tabla 'clientes' asegurada.")
        except Exception as e:
            print("Error con la tabla 'clientes':", e)

        try:
            # Añadir cliente_id a pedidos
            with engine.connect() as conn2:
                conn2.execute(text("ALTER TABLE pedidos ADD COLUMN cliente_id VARCHAR REFERENCES clientes(identificacion);"))
                conn2.commit()
                print("Columna 'cliente_id' añadida a pedidos.")
        except Exception as e:
            print("La columna 'cliente_id' ya existe o hubo un error:", e)

        try:
            # Crear tabla movimientos_inventario
            with engine.connect() as conn3:
                conn3.execute(text("""
                    CREATE TABLE IF NOT EXISTS movimientos_inventario (
                        id SERIAL PRIMARY KEY,
                        producto_sku VARCHAR REFERENCES productos(sku),
                        fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        concepto VARCHAR,
                        descarga FLOAT DEFAULT 0.0,
                        saldo FLOAT DEFAULT 0.0,
                        carga FLOAT DEFAULT 0.0
                    )
                """))
                conn3.commit()
                print("Tabla 'movimientos_inventario' asegurada.")
        except Exception as e:
            print("Error con la tabla 'movimientos_inventario':", e)

if __name__ == "__main__":
    actualizar_bd()
