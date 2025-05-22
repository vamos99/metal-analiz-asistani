# utils/ml_predictor.py
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import logging

logger = logging.getLogger(__name__)

PRICE_RANGE_PERCENTAGE_TREND = 0.005

def prepare_data_for_ml(df: pd.DataFrame, lag_days: int = 5, predict_days: int = 5) -> pd.DataFrame:
    if df.empty or 'Close' not in df.columns:
        logger.error("ML Hazırlık: Geçersiz DataFrame.")
        return pd.DataFrame()
    if len(df) < lag_days + predict_days:
        logger.warning(f"ML Hazırlık: Yetersiz veri ({len(df)}/{lag_days+predict_days}).")
        return pd.DataFrame()

    df_ml = df[['Close']].copy()
    df_ml['Target'] = df_ml['Close'].shift(-predict_days)
    for i in range(1, lag_days + 1):
        df_ml[f'Lag_{i}'] = df_ml['Close'].shift(i)

    df_ml.dropna(inplace=True)
    if df_ml.empty:
        logger.warning(f"ML Hazırlık: NaN değerleri kaldırıldıktan sonra veri kalmadı.")
        return pd.DataFrame()

    logger.info(f"ML Veri Hazırlandı. Shape: {df_ml.shape}, Lag: {lag_days}, Predict: {predict_days}")
    return df_ml

def train_simple_model(df_ml: pd.DataFrame) -> LinearRegression | None:
    if df_ml.empty or 'Target' not in df_ml.columns:
        logger.error("Eğitim: Geçersiz veya boş DataFrame.")
        return None
    try:
        X_train = df_ml.drop('Target', axis=1)
        y_train = df_ml['Target']
        if X_train.empty or y_train.empty:
            logger.error("Eğitim: Eğitim seti boş.")
            return None

        model = LinearRegression()
        model.fit(X_train, y_train)
        logger.info(f"Model Eğitildi. Özellikler: {model.n_features_in_} ({list(X_train.columns)})")
        return model
    except Exception as e:
        logger.error(f"Model eğitimi sırasında hata.", exc_info=True)
        return None

def predict_future_trend(model: LinearRegression, current_data: pd.DataFrame, lag_days: int = 5, predict_days: int = 5) -> dict | None:
    if model is None:
        logger.error("Tahmin: Model mevcut değil.")
        return None

    required_data_len = lag_days + 1
    if len(current_data) < required_data_len:
        logger.warning(f"Tahmin: Yetersiz güncel veri ({len(current_data)}/{required_data_len}).")
        return None

    try:
        last_close_price = current_data['Close'].iloc[-1]
        lags = {f'Lag_{i}': current_data['Close'].iloc[-(i + 1)] for i in range(1, lag_days + 1)}
        features_dict = {'Close': last_close_price, **lags}
        feature_names_in_order = ['Close'] + [f'Lag_{i}' for i in range(1, lag_days + 1)]
        features_df_for_prediction = pd.DataFrame([features_dict], columns=feature_names_in_order)

        logger.info(f"Tahmin için giriş verisi:\n{features_df_for_prediction}")

        try:
             expected_features = list(model.feature_names_in_)
             if list(features_df_for_prediction.columns) != expected_features:
                  logger.warning(f"Tahmin özellik sırası uyuşmazlığı. Yeniden sıralanıyor.")
                  features_df_for_prediction = features_df_for_prediction[expected_features]
        except AttributeError:
             logger.warning("Model özellik adı kontrolü atlandı ('feature_names_in_').")

        predicted_future_price = model.predict(features_df_for_prediction)[0]

        trend = "Nötr"
        if predicted_future_price > last_close_price * (1 + PRICE_RANGE_PERCENTAGE_TREND):
            trend = "Yükseliş"
        elif predicted_future_price < last_close_price * (1 - PRICE_RANGE_PERCENTAGE_TREND):
            trend = "Düşüş"

        logger.info(f"Son Kapanış: {last_close_price:.2f}, {predict_days} Gün Sonrası Tahmin: {predicted_future_price:.2f}, Eğilim: {trend}")
        return {"predicted_price": predicted_future_price, "trend": trend, "predict_days": predict_days}
    except IndexError as ie:
        logger.error(f"Tahmin: Veri indeksi hatası (yetersiz veri olabilir).", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Tahmin sırasında hata.", exc_info=True)
        return None