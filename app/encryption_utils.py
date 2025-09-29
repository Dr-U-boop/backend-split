# backend/app/encryption_utils.py
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()

# Загружаем ключ шифрования из переменных окружения
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if ENCRYPTION_KEY is None:
    raise ValueError("Необходимо установить ENCRYPTION_KEY в .env файле")

# Преобразуем ключ в байты, так как Fernet работает с байтами
key_bytes = ENCRYPTION_KEY.encode('utf-8')
fernet = Fernet(key_bytes)

def encrypt_data(data: str) -> str:
    """Шифрует строку и возвращает зашифрованную строку."""
    if not isinstance(data, str):
        raise TypeError("Шифруемые данные должны быть строкой")
    encrypted_data = fernet.encrypt(data.encode('utf-8'))
    return encrypted_data.decode('utf-8')

def decrypt_data(encrypted_data: str) -> str:
    """Дешифрует строку и возвращает исходную строку."""
    if not isinstance(encrypted_data, str):
        raise TypeError("Дешифруемые данные должны быть строкой")
    decrypted_data = fernet.decrypt(encrypted_data.encode('utf-8'))
    return decrypted_data.decode('utf-8')