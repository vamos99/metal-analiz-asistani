# utils/auth.py
import sqlite3
import os
from passlib.context import CryptContext
import re
import logging

logger = logging.getLogger(__name__)

DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "users.db")
# Şifre hashleme için bcrypt kullan
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Düz metin şifreyi hash'lenmiş şifre ile doğrular."""
    if not hashed_password or not plain_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Şifre doğrulama hatası.", exc_info=True)
        return False

def get_password_hash(password):
    """Düz metin şifreyi hash'ler."""
    return pwd_context.hash(password)

def is_password_strong(password):
    """Şifrenin temel karmaşıklık kurallarına uyup uymadığını kontrol eder."""
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalıdır."
    if not re.search(r"[A-Z]", password):
        return False, "Şifre en az bir büyük harf içermelidir."
    if not re.search(r"[a-z]", password):
        return False, "Şifre en az bir küçük harf içermelidir."
    if not re.search(r"[0-9]", password):
        return False, "Şifre en az bir rakam içermelidir."
    return True, "Şifre güçlü."

def init_db():
    """Veritabanını ve 'users' tablosunu başlatır (eğer yoksa)."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Kullanıcı bilgilerini saklamak için tablo oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)
        conn.commit()
        logger.info("Veritabanı ve 'users' tablosu başarıyla başlatıldı veya zaten mevcut.")
    except sqlite3.Error as e:
        logger.error(f"Veritabanı hatası (init_db): {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def add_user(username, password):
    """Veritabanına yeni bir kullanıcı ekler (güçlü şifre kontrolü ile)."""
    if not username or not password:
        logger.warning("Kullanıcı ekleme denemesi: Kullanıcı adı veya şifre boş.")
        return False, "Kullanıcı adı veya şifre boş olamaz."

    is_strong, message = is_password_strong(password)
    if not is_strong:
        logger.warning(f"Başarısız kayıt denemesi ({username}): {message}")
        return False, message

    hashed_password = get_password_hash(password)
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        logger.info(f"Kullanıcı '{username}' başarıyla eklendi.")
        return True, "Kayıt başarılı!"
    except sqlite3.IntegrityError: # Kullanıcı adı zaten varsa
        message = f"Kullanıcı adı '{username}' zaten mevcut."
        logger.warning(f"Başarısız kayıt denemesi: {message}")
        return False, message
    except sqlite3.Error as e:
        message = "Bir veritabanı hatası oluştu."
        logger.error(f"Veritabanı hatası (kullanıcı ekleme).", exc_info=True)
        return False, message
    finally:
        if conn:
            conn.close()

def get_user(username):
    """Kullanıcı adına göre kullanıcı bilgilerini (id, username, hashed_password) getirir."""
    conn = None
    user = None
    if not username:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Sonuçları sözlük gibi erişilebilir yap
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Veritabanı hatası (kullanıcı alma).", exc_info=True)
    finally:
        if conn:
            conn.close()
    logger.debug(f"Kullanıcı sorgulandı: {username}, Sonuç: {'Bulundu' if user else 'Bulunamadı'}")
    return dict(user) if user else None