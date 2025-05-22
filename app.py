# app.py
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
from typing import Dict, Any

from utils.logger_config import setup_logging

# Loglamayı başlat
try:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("app.py başlatılıyor...")
except Exception as e:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    st.error(f"Loglama başlatılamadı: {e}. Standart loglama kullanılıyor.")
    logger.warning("Standart loglama kullanılıyor (hata nedeniyle).")

# Gerekli modülleri import et
try:
    from utils.data_loader import get_metal_data
    from utils.plot_generator import create_price_chart, create_comparison_chart
    from utils.ml_predictor import prepare_data_for_ml, train_simple_model, predict_future_trend
    from utils.rag_retriever import get_rag_content
    from utils.gemini_handler import generate_ai_comment, generate_comparison_comment, generate_chat_response
    from utils.auth import init_db, add_user, get_user, verify_password
    from utils.technical_indicators import calculate_sma
    from ui_components.sidebar import display_login_signup, display_user_profile, display_metal_selection, display_ml_prediction
    from ui_components.main_page import display_single_metal_analysis, display_comparison_section
except ImportError as e:
    logger.critical(f"Kritik modül import hatası: {e}. Uygulama durduruluyor.", exc_info=True)
    st.error(f"Uygulama başlatılamadı! Gerekli modüller yüklenemedi: {e}")
    st.stop()

# Ortam değişkenlerini yükle ve veritabanını başlat
try:
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        logger.critical("GEMINI_API_KEY ortam değişkeni ayarlanmamış! AI özellikleri çalışmayacak.")
        st.error("Kritik Yapılandırma Hatası: GEMINI_API_KEY eksik. AI özellikleri devre dışı.")
    init_db()
except Exception as e:
    logger.error(f"Başlangıç sırasında hata (dotenv/veritabanı): {e}", exc_info=True)
    st.error(f"Uygulama başlangıç hatası: {e}")
    st.stop()

# Streamlit sayfa yapılandırması ve özel CSS
st.set_page_config(page_title="Metal Analiz Asistanı", page_icon="🪙", layout="wide")
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; padding-left: 5rem; padding-right: 5rem; }
    [data-testid="stSidebar"] { width: 380px !important; }
    .stButton>button { border-radius: 8px; border: 1px solid #cccccc; }
    .stButton>button:hover { border: 1px solid #007bff; color: #007bff; }
    .stMetric > label { font-size: 0.95rem !important; color: #4f4f4f; }
    .stMetric > div > div { font-size: 1.1rem !important; }
    h1, h2, h3 { padding-bottom: 0.2rem !important; margin-bottom: 0.5rem !important; }
    .streamlit-expanderHeader { font-size: 1.05rem !important; }
    [data-testid="stChatMessage"] { margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

def initialize_constants_in_state():
    """Uygulama sabitlerini ve cache'li fonksiyonları session state'e yükler."""
    if 'METALS_VAR' not in st.session_state:
        logger.info("Sabitler ve cache'li fonksiyonlar session state'e ilk kez yükleniyor.")
        st.session_state.METALS_VAR = {
            "Altın": "GC=F", "Gümüş": "SI=F", "Platin": "PL=F",
            "Paladyum": "PA=F", "Bakır": "HG=F"
        }
        st.session_state.PERIODS_VAR = {
            "1 Ay": "1mo", "3 Ay": "3mo", "6 Ay": "6mo",
            "1 Yıl": "1y", "5 Yıl": "5y", "Tümü": "max"
        }
        st.session_state.TICKER_TO_NAME_VAR = {v: k for k, v in st.session_state.METALS_VAR.items()}
        st.session_state.ML_DATA_PERIOD_VAR = "5y" # ML için kullanılacak veri periyodu
        st.session_state.LAG_DAYS_VAR = 7 # ML için gecikme gün sayısı
        st.session_state.PREDICTION_DAYS_VAR = 5 # ML tahmin gün sayısı
        st.session_state.PRICE_RANGE_PERCENTAGE_VAR = 0.015 # ML trend belirleme eşiği (kullanılmıyor olabilir, ml_predictor'daki geçerli)

        # AI yorumlama personaları
        st.session_state.PERSONAS_CONFIG_VAR = {
             "wall_street_analyst": {
                "name": "Kıdemli Wall Street Analisti",
                "prompt": "Sen 25+ yıllık Wall Street deneyimine sahip, büyük yatırım fonları için çalışmış, makroekonomik analiz, temel değerleme ve risk yönetimi konularında uzman kıdemli bir analistsin. Yorumlarında küresel ekonomik göstergelere (faiz oranları, enflasyon, GSYH büyümesi, jeopolitik riskler), sektör dinamiklerine ve şirketin/metalin temel değerine odaklanırsın. Sağlanan RAG bilgisini ve uygulama verilerini bu çerçevede değerlendirirsin. Dilin profesyonel, kendinden emin ama ölçülüdür. Kesin yatırım tavsiyesinden kaçınır, potansiyel senaryoları ve riskleri vurgularsın.",
                "temperature": 0.15
            },
            "gold_strategist": {
                "name": "Altın Stratejisti",
                "prompt": "Sen özellikle Altın piyasası üzerine uzmanlaşmış bir stratejistsin. Altının parasal rolünü (güvenli liman, enflasyon koruması), merkez bankası politikalarını, jeopolitik gelişmeleri, fiziki talep ve arz dinamiklerini (RAG bilgisinden yararlanarak) yakından takip edersin. Yorumlarında sağlanan Altın verilerini (fiyat, tahmin vb.) bu özel perspektiften değerlendirirsin. Dilin net, odaklı ve genellikle altına yönelik uzun vadeli bir bakış açısı içerir, ancak kısa vadeli risklere de değinirsin.",
                "temperature": 0.3
            },
            "industrial_metals_trader": {
                "name": "Endüstriyel Metal Traderı",
                "prompt": "Sen başta Bakır olmak üzere endüstriyel metallerin alım satımı konusunda tecrübeli bir tradersın. Küresel sanayi üretimi (özellikle Çin PMI verileri), inşaat sektörü trendleri, LME stok seviyeleri, madencilik arzı/kesintileri gibi faktörlere odaklanırsın. Sağlanan metal (özellikle Bakır ise) verilerini ve RAG bilgisini bu arz/talep dinamikleri açısından yorumlarsın. Teknik göstergelere (varsa SMA) ve kısa/orta vadeli fiyat hareketlerine dikkat edersin. Dilin daha doğrudan, hızlı ve piyasa jargonu içerebilir.",
                "temperature": 0.45
            }
        }

        # Veri yükleme ve hesaplama fonksiyonlarını cache ile state'e ata
        @st.cache_data(ttl=1800) # 30 dakika cache
        def load_data_state(ticker, period):
            logger.info(f"Cache'li fonksiyon çağrıldı: load_data_state({ticker}, {period})")
            df = get_metal_data(ticker, period=period)
            if df is not None and not df.empty:
                 df['last_updated'] = pd.Timestamp.now(tz='UTC') # Verinin ne zaman çekildiğini ekle
            return df

        @st.cache_data(ttl=3600) # 1 saat cache
        def calculate_stats_state(data):
            logger.info("Cache'li fonksiyon çağrıldı: calculate_stats_state")
            if data is None or data.empty or 'Close' not in data.columns:
                 return None
            close = data['Close']
            stats = {'mean': close.mean(), 'max': close.max(), 'min': close.min(), 'std': close.std()}
            if not close.empty:
                stats['last'] = close.iloc[-1]
            return stats

        @st.cache_resource(ttl=86400) # 1 gün cache (model eğitimi pahalı olabilir)
        def get_trained_model_state(ticker, period, lag_days, predict_days):
            logger.info(f"Cache'li fonksiyon çağrıldı: get_trained_model_state({ticker}, {period})")
            _ml_data_raw = load_data_state(ticker, period)
            _model = None
            if _ml_data_raw is not None and len(_ml_data_raw) >= lag_days + predict_days + 30: # Yeterli veri var mı?
                 _df_ml = prepare_data_for_ml(_ml_data_raw, lag_days=lag_days, predict_days=predict_days)
                 if not _df_ml.empty:
                     _model = train_simple_model(_df_ml)
                 else:
                     logger.warning(f"Model eğitimi için ML verisi hazırlanamadı (NaN sonrası boş): {ticker}")
            else:
                 logger.warning(f"Model eğitimi için yetersiz veri: {ticker} (Mevcut: {len(_ml_data_raw) if _ml_data_raw is not None else 0})")
            return _model, _ml_data_raw # Modeli ve kullanılan ham veriyi döndür

        st.session_state.load_data_func = load_data_state
        st.session_state.calculate_stats_func = calculate_stats_state
        st.session_state.get_trained_model_func = get_trained_model_state
        logger.info("Sabitler ve cache'li fonksiyonlar session state'e başarıyla yüklendi.")

def initialize_session_state():
    """Gerekli session state anahtarlarını varsayılan değerlerle başlatır."""
    if 'METALS_VAR' not in st.session_state:
        initialize_constants_in_state() # Sabitleri yükle

    # Oturum durumu değişkenleri
    st.session_state.setdefault('logged_in', False)
    st.session_state.setdefault('username', None)
    st.session_state.setdefault('user_id', None)
    st.session_state.setdefault('selected_metal_name', list(st.session_state.METALS_VAR.keys())[0]) # Varsayılan metal: Altın
    st.session_state.setdefault('selected_period_name', list(st.session_state.PERIODS_VAR.keys())[3]) # Varsayılan periyot: 1 Yıl
    st.session_state.setdefault('current_persona_key', list(st.session_state.PERSONAS_CONFIG_VAR.keys())[0]) # Varsayılan persona
    st.session_state.setdefault('show_sma', False)
    st.session_state.setdefault('sma_window', 20)
    st.session_state.setdefault('prediction_result', None) # ML tahmin sonucu
    st.session_state.setdefault('predict_button_pressed', False)
    st.session_state.setdefault('chat_history', []) # Sohbet geçmişi
    st.session_state.setdefault('active_tab', "Tek Metal Analizi") # Aktif sekme (kullanılmıyor olabilir)

initialize_session_state() # Uygulama her çalıştığında state'i kontrol et/başlat

def get_current_context(selected_metal_name: str, selected_period_name: str, selected_ticker: str, selected_period_code: str) -> Dict[str, Any]:
    """ AI fonksiyonları ve sohbet için mevcut uygulama bağlamını (veriler, ayarlar) toplar. """
    logger.debug(f"Context oluşturuluyor: Metal={selected_metal_name}, Periyot={selected_period_name}")
    context: Dict[str, Any] = {
        "selected_metal": selected_metal_name,
        "selected_period_name": selected_period_name,
        "selected_ticker": selected_ticker,
        "selected_period_code": selected_period_code,
        "current_price": None,
        "stats": None,
        "prediction": st.session_state.get('prediction_result'),
        "rag_content": get_rag_content(selected_metal_name), # İlgili metalin RAG içeriği
        "sma_info": None,
        "context_summary_string": "Bağlam özeti oluşturulamadı." # AI'a gönderilecek özet metin
    }

    if st.session_state.get('show_sma'):
        context["sma_info"] = {
            "active": True,
            "window": st.session_state.get('sma_window', 20)
        }

    try:
        # Cache'li fonksiyonlarla veriyi ve istatistikleri al
        graph_data = st.session_state.load_data_func(selected_ticker, selected_period_code)
        if graph_data is not None and not graph_data.empty:
            if 'Close' in graph_data.columns and not graph_data['Close'].empty:
                 context["current_price"] = graph_data['Close'].iloc[-1]
            context["stats"] = st.session_state.calculate_stats_func(graph_data)
    except Exception as data_err:
         logger.error(f"Context oluştururken veri alma/işleme hatası: {data_err}", exc_info=True)

    # AI'a gönderilecek özet metni oluştur
    context_str_parts = [f"- Seçili Metal: {selected_metal_name} ({selected_ticker})",
                         f"- Seçili Analiz Periyodu: {selected_period_name}"]
    if context["current_price"] is not None:
        context_str_parts.append(f"- Son Fiyat (Grafikten): {context['current_price']:.2f}")
    if context["stats"]:
        mean_p = context['stats'].get('mean', 0)
        std_p = context['stats'].get('std', 0)
        context_str_parts.append(f"- Dönem İstatistikleri (Ort: {mean_p:.2f}, StdSapma: {std_p:.2f})")
    if context["prediction"]:
        pred_days = context['prediction'].get('predict_days', '?')
        trend = context['prediction'].get('trend', 'Bilinmiyor')
        context_str_parts.append(f"- Son {pred_days} Günlük ML Tahmini: {trend} (Basit model, garanti yok)")
    else:
        context_str_parts.append("- ML Tahmini: Yok veya yapılmadı")
    if context["sma_info"]:
        context_str_parts.append(f"- Aktif Gösterge: SMA({context['sma_info']['window']})")

    if len(context_str_parts) > 2: # En az metal ve periyot dışında bilgi varsa
        context["context_summary_string"] = "\n".join(context_str_parts)
    else:
        context["context_summary_string"] = "Uygulama arayüzünde henüz yeterli analiz verisi yok."

    logger.debug(f"Oluşturulan Context Özeti:\n{context['context_summary_string']}")
    return context

def display_ai_features_sidebar(context: Dict[str, Any]):
    """Kenar çubuğunda AI yorumlama (persona seçimi, yorum alma) bölümünü yönetir."""
    st.sidebar.divider()
    st.sidebar.subheader("🤖 Yapay Zeka Yorumlama")
    st.sidebar.markdown("**Piyasa Yorumu**")

    available_personas = st.session_state.PERSONAS_CONFIG_VAR
    persona_display_names = [config.get("name", k) for k, config in available_personas.items()]
    persona_keys = list(available_personas.keys())

    # Seçili personayı state'den al, yoksa varsayılanı kullan
    default_index = 0
    current_key_in_state = st.session_state.get('current_persona_key')
    if current_key_in_state and current_key_in_state in persona_keys:
        try: default_index = persona_keys.index(current_key_in_state)
        except ValueError: default_index = 0

    selected_persona_display_name = st.sidebar.selectbox(
        "Yorumlama Personası Seç:",
        persona_display_names,
        index=default_index,
        key="persona_select_sb",
        help="Farklı bakış açıları için yorum yapacak kişiliği seçin."
    )

    # Kullanıcı persona değiştirirse state'i güncelle
    selected_persona_key = None
    if selected_persona_display_name and persona_keys:
        try:
            selected_persona_key = persona_keys[persona_display_names.index(selected_persona_display_name)]
            if st.session_state.current_persona_key != selected_persona_key:
                st.session_state.current_persona_key = selected_persona_key
                logger.info(f"Persona değiştirildi: {selected_persona_key}")
                # Persona değişince eski yorumu temizle (isteğe bağlı)
                if f'last_comment_{selected_persona_key}' in st.session_state:
                    del st.session_state[f'last_comment_{selected_persona_key}']
        except (ValueError, IndexError):
            logger.error(f"Seçilen persona ismi '{selected_persona_display_name}' için anahtar bulunamadı!")
            selected_persona_key = persona_keys[0] # Hata durumunda ilk personaya dön
            st.session_state.current_persona_key = selected_persona_key
    elif not persona_keys:
         st.sidebar.warning("Yorumlama personaları yüklenemedi.")
         st.session_state.current_persona_key = None

    active_persona_key = st.session_state.get('current_persona_key')
    if active_persona_key:
        active_persona_name = available_personas.get(active_persona_key, {}).get('name', active_persona_key)
        # Yorum alma butonu
        if st.sidebar.button("💬 Yorum Al", key="ai_comment_button_sb", use_container_width=True):
            with st.spinner(f"{active_persona_name} yorumluyor..."):
                try:
                    ai_comment = generate_ai_comment(
                        context,
                        active_persona_key,
                        st.session_state.PERSONAS_CONFIG_VAR
                    )
                    # Yorumu state'e kaydet (persona'ya özel anahtarla)
                    st.session_state[f'last_comment_{active_persona_key}'] = ai_comment
                except Exception as comment_err:
                     logger.error(f"AI yorumu üretilirken hata: {comment_err}", exc_info=True)
                     st.error(f"Yorum alınırken bir hata oluştu: {comment_err}")
                     if f'last_comment_{active_persona_key}' in st.session_state:
                         del st.session_state[f'last_comment_{active_persona_key}']

        # İlgili persona için son yorum varsa göster
        last_comment_key = f'last_comment_{active_persona_key}'
        if last_comment_key in st.session_state:
            with st.sidebar.expander(f"{active_persona_name} Yorumu", expanded=True):
                st.markdown(st.session_state[last_comment_key])

def display_simple_chat(current_context: Dict[str, Any]):
    """Ana sayfada AI ile basit sohbet bölümünü gösterir."""
    st.header("💬 AI Analiz Sohbeti")
    st.caption("Seçili metal, piyasa durumu veya genel finans konuları hakkında sorular sorun.")

    # Sohbet geçmişini göster
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Kullanıcıdan yeni mesaj al
    if prompt := st.chat_input("Altının genel durumu hakkında ne düşünüyorsun?"):
        # Kullanıcı mesajını geçmişe ve arayüze ekle
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
             st.markdown(prompt)

        # AI yanıtını oluştur ve göster
        with st.chat_message("assistant"):
            with st.spinner("AI yanıtı oluşturuluyor..."):
                try:
                    # Yanıt üretmeden önce context'i tekrar al (state değişmiş olabilir)
                    updated_context = get_current_context(
                        st.session_state.selected_metal_name,
                        st.session_state.selected_period_name,
                        st.session_state.METALS_VAR.get(st.session_state.selected_metal_name),
                        st.session_state.PERIODS_VAR.get(st.session_state.selected_period_name)
                    )

                    ai_response = generate_chat_response(
                        user_query=prompt,
                        chat_history=st.session_state.chat_history[:-1], # Son kullanıcı mesajı hariç geçmiş
                        context=updated_context
                    )
                    st.markdown(ai_response)
                except Exception as chat_err:
                     logger.error(f"Sohbet yanıtı üretilirken hata: {chat_err}", exc_info=True)
                     error_msg = f"Yanıt alınırken bir sorun oluştu: {chat_err}"
                     st.error(error_msg)
                     ai_response = error_msg # Hata mesajını da geçmişe ekle

        # AI yanıtını geçmişe ekle
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        # st.rerun() # Genellikle chat_input sonrası otomatik rerun olur, manuel gerekmez

def main():
    """Ana Streamlit uygulama akışını yönetir."""
    st.sidebar.title("Kontrol Paneli")

    # Kenar çubuğundan metal ve periyot seçimlerini al
    selected_metal_name, selected_period_name = display_metal_selection()
    selected_ticker = st.session_state.METALS_VAR.get(selected_metal_name)
    selected_period_code = st.session_state.PERIODS_VAR.get(selected_period_name)

    if not selected_ticker or not selected_period_code:
        st.error("Metal veya periyot seçimiyle ilgili bir sorun var.")
        logger.error(f"Geçersiz seçim: Metal='{selected_metal_name}', Periyot='{selected_period_name}'")
        st.stop()

    # Giriş/Kayıt veya Kullanıcı Profili bölümünü göster
    if not st.session_state.logged_in:
        display_login_signup()
    else:
        display_user_profile()

    # ML Tahmin bölümünü göster
    display_ml_prediction(selected_ticker, selected_metal_name)

    # Güncel uygulama bağlamını oluştur
    current_context = get_current_context(selected_metal_name, selected_period_name, selected_ticker, selected_period_code)

    # AI Yorumlama bölümünü göster
    display_ai_features_sidebar(current_context)

    # Ana sayfa başlığı
    st.title(f"🪙 Metal Analiz Asistanı")

    # Ana içerik sekmeleri
    tab1, tab2, tab3 = st.tabs(["📊 Tek Metal Analizi", "🆚 Karşılaştırma", "💬 AI Sohbet"])

    with tab1:
        # Tek metal analizini göster
        display_single_metal_analysis(selected_ticker, selected_metal_name, selected_period_name, selected_period_code)

    with tab2:
        # Karşılaştırma bölümünü göster
        display_comparison_section(get_current_context) # Context fonksiyonunu geç

    with tab3:
        # Sohbet arayüzünü göster
        display_simple_chat(current_context)

if __name__ == "__main__":
    try:
        main()
    except Exception as main_err: # Beklenmedik hataları yakala
        logger.critical(f"Ana uygulama döngüsünde yakalanmayan kritik hata!", exc_info=True)
        st.error(f"Uygulamada beklenmedik bir sorun oluştu. Lütfen sayfayı yenileyin veya daha sonra tekrar deneyin.")
        st.exception(main_err)