from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import secrets

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from dotenv import load_dotenv # <--- Импортируем функцию
import os # <--- Импортируем модуль os для доступа к переменным окружения

# Загружаем переменные из .env файла в окружение
load_dotenv()

# --- КОНФИГУРАЦИЯ БЕЗОПАСНОСТИ ---

# Читаем секретный ключ из переменных окружения
# os.getenv() вернет None, если переменная не найдена
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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