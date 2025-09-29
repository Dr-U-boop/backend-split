from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import secrets
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from dotenv import load_dotenv # <--- Импортируем функцию
import os # <--- Импортируем модуль os для доступа к переменным окружения
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import sqlite3

# Загружаем переменные из .env файла в окружение
load_dotenv()

# --- КОНФИГУРАЦИЯ БЕЗОПАСНОСТИ ---

# Читаем секретный ключ из переменных окружения
# os.getenv() вернет None, если переменная не найдена
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_NAME = "medical_app.db"

# Добавляем проверку, что ключ действительно загружен
if SECRET_KEY is None:
    raise ValueError("Необходимо установить переменную окружения SECRET_KEY в .env файле")

def create_access_token(data: dict):
    # ... (остальной код функции остается без изменений) ...
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_doctor(token: str = Depends(oauth2_scheme)):
    """
    Зависимость для проверки JWT-токена и получения данных о текущем враче.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Ищем пользователя в БД, чтобы убедиться, что он все еще существует и активен
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM doctors WHERE username = ?", (username,))
    user = cur.fetchone()
    con.close()
    
    if user is None:
        raise credentials_exception
        
    return user