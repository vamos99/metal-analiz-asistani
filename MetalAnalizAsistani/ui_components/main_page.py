# ui_components/main_page.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
from utils.plot_generator import create_price_chart, create_comparison_chart
from utils.rag_retriever import get_rag_content
from utils.technical_indicators import calculate_sma
from utils.gemini_handler import generate_comparison_comment

logger = logging.getLogger(__name__)

def display_single_metal_analysis(selected_ticker, selected_metal_name, selected_period_name, selected_period_code):
    """Ana sayfada tek metal analiz bölümünü gösterir."""
    st.header(f"📊 {selected_metal_name} Detaylı Analizi")
    st.markdown(f"**Seçili Dönem:** {selected_period_name}")

    # Veri yükleme (cache'li fonksiyon state'den)
    graph_data = st.session_state.load_data_func(selected_ticker, selected_period_code)

    if graph_data is not None and not graph_data.empty:
        # Son güncelleme zamanını al (varsa)
        last_update_time = None
        if 'last_updated' in graph_data.columns:
             # Bazen Timestamp yerine tarih string'i gelebilir, kontrol edelim
             if isinstance(graph_data['last_updated'].iloc[-1], pd.Timestamp):
                 last_update_time = graph_data['last_updated'].iloc[-1].tz_localize(None) # Zaman dilimi bilgisini kaldır
             else:
                 try:
                     # String ise parse etmeyi dene
                     last_update_time = pd.to_datetime(graph_data['last_updated'].iloc[-1]).tz_localize(None)
                 except Exception:
                     logger.warning("last_updated sütunu Timestamp veya parse edilebilir string değil.")


        # SMA verisini hesapla (eğer seçiliyse)
        sma_data = None
        if st.session_state.get('show_sma', False):
            sma_window = st.session_state.get('sma_window', 20)
            if sma_window >= 5:
                sma_data = calculate_sma(graph_data['Close'], sma_window)

        # Fiyat grafiğini oluştur
        price_chart = create_price_chart(
            graph_data,
            selected_metal_name,
            sma_series=sma_data,
            sma_window=sma_window if sma_data is not None else None
        )
        st.plotly_chart(price_chart, use_container_width=True)

        # Veri tazelik bilgisini göster
        if last_update_time:
            try:
                # Zaman farkını hesapla (datetime.now() zaman dilimsiz olmalı)
                time_diff = datetime.now() - last_update_time
                if time_diff < timedelta(hours=1) and time_diff.total_seconds() > 0:
                    update_text = f"yaklaşık {int(time_diff.total_seconds() // 60)} dk önce"
                else:
                    update_text = last_update_time.strftime('%d.%m.%Y %H:%M')
                st.caption(f"📈 Grafik verileri {update_text} itibarıyla günceldir (Önbellekten).")
            except Exception as time_err:
                 logger.error(f"Zaman farkı hesaplama hatası: {time_err}")
                 st.caption("📈 Veri güncelleme zamanı işlenemedi.")
        else:
            st.caption("📈 Veri güncelleme zamanı bilgisi mevcut değil.")

        st.subheader("Özet İstatistikler")
        # İstatistikleri hesapla (cache'li fonksiyon state'den)
        stats = st.session_state.calculate_stats_func(graph_data)
        if stats:
            col1, col2, col3 = st.columns(3)
            col1.metric("Ortalama Fiyat", f"{stats.get('mean', 0):.2f} USD")
            col2.metric("En Yüksek Fiyat", f"{stats.get('max', 0):.2f} USD")
            col3.metric("En Düşük Fiyat", f"{stats.get('min', 0):.2f} USD")
            st.metric("Standart Sapma (Oynaklık)", f"{stats.get('std', 0):.2f}",
                      help="Fiyatların ortalamadan ne kadar saptığını gösteren bir ölçümdür. Yüksek değer, yüksek oynaklık anlamına gelir.")

            # Detaylı rapor indirme butonu
            try:
                report_str = f"--- {selected_metal_name} Analiz Raporu ({datetime.now():%Y-%m-%d %H:%M}) ---\n\n"
                report_str += f"Analiz Dönemi: {selected_period_name}\n\n"
                report_str += "Temel İstatistikler:\n"
                report_str += f"- Ortalama Fiyat: {stats.get('mean', 'N/A'):.2f}\n"
                report_str += f"- En Yüksek Fiyat: {stats.get('max', 'N/A'):.2f}\n"
                report_str += f"- En Düşük Fiyat: {stats.get('min', 'N/A'):.2f}\n"
                report_str += f"- Standart Sapma: {stats.get('std', 'N/A'):.2f}\n\n"

                if st.session_state.get('show_sma'):
                    report_str += f"Teknik Gösterge: Basit Hareketli Ortalama (SMA)\n"
                    report_str += f"- Pencere Boyutu: {st.session_state.get('sma_window', '?')} gün\n\n"

                if st.session_state.get('prediction_result'):
                    pred = st.session_state.prediction_result
                    pred_days = pred.get('predict_days', '?')
                    trend = pred.get('trend', 'Bilinmiyor')
                    pred_price = pred.get('predicted_price')
                    report_str += f"Basit Fiyat Eğilimi Tahmini ({pred_days} Günlük):\n"
                    report_str += f"- Eğilim: {trend}\n"
                    if pred_price is not None:
                        price_range_perc = st.session_state.PRICE_RANGE_PERCENTAGE_VAR
                        lower = pred_price * (1 - price_range_perc)
                        upper = pred_price * (1 + price_range_perc)
                        report_str += f"- Tahmini Fiyat Aralığı: {lower:.2f} - {upper:.2f} USD\n\n"
                    else:
                        report_str += "- Tahmini fiyat aralığı hesaplanamadı.\n\n"
                else:
                     report_str += "Fiyat tahmini yapılmadı veya mevcut değil.\n\n"


                report_str += f"Ek Bilgi ({selected_metal_name} - RAG):\n"
                rag_report_text = get_rag_content(selected_metal_name)
                report_str += rag_report_text if rag_report_text else "- Bu metal için ek bilgi (RAG) bulunamadı.\n"

                report_filename = f"{selected_metal_name.lower().replace(' ', '_')}_analiz_raporu_{datetime.now():%Y%m%d}.txt"
                st.download_button(
                    label="📥 Detaylı Raporu İndir (.txt)",
                    data=report_str.encode('utf-8'),
                    file_name=report_filename,
                    mime='text/plain',
                    use_container_width=True
                )
            except Exception as report_err:
                logger.error(f"Rapor oluşturma veya indirme hatası: {report_err}", exc_info=True)
                st.warning("Rapor oluşturulurken bir sorun oluştu.")
        else:
            st.warning("İstatistikler hesaplanamadı. Veri kaynağını kontrol edin.")

        # Son veri noktalarını gösteren tablo
        st.subheader("Son Fiyat Verileri")
        st.dataframe(graph_data.tail(), use_container_width=True)

    else:
        st.error(f"'{selected_metal_name}' için '{selected_period_name}' dönemine ait veri bulunamadı veya yüklenemedi. Lütfen farklı bir metal veya dönem seçin.")

def display_comparison_section(context_func): # Context oluşturma fonksiyonunu al
    """Ana sayfada metal karşılaştırma bölümünü gösterir ve AI yorumu ekler."""
    st.divider()
    st.header("🆚 Metal Performans Karşılaştırması")

    # Karşılaştırılacak metalleri seçme
    comp_metals_names = st.multiselect(
        "Karşılaştırılacak Metaller:",
        list(st.session_state.METALS_VAR.keys()),
        default=["Altın", "Gümüş"], # Varsayılan seçim
        key="comp_metal_select_main"
    )

    # Karşılaştırma periyodunu seçme (index 3: "1 Yıl")
    comp_period_name = st.selectbox(
        "Karşılaştırma Periyodu:",
        list(st.session_state.PERIODS_VAR.keys()),
        index=3,
        key="comp_period_select_main"
    )
    comp_period_code = st.session_state.PERIODS_VAR[comp_period_name]

    last_day_performance = None
    normalized_df = None
    comparison_data = {} # Verileri tutacak sözlük

    # En az 2 metal seçildiyse devam et
    if len(comp_metals_names) >= 2:
        with st.spinner("Karşılaştırma verileri yükleniyor..."):
            for name in comp_metals_names:
                ticker = st.session_state.METALS_VAR[name]
                # Veriyi cache'li fonksiyonla yükle
                data = st.session_state.load_data_func(ticker, comp_period_code)
                if data is not None and not data.empty and 'Close' in data.columns:
                    comparison_data[name] = data['Close']
                else:
                    st.warning(f"'{name}' için veri bulunamadı veya eksik.")
                    logger.warning(f"Karşılaştırma için {name} ({ticker}) verisi alınamadı (Periyot: {comp_period_code}).")

        # Yeterli sayıda metal için veri bulunduysa grafik oluştur
        if len(comparison_data) >= 2:
            try:
                # Verileri birleştir ve normalleştir
                combined_df = pd.DataFrame(comparison_data)
                # Normalleştirme için ilk geçerli indeksi bul (tüm seriler için ortak)
                first_valid_indices = combined_df.apply(lambda col: col.first_valid_index())
                if first_valid_indices.isnull().any():
                     st.error("Bazı metaller için seçilen dönemde hiç veri bulunamadı.")
                     return # Fonksiyondan çık

                start_index = first_valid_indices.max() # En geç başlayan serinin başlangıcını al

                # Başlangıç indeksinden itibaren verileri al ve doldur (ileriye doğru)
                normalized_df = combined_df.loc[start_index:].ffill()
                # Başlangıç değerine bölerek normalleştir (ilk satırdaki değerler 100 olacak)
                normalized_df = (normalized_df / normalized_df.iloc[0]) * 100
                normalized_df.dropna(axis=1, how='all', inplace=True) # Tamamen NaN olan sütunları kaldır

                if normalized_df.empty or len(normalized_df.columns) < 2:
                     st.error("Normalleştirme sonrası karşılaştırma için yeterli veri kalmadı.")
                     return

                # Karşılaştırma grafiğini oluştur
                comparison_chart = create_comparison_chart(normalized_df, comp_period_name)
                st.plotly_chart(comparison_chart, use_container_width=True)

                # Performans sıralamasını göster
                st.subheader(f"{comp_period_name} Dönemi Performans Sıralaması")
                # Son gündeki performansı al ve sırala
                last_day_performance = normalized_df.iloc[-1].sort_values(ascending=False)
                # DataFrame olarak göster, yüzdelik değişim formatıyla
                st.dataframe(
                    last_day_performance.map(lambda x: f"{x-100:.2f}%"), # Başlangıca göre % değişim
                    use_container_width=True
                )

            except Exception as comp_err:
                logger.error(f"Karşılaştırma grafiği/sıralaması oluşturulurken hata: {comp_err}", exc_info=True)
                st.error(f"Karşılaştırma grafiği oluşturulamadı. Hata: {comp_err}")
                last_day_performance = None # Hata durumunda sıfırla

        # Yeterli veri yoksa uyarı ver
        elif len(comp_metals_names) >= 2:
            st.warning("Karşılaştırma yapmak için en az 2 metalin verisi bulunamadı.")

        # --- Karşılaştırma Yorumu Bölümü ---
        # Sadece geçerli performans verisi varsa AI yorumu iste
        if last_day_performance is not None and not last_day_performance.empty:
            st.subheader("🤖 AI Karşılaştırma Yorumu")

            # Yorum için kullanılacak personayı sidebar'daki seçimden al
            DEFAULT_COMPARISON_PERSONA_KEY = "deneyimli_analist" # Varsayılan
            comp_persona_key = st.session_state.get('current_persona_key', DEFAULT_COMPARISON_PERSONA_KEY)

            # Anahtarın geçerliliğini kontrol et
            if comp_persona_key not in st.session_state.PERSONAS_CONFIG_VAR:
                logger.warning(f"Karşılaştırma yorumu için geçersiz persona anahtarı: '{comp_persona_key}'. Varsayılana ('{DEFAULT_COMPARISON_PERSONA_KEY}') dönülüyor.")
                comp_persona_key = DEFAULT_COMPARISON_PERSONA_KEY

            persona_info = st.session_state.PERSONAS_CONFIG_VAR.get(comp_persona_key, {})
            comp_persona_name = persona_info.get("name", comp_persona_key)

            st.caption(f"Yorumcu Persona: **{comp_persona_name}**")

            # Yorumu state'de saklamak için benzersiz bir anahtar oluştur
            # Sıralanmış metal isimlerini kullanmak, seçilme sırasından bağımsızlık sağlar
            sorted_metal_names = '_'.join(sorted(comp_metals_names))
            comment_state_key = f"comparison_comment_{comp_period_code}_{sorted_metal_names}_{comp_persona_key}"

            # Yorum alma butonu
            if st.button("📊 Karşılaştırma Yorumu İste", key="comp_comment_button_main", use_container_width=True):
                # AI yorumu için gerekli context'i oluştur
                # Not: Karşılaştırma context'i, tek metal context'inden farklı olabilir.
                # Şimdilik RAG özetlerini ve performans verisini kullanıyoruz.
                context = {
                    "compared_metals": comp_metals_names,
                    "performance_data": last_day_performance, # Performans verisini ekle
                    "period_name": comp_period_name,
                    "rag_summaries": {},
                    "persona_key": comp_persona_key
                }

                with st.spinner("Metaller hakkında temel bilgiler (RAG) toplanıyor..."):
                    for name in comp_metals_names:
                        content = get_rag_content(name)
                        # Özeti biraz daha uzun tutabiliriz
                        summary = (content[:250] + "...") if content and len(content) > 250 else content if content else "Bu metal hakkında ek bilgi bulunamadı."
                        context["rag_summaries"][name] = summary

                # Yorumu üret (context tabanlı hale getirilen fonksiyonu çağır)
                with st.spinner(f"{comp_persona_name} karşılaştırmayı yorumluyor..."):
                     try:
                        comp_comment = generate_comparison_comment(
                            context, # Context sözlüğünü geç
                            st.session_state.PERSONAS_CONFIG_VAR
                        )
                        st.session_state[comment_state_key] = comp_comment # Yorumu state'e kaydet
                     except Exception as ai_comp_err:
                         logger.error(f"AI karşılaştırma yorumu üretilirken hata: {ai_comp_err}", exc_info=True)
                         st.error(f"AI yorumu üretilirken bir hata oluştu: {ai_comp_err}")
                         st.session_state[comment_state_key] = "Yorum üretilemedi."


            # Kaydedilmiş son yorumu state'den göster (varsa)
            if comment_state_key in st.session_state:
                with st.expander("AI Karşılaştırma Yorumunu Gör/Gizle", expanded=True):
                    st.info(st.session_state[comment_state_key])

    # En az 2 metal seçilmediyse uyarı ver
    else:
        st.info("📊 Performans karşılaştırması için lütfen yukarıdan en az 2 metal seçin.")