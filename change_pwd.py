from database import SessionLocal
import models, auth

def change_password():
    db = SessionLocal()
    user = db.query(models.Usuario).filter(models.Usuario.username == "pepito").first()
    if user:
        user.password_hash = auth.encriptar_password("3653247")
        db.commit()
        print("Password updated successfully.")
    else:
        print("User not found.")
    db.close()

if __name__ == "__main__":
    change_password()
