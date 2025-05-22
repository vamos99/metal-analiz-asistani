import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import logging

logger = logging.getLogger(__name__)

def create_price_chart(df: pd.DataFrame, metal_name: str, sma_series: pd.Series | None = None, sma_window: int | None = None) -> go.Figure:
    """ Tek metal için fiyat grafiği oluşturur, opsiyonel SMA ekler. """
    logger.info(f"'{metal_name}' için fiyat grafiği (SMA: {sma_window if sma_window else 'Yok'}).")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=f'{metal_name} Kapanış'))
    if sma_series is not None and sma_window is not None:
        fig.add_trace(go.Scatter(x=sma_series.index, y=sma_series, mode='lines', name=f'SMA({sma_window})', line=dict(dash='dash', width=1.5, color='orange')))
    fig.update_layout(
        title=f'{metal_name} Fiyat Grafiği' + (f' ve SMA({sma_window})' if sma_window else ''),
        xaxis_title='Tarih',
        yaxis_title='Fiyat (USD)',
        xaxis_rangeslider_visible=False,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig

def create_comparison_chart(normalized_df: pd.DataFrame, period_name: str) -> go.Figure:
    """ Çoklu metal karşılaştırma grafiği oluşturur (normalize edilmiş veriye göre). """
    logger.info(f"'{period_name}' periyodu için karşılaştırma grafiği. Metaller: {list(normalized_df.columns)}")
    fig = go.Figure()
    colors = px.colors.qualitative.Vivid # Farklı renkler kullan
    num_metals = len(normalized_df.columns)
    for i, metal_name in enumerate(normalized_df.columns):
        fig.add_trace(go.Scatter(
            x=normalized_df.index,
            y=normalized_df[metal_name],
            mode='lines',
            name=metal_name,
            line=dict(color=colors[i % len(colors)]) # Renkleri döngüsel kullan
        ))
    # Başlangıç seviyesini gösteren çizgi
    fig.add_hline(y=100, line_dash="dash", line_color="grey", annotation_text="Başlangıç (100)", annotation_position="bottom right")
    fig.update_layout(
        title=f'Metal Performans Karşılaştırması ({period_name})',
        xaxis_title='Tarih',
        yaxis_title='Normalize Performans (Başlangıç = 100)',
        hovermode="x unified", # Fare ile üzerine gelince tüm verileri göster
        legend_title_text='Metaller'
    )
    return fig