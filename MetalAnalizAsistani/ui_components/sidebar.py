# ui_components/sidebar.py
import streamlit as st
import logging
from utils.auth import get_user, verify_password, add_user
from utils.ml_predictor import predict_future_trend

logger = logging.getLogger(__name__)

def display_login_signup():
    """Giriş ve Kayıt sekmelerini gösterir."""
    login_tab, signup_tab = st.sidebar.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
    with login_tab:
        st.subheader("Giriş Yap")
        with st.form("login_form"):
            login_username = st.text_input("Kullanıcı Adı", key="login_user_sb")
            login_password = st.text_input("Şifre", type="password", key="login_pass_sb")
            login_submitted = st.form_submit_button("Giriş Yap")
            if login_submitted:
                if not login_username or not login_password:
                    st.warning("Kullanıcı adı ve şifre boş olamaz.")
                else:
                    user = get_user(login_username)
                    if user and verify_password(login_password, user.get('hashed_password')):
                        logger.info(f"Kullanıcı '{login_username}' giriş yaptı.")
                        st.session_state.logged_in = True
                        st.session_state.username = user['username']
                        st.session_state.user_id = user['id']
                        st.session_state.selected_metal_name = list(st.session_state.METALS_VAR.keys())[0]
                        st.session_state.prediction_result = None
                        # Giriş yapınca sayfayı yenilemek state'in oturmasını sağlar
                        st.rerun()
                    else:
                        logger.warning(f"Başarısız giriş denemesi: {login_username}")
                        st.error("Geçersiz kullanıcı adı veya şifre.")
    with signup_tab:
        st.subheader("Yeni Kullanıcı Kaydı")
        with st.form("signup_form"):
            signup_username = st.text_input("Kullanıcı Adı", key="signup_user_sb")
            signup_password = st.text_input("Şifre", type="password", key="signup_pass_sb")
            signup_password_confirm = st.text_input("Şifre Tekrar", type="password", key="signup_pass_confirm_sb")
            signup_submitted = st.form_submit_button("Kayıt Ol")
            if signup_submitted:
                if not signup_username or not signup_password:
                    st.warning("Kullanıcı adı ve şifre boş olamaz.")
                elif signup_password != signup_password_confirm:
                    st.error("Şifreler uyuşmuyor.")
                else:
                    success, message = add_user(signup_username, signup_password)
                    if success:
                        st.success(message + " Şimdi giriş yapabilirsiniz.")
                    else:
                        st.error(message)


def display_user_profile():
    """Giriş yapmış kullanıcı bilgilerini ve çıkış butonunu gösterir."""
    st.sidebar.success(f"Hoş geldin, {st.session_state.username}! 👋")
    st.sidebar.divider()

    # Favoriler bölümü kaldırıldı.

    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        logger.info(f"Kullanıcı '{st.session_state.username}' çıkış yapıyor.")
        username_backup = st.session_state.username
        # Oturumla ilgili state değişkenlerini temizle
        protected_keys = ['METALS_VAR', 'PERIODS_VAR', 'TICKER_TO_NAME_VAR', 'ML_DATA_PERIOD_VAR',
                          'LAG_DAYS_VAR', 'PREDICTION_DAYS_VAR', 'PRICE_RANGE_PERCENTAGE_VAR',
                          'PERSONAS_CONFIG_VAR', 'load_data_func', 'calculate_stats_func',
                          'get_trained_model_func', 'chat_history'] # agent_executor kaldırıldı, chat_history korundu
        keys_to_delete = [k for k in st.session_state.keys() if k not in protected_keys]
        for key in keys_to_delete:
            del st.session_state[key]

        # Oturum durumunu sıfırla ve sayfayı yenile
        st.session_state.logged_in = False
        st.session_state.setdefault('selected_metal_name', list(st.session_state.METALS_VAR.keys())[0])
        # Çıkış yapınca sohbet geçmişini de temizleyelim
        st.session_state.chat_history = []
        logger.info(f"Oturum temizlendi ({username_backup}).")
        st.rerun()


def display_metal_selection():
    """Kenar çubuğunda metal, periyot ve SMA seçimini yönetir."""
    st.sidebar.header("Tek Metal Analizi")
    try:
        current_metal_index = list(st.session_state.METALS_VAR.keys()).index(st.session_state.selected_metal_name)
    except (ValueError, KeyError):
        st.session_state.selected_metal_name = list(st.session_state.METALS_VAR.keys())[0]
        current_metal_index = 0

    selected_metal_name_sb = st.sidebar.selectbox(
        "Metal Seçin:",
        list(st.session_state.METALS_VAR.keys()),
        key="metal_select_sb",
        index=current_metal_index
    )
    if selected_metal_name_sb != st.session_state.selected_metal_name:
        st.session_state.selected_metal_name = selected_metal_name_sb
        st.session_state.prediction_result = None
        logger.info(f"Metal seçimi değişti: {selected_metal_name_sb}")
        st.rerun()

    current_period_name = st.session_state.get('selected_period_name', list(st.session_state.PERIODS_VAR.keys())[3])
    try:
         current_period_index = list(st.session_state.PERIODS_VAR.keys()).index(current_period_name)
    except ValueError:
         current_period_index = 3

    selected_period_name = st.sidebar.selectbox(
        "Grafik Periyodu Seçin:",
        list(st.session_state.PERIODS_VAR.keys()),
        index=current_period_index,
        key="period_select_sb"
    )
    if selected_period_name != st.session_state.get('selected_period_name'):
         st.session_state.selected_period_name = selected_period_name
         logger.info(f"Periyot seçimi değişti: {selected_period_name}")
         st.rerun()

    st.sidebar.subheader("Teknik Gösterge")
    show_sma_checkbox = st.sidebar.checkbox(
        "Hareketli Ort. Göster (SMA)",
        value=st.session_state.get('show_sma', False),
        key="sma_check_sb"
    )
    sma_window_input = st.session_state.get('sma_window', 20)
    if show_sma_checkbox:
        sma_window_input = st.sidebar.number_input(
            "SMA Periyodu (gün):",
            min_value=5,
            max_value=100,
            value=max(5, sma_window_input),
            step=5,
            key="sma_window_sb"
        )

    sma_state_changed = (st.session_state.get('show_sma') != show_sma_checkbox or
                         (show_sma_checkbox and st.session_state.get('sma_window') != sma_window_input))

    st.session_state.show_sma = show_sma_checkbox
    if show_sma_checkbox:
        st.session_state.sma_window = sma_window_input

    if sma_state_changed:
         logger.info(f"SMA ayarı değişti: Göster={show_sma_checkbox}, Pencere={sma_window_input if show_sma_checkbox else 'N/A'}")
         st.rerun()

    return st.session_state.selected_metal_name, st.session_state.selected_period_name


def display_ml_prediction(selected_ticker, selected_metal_name):
    """Kenar çubuğunda ML tahmin bölümünü yönetir."""
    st.sidebar.subheader(f"Gelecek {st.session_state.PREDICTION_DAYS_VAR} Gün İçin Basit Tahmin")
    if st.session_state.logged_in:
        if st.sidebar.button(f"📈 {st.session_state.PREDICTION_DAYS_VAR} Günlük Tahmin Yap", key="predict_button_sb", use_container_width=True):
            st.session_state.predict_button_pressed = True
            with st.spinner(f"{selected_metal_name} için model hazırlanıyor ve tahmin yapılıyor..."):
                try:
                    model, ml_data_raw_for_pred = st.session_state.get_trained_model_func(
                        selected_ticker,
                        st.session_state.ML_DATA_PERIOD_VAR,
                        st.session_state.LAG_DAYS_VAR,
                        st.session_state.PREDICTION_DAYS_VAR
                    )
                    if model and ml_data_raw_for_pred is not None and not ml_data_raw_for_pred.empty:
                        prediction_result = predict_future_trend(
                            model,
                            ml_data_raw_for_pred,
                            lag_days=st.session_state.LAG_DAYS_VAR,
                            predict_days=st.session_state.PREDICTION_DAYS_VAR
                        )
                        st.session_state.prediction_result = prediction_result
                        if not prediction_result:
                             st.sidebar.error("Tahmin verisi oluşturulamadı.")
                             st.session_state.predict_button_pressed = False
                    else:
                        st.session_state.prediction_result = None
                        st.sidebar.warning("Model eğitimi veya tahmin için yeterli veri bulunamadı.")
                        st.session_state.predict_button_pressed = False
                except Exception as pred_err:
                    logger.error(f"ML tahmin sırasında hata oluştu: {pred_err}", exc_info=True)
                    st.session_state.prediction_result = None
                    st.sidebar.error(f"Tahmin sırasında bir hata oluştu: {pred_err}")
                    st.session_state.predict_button_pressed = False

        prediction_result = st.session_state.get('prediction_result')
        if prediction_result:
            pred_price = prediction_result.get("predicted_price")
            trend = prediction_result.get("trend", "Bilinmiyor")
            pred_days = prediction_result.get("predict_days", st.session_state.PREDICTION_DAYS_VAR)
            if pred_price is not None:
                price_range_perc = st.session_state.PRICE_RANGE_PERCENTAGE_VAR
                lower = pred_price * (1 - price_range_perc)
                upper = pred_price * (1 + price_range_perc)
                st.sidebar.metric(label=f"{pred_days} Günlük Eğilim Tahmini", value=trend)
                st.sidebar.markdown(f"**{pred_days}. Gün Tahmini Fiyat Aralığı:**")
                st.sidebar.markdown(f"<span style='color:green;'>{lower:.2f}</span> - <span style='color:red;'>{upper:.2f}</span> USD", unsafe_allow_html=True)
                st.sidebar.caption(f"Merkez Tahmin: {pred_price:.2f} (+/- {price_range_perc*100:.1f}%)")
            else:
                 st.sidebar.warning("Tahmin sonucu alındı ancak fiyat bilgisi eksik.")
                 st.sidebar.metric(label=f"{pred_days} Günlük Eğilim Tahmini", value=trend)

        elif st.session_state.get('predict_button_pressed'):
             st.sidebar.error("Tahmin işlemi başarısız oldu veya sonuç üretilemedi.")
             # Butona basılma durumunu sıfırla ki hata mesajı sürekli görünmesin
             st.session_state.predict_button_pressed = False

    else:
        st.sidebar.info("💡 Fiyat tahmini özelliğini kullanmak için lütfen giriş yapın.")