import logging
import logging.handlers
import os

LOG_DIR = "logs"
LOG_FILENAME = "app.log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)

MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

def setup_logging():
    """Uygulama için loglama ayarlarını yapar."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        logger = logging.getLogger()

        if logger.hasHandlers():
            logger.debug("Loglama zaten yapılandırılmış.")
            return

        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Konsola sadece WARNING ve üzeri logları yazdır
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Dosyaya WARNING ve üzerini yaz, rotasyon uygula
        fh = logging.handlers.RotatingFileHandler(
            LOG_PATH,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        fh.setLevel(logging.WARNING)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logging.info("Loglama başarıyla başlatıldı (Dosya/Konsol Seviyesi: WARNING).")

    except Exception as e:
        print(f"!!! LOGLAMA BAŞLATILAMADI: {e} !!!")
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - [%(levelname)s] - %(message)s'
        )
        logging.error("Standart loglama kullanılıyor (yapılandırma hatası nedeniyle).")