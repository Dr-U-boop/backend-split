import sqlite3
import bcrypt

# Имя файла нашей базы данных
DB_NAME = "medical_app.db"
# Пароль для нашего первого тестового врача
TEST_PASSWORD = "supersecretpassword123"

# --- Хэшируем пароль ---
# 1. Конвертируем пароль в байты
password_bytes = TEST_PASSWORD.encode('utf-8')
# 2. Генерируем "соль" и создаем хэш
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password_bytes, salt)


# --- Подключаемся к БД (если файла нет, он создастся) ---
con = sqlite3.connect(DB_NAME)
cur = con.cursor()

# --- Создаем таблицу для врачей ---
# "IF NOT EXISTS" предотвращает ошибку, если таблица уже создана
cur.execute("""
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT
)
""")

# --- Добавляем первого тестового врача ---
# "OR IGNORE" предотвращает ошибку, если пользователь с таким username уже существует
cur.execute("""
INSERT OR IGNORE INTO doctors (username, hashed_password, full_name) 
VALUES (?, ?, ?)
""", ("doctor", hashed_password, "Иван Петрович Сидоров"))


# --- Сохраняем изменения и закрываем соединение ---
con.commit()
con.close()

print(f"База данных '{DB_NAME}' успешно создана/обновлена.")
print(f"Тестовый пользователь 'doctor' с паролем '{TEST_PASSWORD}' добавлен.")