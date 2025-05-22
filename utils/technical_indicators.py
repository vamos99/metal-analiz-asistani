# utils/technical_indicators.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_sma(data: pd.Series, window: int) -> pd.Series | None:
    """Verilen Pandas Serisi için Basit Hareketli Ortalama (SMA) hesaplar."""
    if data is None or len(data) < window:
        logger.warning(f"SMA({window}) için yetersiz veri. Gerekli: {window}, Mevcut: {len(data) if data is not None else 0}")
        return None
    try:
        sma = data.rolling(window=window).mean()
        logger.info(f"{window} günlük SMA başarıyla hesaplandı.")
        return sma
    except Exception as e:
        logger.error(f"{window} günlük SMA hesaplanırken hata.", exc_info=True)
        return None