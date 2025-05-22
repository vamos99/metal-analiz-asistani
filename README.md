# 🏆 Metal Analiz Asistanı

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.31.0-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Metal piyasalarını analiz eden, yapay zeka destekli modern web uygulaması.

[Özellikler](#özellikler) • [Kurulum](#kurulum) • [Kullanım](#kullanım) • [Teknolojiler](#teknolojiler)

</div>

## ✨ Özellikler

### 📊 Tek Metal Analizi
- Detaylı fiyat grafiği ve istatistikler
- SMA (Basit Hareketli Ortalama) göstergesi
- PDF/Excel formatında rapor indirme
- Temel teknik analiz metrikleri

### 🆚 Metal Karşılaştırması
- Normalize edilmiş performans grafiği
- Otomatik performans sıralaması
- Yapay zeka destekli karşılaştırma yorumu
- Özelleştirilebilir zaman aralığı

### 🤖 Yapay Zeka Özellikleri
- Farklı piyasa uzmanı personalleri
- Gerçek zamanlı piyasa yorumları
- Sohbet tabanlı analiz desteği
- RAG (Retrieval Augmented Generation) entegrasyonu

### 🔮 ML Tahminleri
- Basit trend tahmini
- Fiyat aralığı öngörüsü
- Performans metrikleri
- Otomatik model güncelleme

## 🚀 Kurulum

1. **Python Kurulumu**
   ```bash
   # Python 3.8 veya üstü gerekli
   python --version
   ```

2. **Projeyi İndirin**
   ```bash
   git clone https://github.com/kullanici/metal-analiz-asistani.git
   cd metal-analiz-asistani
   ```

3. **Sanal Ortam Oluşturun**
   ```bash
   # Linux/Mac
   python -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Bağımlılıkları Yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

5. **API Anahtarını Ayarlayın**
   ```bash
   # .env dosyası oluşturun
   echo "GEMINI_API_KEY=your_api_key_here" > .env
   ```

## 💻 Kullanım

```bash
# Uygulamayı başlatın
streamlit run app.py
```

## 🛠️ Teknolojiler

<div align="center">

| Kategori | Teknolojiler |
|:--------:|:------------:|
| Frontend | ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white) |
| Backend | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) |
| Veri Analizi | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white) |
| Görselleştirme | ![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat&logo=plotly&logoColor=white) |
| ML | ![Scikit-learn](https://img.shields.io/badge/Scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white) |
| AI | ![Google Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat&logo=google&logoColor=white) |
| Veritabanı | ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white) |
| Güvenlik | ![Passlib](https://img.shields.io/badge/Passlib-000000?style=flat&logo=passlib&logoColor=white) |

</div>

## 📁 Proje Yapısı

```
metal-analiz-asistani/
├── app.py                 # Ana uygulama
├── requirements.txt       # Bağımlılıklar
├── data/                 # Metal bilgi dosyaları
├── utils/                # Yardımcı modüller
│   ├── auth.py          # Kimlik doğrulama
│   ├── data_loader.py   # Veri yükleme
│   ├── gemini_handler.py # AI entegrasyonu
│   ├── ml_predictor.py  # ML tahminleri
│   ├── plot_generator.py # Grafik oluşturma
│   └── technical_indicators.py # Teknik analiz
└── ui_components/        # Arayüz bileşenleri
    ├── main_page.py     # Ana sayfa
    └── sidebar.py       # Kenar çubuğu
```

## 🔒 Güvenlik

- 🔐 Şifreler bcrypt ile güvenli şekilde hashlenir
- 🔑 API anahtarları .env dosyasında saklanır
- 🛡️ SQLite veritabanı güvenliği
- 🔒 Güçlü şifre politikası

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

<div align="center">

**Metal Analiz Asistanı** ©2024 Created by [vamos99](https://github.com/vamos99)

</div> 