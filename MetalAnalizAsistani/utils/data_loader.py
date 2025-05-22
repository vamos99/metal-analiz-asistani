# utils/data_loader.py
import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_metal_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | None:
    """Belirtilen ticker için yfinance'dan geçmiş fiyat verilerini çeker."""
    try:
        logger.info(f"{ticker} için yfinance verisi çekiliyor (Period: {period}, Interval: {interval}).")
        metal = yf.Ticker(ticker)
        history = metal.history(period=period, interval=interval)
        if history.empty:
            logger.warning(f"{ticker} için veri bulunamadı (Period: {period}).")
            return None
        # Sadece gerekli sütunları al
        history = history[['Open', 'High', 'Low', 'Close', 'Volume']]
        return history
    except Exception as e:
        logger.error(f"{ticker} için veri çekilirken sorun oluştu.", exc_info=True)
        return None