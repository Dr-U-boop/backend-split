from fastapi import APIRouter, HTTPException
from app.models import UserCredentials
from app.auth_utils import create_access_token
import sqlite3
import bcrypt

router = APIRouter()
DB_NAME = "medical_app.db"

@router.post("/login")
async def login_for_access_token(credentials: UserCredentials):
    # Подключаемся к базе данных
    con = sqlite3.connect(DB_NAME)
    # Устанавливаем row_factory, чтобы получать результаты в виде словарей
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1. Ищем пользователя по имени
    cur.execute("SELECT * FROM doctors WHERE username = ?", (credentials.username,))
    user_record = cur.fetchone()
    con.close()

    if not user_record:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    # 2. Сравниваем хэши паролей
    stored_hashed_password = user_record["hashed_password"]
    password_bytes = credentials.password.encode('utf-8')

    # bcrypt.checkpw сама сравнивает введенный пароль с хэшем из БД
    if not bcrypt.checkpw(password_bytes, stored_hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    
     # --- ГЕНЕРАЦИЯ JWT-ТОКЕНА ---
    # Создаем токен, содержащий имя пользователя
    access_token = create_access_token(
        data={"sub": user_record["username"]}
    )
    
    # Возвращаем токен вместо заглушки
    return {"access_token": access_token, "token_type": "bearer"}