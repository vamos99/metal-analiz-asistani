# utils/gemini_handler.py
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv
import logging
import re
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        logger.info("Google Generative AI (Gemini) başarıyla yapılandırıldı.")
    except Exception as e:
        logger.error(f"Google AI yapılandırma hatası: {e}", exc_info=True)
        API_KEY = None
else:
    logger.error("Kritik Hata: GEMINI_API_KEY ortam değişkeni bulunamadı!")

# İçerik güvenliği filtreleri
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

MODEL_NAME = "gemini-1.5-flash-latest"

def _generate_gemini_content(prompt: str, temperature: float) -> str:
    """Genel Gemini içerik üretme fonksiyonu, temel hata yönetimi ile."""
    if not API_KEY:
        logger.error("Gemini çağrısı yapılamadı: API Anahtarı eksik.")
        return "Hata: Yapay zeka modeli için API anahtarı yapılandırılmamış."

    try:
        generation_config = genai.types.GenerationConfig(temperature=temperature)
        model = genai.GenerativeModel(
            MODEL_NAME,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.info(f"Gemini ({MODEL_NAME}, temp={temperature}) çağrılıyor. Prompt (ilk 300): {prompt[:300]}...")
        response = model.generate_content(prompt)

        try:
            # Yanıtın tüm metin parçalarını birleştir
            full_text = "".join(part.text for part in response.parts)
            comment_text = full_text.strip()

            if not comment_text: # Boş yanıt veya engellenmiş prompt durumu
                 feedback = response.prompt_feedback
                 block_reason = getattr(feedback, 'block_reason', None)
                 safety_ratings = getattr(feedback, 'safety_ratings', [])
                 logger.warning(f"Gemini boş yanıt döndürdü. Block Reason: {block_reason}, Safety Ratings: {safety_ratings}")
                 if block_reason:
                     return f"Yanıt üretilemedi çünkü içerik güvenlik filtrelerimize takıldı (Sebep: {block_reason}). Lütfen sorunuzu değiştirin."
                 else:
                     return "Yanıt üretilemedi. Model beklenmedik bir şekilde boş yanıt döndürdü. Lütfen tekrar deneyin."
            logger.info(f"Gemini yanıtı alındı (ilk 100): {comment_text[:100]}...")
            return comment_text

        except (AttributeError, ValueError) as e: # Yanıt formatı beklenenden farklıysa
             logger.warning(f"Gemini yanıtı işlenemedi (Attribute/Value Error): {e}. Response: {response}")
             feedback = getattr(response, 'prompt_feedback', None)
             block_reason = getattr(feedback, 'block_reason', None) if feedback else None
             if block_reason:
                 return f"Yanıt üretilemedi (İçerik güvenlik filtresine takıldı: {block_reason})."
             else:
                 return "Yanıt formatı beklenenden farklı veya işlenemedi. Lütfen tekrar deneyin."

    # API ile ilgili sık karşılaşılan hatalar
    except ResourceExhausted as ree:
         logger.error(f"Gemini API Hatası: Kaynak Limiti Aşıldı - {ree}")
         return "Hata: AI modeli için kullanım limiti aşıldı. Lütfen daha sonra tekrar deneyin."
    except genai.types.BlockedPromptException as bpe:
         logger.warning(f"Gemini API Hatası: Prompt engellendi - {bpe}")
         return "Hata: Gönderilen içerik güvenlik filtrelerine takıldı."
    except genai.types.StopCandidateException as sce:
         logger.warning(f"Gemini API Hatası: Üretim durduruldu - {sce}")
         return "Hata: Yanıt üretimi güvenlik nedeniyle durduruldu."
    except Exception as e: # Diğer beklenmedik hatalar
        logger.error(f"Gemini API çağrısı sırasında beklenmedik hata: {e}", exc_info=True)
        error_type = type(e).__name__
        if "API key not valid" in str(e):
            return "Hata: Geçersiz Gemini API Anahtarı yapılandırılmış."
        return f"Hata: Yapay zeka yanıtı üretilemedi ({error_type})."

def generate_ai_comment(context: Dict[str, Any], persona_key: str, personas_config: Dict[str, Dict[str, Any]]) -> str:
    """ Uygulama context'ine, RAG bilgisine ve seçilen personaya göre temel yorumu üretir. """
    persona_config = personas_config.get(persona_key)
    if not persona_config:
        logger.error(f"Geçersiz persona anahtarı: {persona_key}")
        return f"Hata: Geçersiz yorumlama personası ('{persona_key}') seçildi."

    persona_prompt_desc = persona_config.get("prompt", "Tarafsız bir analist gibi yorum yap.")
    temperature = persona_config.get("temperature", 0.3)

    metal_name = context.get('selected_metal', 'Bilinmeyen Metal')
    period_name = context.get('selected_period_name', 'Bilinmeyen Dönem')
    rag_content = context.get("rag_content")
    context_summary = context.get("context_summary_string", "Uygulama bağlamı özeti mevcut değil.")

    # Prompt'u yapılandır: Görev, Kimlik, Talimatlar, Veriler
    prompt_parts = [
        f"**Görevin:** Aşağıdaki **Uygulama Bağlamı** ve **Ek Bilgi (RAG)** verilerini kullanarak **{metal_name}** piyasası hakkında **{period_name}** dönemi için **seçilen kimliğe/personaya tamamen uygun, kısa ve öz (en fazla 3-4 cümle)** bir yorum hazırla.",
        f"**Kimliğin/Personan:** {persona_prompt_desc}",
        "**Kritik Talimatlar:**",
        "1. **SADECE Sağlanan Veri:** Yorumunu KESİNLİKLE aşağıdaki 'Uygulama Bağlamı' ve 'Ek Bilgi (RAG)' bölümlerine dayandır. DIŞ BİLGİ veya güncel web araştırması EKLEME.",
        "2. **Bağlantı Kur:** Uygulama bağlamındaki veriler (fiyat, tahmin vb.) ile RAG bilgisindeki temel faktörler arasında kısa bağlantılar kurmaya çalış.",
        "3. **Yatırım Tavsiyesi YOK:** Asla alım/satım tavsiyesi verme.",
        "4. **Kısa ve Net:** Yorumunu 3-4 cümleyi geçmeyecek şekilde kısa tut.",
        "5. **Kaynak Belirtme:** Yorumun sonuna `*Kaynak: Sağlanan uygulama verileri ve RAG.*` şeklinde bir not ekle."
    ]
    prompt_parts.append("\n**1. Uygulama Bağlamı (Arayüzdeki Veriler):**")
    prompt_parts.append(context_summary)

    rag_source_used = "RAG verisi yok"
    if rag_content:
        prompt_parts.append(f"\n**2. Ek Bilgi ({metal_name} - RAG Özeti):**\n{rag_content[:1000]}...") # RAG içeriğini kısaltarak ekle
        safe_metal_name = metal_name.replace(' ','_')
        rag_source_used = f"RAG ({safe_metal_name}_bilgi.txt/pdf)"
    else:
        prompt_parts.append(f"\n**2. Ek Bilgi ({metal_name} - RAG):**")
        prompt_parts.append(f"- Bu metal hakkında ek bilgi (RAG) bulunamadı.")

    prompt_parts.append(f"\n**{persona_config.get('name', persona_key)} Yorumu (Sadece Sağlanan Verilere Göre):**")

    final_prompt = "\n".join(prompt_parts)
    comment_text = _generate_gemini_content(final_prompt, temperature)

    # Yanıt başarılıysa kaynak bilgisini ekle
    if not comment_text.startswith("Hata:") and not comment_text.startswith("Yanıt üretilemedi"):
        return comment_text + f"\n\n---\n*Kaynak: Sağlanan uygulama verileri ve {rag_source_used}.*"
    else:
        return comment_text

def generate_comparison_comment(context: Dict[str, Any], personas_config: Dict[str, Dict[str, Any]]) -> str:
    """ Verilen performans verisi, RAG özetleri ve seçili persona ile karşılaştırma yorumu üretir. """
    persona_key = context.get("persona_key")
    persona_config = personas_config.get(persona_key) if persona_key else None
    if not persona_config: # Geçersiz persona ise varsayılana dön
        logger.error(f"Geçersiz veya eksik persona anahtarı: {persona_key}")
        default_key = list(personas_config.keys())[0]
        persona_config = personas_config.get(default_key)
        if not persona_config: return "Hata: Geçersiz veya eksik karşılaştırma persona yapılandırması."
        persona_key = default_key
        logger.warning(f"'{persona_key}' bulunamadı, varsayılan persona '{default_key}' kullanılıyor.")

    persona_prompt_desc = persona_config.get("prompt", "Tarafsız bir analist gibi yorum yap.")
    temperature = persona_config.get("temperature", 0.4)

    compared_metals = context.get("compared_metals", [])
    performance_data = context.get("performance_data") # Normalize edilmiş son değerler
    rag_summaries = context.get("rag_summaries", {})
    period_name = context.get("period_name", "belirtilen dönem")

    if not compared_metals or performance_data is None or performance_data.empty or len(compared_metals) < 2:
        return "Karşılaştırma yorumu için yeterli performans verisi veya metal seçimi yok."

    # Prompt'u yapılandır: Görev, Kimlik, Talimatlar, Veriler
    prompt_parts = [
        f"**Görevin:** Aşağıdaki metal performans verilerini ve RAG özetlerini kullanarak, **{period_name}** dönemi için **seçilen kimliğe/personaya uygun, kısa (2-3 cümle)** bir karşılaştırmalı yorum yap.",
        f"**Kimliğin/Personan:** {persona_prompt_desc}",
        "**Kritik Talimatlar:**",
        "1. **Performansı Vurgula:** Hangi metalin(lerin) diğerlerine göre belirgin şekilde daha iyi veya daha kötü performans gösterdiğini belirt.",
        "2. **Potansiyel Neden:** Bu performans farkının **POTANSİYEL** nedenini RAG özetlerindeki bilgilere (örn: endüstriyel kullanım, yatırımcı ilgisi) dayanarak **çok kısa** (1 cümle) açıkla.",
        "3. **Sadece Sağlanan Bilgi:** Yorumunu SADECE aşağıdaki verilere ve RAG özetlerine dayandır. DIŞ BİLGİ EKLEME.",
        "4. **Yatırım Tavsiyesi YOK.**",
        "5. **Kısa ve Öz:** Yorumunu 2-3 cümle ile sınırla.",
        "6. **Kaynak Belirtme:** Yorumun sonuna `*Kaynak: Karşılaştırma verileri ve RAG özetleri.*` notunu ekle."
    ]

    prompt_parts.append(f"\n**Performans Verileri ({period_name}, Başlangıç=100):**")
    try:
        # Performans verisini (son normalize değerler) prompt'a ekle
        for metal, perf in performance_data.items():
            prompt_parts.append(f"- {metal}: {perf-100:.2f}%") # Yüzdelik değişim olarak göster
    except AttributeError:
         logger.error("Karşılaştırma yorumu: performance_data beklenen formatta değil (Series değil?).")
         return "Hata: Performans verileri işlenemedi."

    prompt_parts.append("\n**Metaller Hakkında Kısa Bilgiler (RAG Özetleri):**")
    if rag_summaries:
        for metal, summary in rag_summaries.items():
            prompt_parts.append(f"- {metal}: {summary}")
    else:
        prompt_parts.append("- Metaller hakkında RAG özeti bulunamadı.")

    prompt_parts.append(f"\n**{persona_config.get('name', persona_key)} Karşılaştırma Yorumu (Sağlanan Verilere Göre):**")

    final_prompt = "\n".join(prompt_parts)
    comment_text = _generate_gemini_content(final_prompt, temperature)

    if not comment_text.startswith("Hata:") and not comment_text.startswith("Yanıt üretilemedi"):
        return comment_text + f"\n\n---\n*Kaynak: Karşılaştırma verileri ve RAG özetleri.*"
    else:
        return comment_text

def generate_chat_response(user_query: str, chat_history: List[Dict[str, str]], context: Dict[str, Any]) -> str:
    """ Kullanıcı sorgusuna, geçmişe, RAG'a ve uygulama context'ine göre yorumlayıcı ve sohbet odaklı yanıt üretir. """
    temperature = 0.5
    metal_name_in_context = context.get('selected_metal', 'Bilinmeyen Metal')
    rag_content = context.get("rag_content")
    context_summary = context.get("context_summary_string", "Uygulama bağlamı özeti mevcut değil.")

    # Sohbet geçmişini LLM için formatla
    formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])

    # ML tahmin bilgisini hazırla
    ml_prediction_info = "Uygulamada ML Tahmini: Mevcut Değil/Yapılmadı"
    ml_trend = "Yok"
    if context.get("prediction"):
        pred = context["prediction"]
        pred_days = pred.get('predict_days', '?')
        ml_trend = pred.get('trend', 'Bilinmiyor')
        ml_prediction_info = f"Uygulamadaki ML Tahmini ({pred_days}-Günlük): **{ml_trend}** (Not: Bu basit bir modeldir, finansal tavsiye değildir ve garanti sunmaz.)"

    # Prompt'u yapılandır: Rol, Görev, Önemli Kurallar, Bilgi Kaynakları, Yanıtlama Tarzı, Veriler
    prompt_parts = [
        "**Rolün:** Sen bilgili, analitik ve içgörü sahibi bir Metal Piyasası Tartışma Partnerisin. Finansal tavsiye vermezsin ama verileri yorumlayarak ve sentezleyerek kullanıcıların kendi kararlarını vermesine yardımcı olursun.",
        "**Görevin:** Kullanıcının metal piyasaları, finans veya uygulamadaki analizler hakkındaki sorularını yanıtlamak.",
        "**>>> ÇOK ÖNEMLİ KURAL: SORUDAKİ METALE ODAKLAN! <<<**",
        f"Cevabını HER ZAMAN kullanıcının **son sorusunda belirttiği metale** odakla. Aşağıda sana sağlanan 'Güncel Uygulama Bağlamı' ve 'Temel Metal Bilgisi (RAG)' şu anda **arayüzde seçili olan `{metal_name_in_context}` metaline aittir.**",
        f"Eğer kullanıcının sorusu `{metal_name_in_context}` hakkında ise, sağlanan tüm bilgileri (Context, RAG, ML) kullanarak detaylı yorum yap.",
        "Eğer kullanıcının sorusu **FARKLI** bir metal hakkındaysa (örn: Altın soruyorsa ama context Gümüş içinse), cevabını **o FARKLI metal üzerine** kur. Bu durumda, sağlanan context ve RAG'ın o metal için geçerli olmadığını, dolayısıyla o metale özel detaylı analiz veya ML yorumu yapamayacağını belirt. Ancak, o metalle ilgili genel finansal bilgilerini (varsa) veya temel prensipleri kullanarak yine de yardımcı olmaya çalış.",
        "**Bilgi Kaynakların:**",
        f"1.  **Güncel Uygulama Bağlamı ({metal_name_in_context} İçin):** Kullanıcının arayüzde gördüğü analizler (aşağıda).",
        f"2.  **Temel Metal Bilgisi (RAG - {metal_name_in_context} İçin):** Seçili metal hakkında genel bilgiler (aşağıda).",
        "3.  **Sohbet Geçmişi:** Konuşmanın akışı.",
        "**Yanıtlama Tarzın ve İlkelerin:**",
        "-   **Derinlemesine Yorumla (Eğer Soru Context'teki Metalle İlgiliyse):** Verileri yorumla. RAG bilgisiyle birleştirerek anlam çıkar. Neden-sonuç ilişkileri kurmaya çalış.",
        "-   **ML Tahminini Entegre Et (Eğer Soru Context'teki Metalle İlgiliyse ve ML Varsa):** ML Tahmini varsa, bu trend bilgisini analizinin merkezine koy. RAG veya diğer verilerle uyuşup uyuşmadığını tartış. Basitliğini ve garanti olmadığını vurgula.",
        "-   **Dengeli Perspektif Sun:** Destekleyici ve karşıt argümanları sun.",
        "-   **'Almalı mıyım?' / Yatırım Kararı Soruları:**",
        "    1.  Kesinlikle 'evet/hayır' deme veya doğrudan tavsiye verme. 'Bu kişisel bir karar ve yatırım tavsiyesi veremem' cümlesiyle başla.",
        "    2.  **Sonrasında** SANA SAĞLANAN verilere (eğer soru context'teki metalle ilgiliyse o metalin verileri, değilse genel prensipler) dayanarak potansiyel **artıları ve eksileri** net bir şekilde listele ve tartış.",
        "    3.  **<<< EĞİLİM YORUMU (Eğer Soru Context'teki Metalle İlgiliyse) >>>** Tüm artı ve eksileri değerlendirdikten sonra, **'Ancak, yalnızca elimizdeki bu sınırlı verilere (fiyat durumu, RAG bilgisi, ML tahmini [{ML Trendi Varsa Belirt, Yoksa 'Yok'}]) dayanarak bir genel bakış sunmam gerekirse, tablo şu an için daha çok [{Hafifçe Olumlu / Hafifçe Olumsuz / Dengeli / Belirsiz}] bir eğilim gösteriyor gibi duruyor.'** şeklinde, verilerin genel dengesini yansıtan bir **yorum ekle.** Bu yorumun KESİNLİKLE bir tavsiye olmadığını vurgula.",
        "    4.  Kararın kullanıcının kendi risk profiline, hedeflerine ve ek araştırmasına bağlı olduğunu belirterek bitir.",
        "-   **Gelecek Tahmini Soruları:** Kesin fiyat tahmini yapma. RAG'daki uzun vadeli faktörleri veya ML tahmininin *ne gösterdiğini* (varsa ve garanti olmadığını vurgulayarak) tartış.",
        "-   **Sohbeti Sürdür:** Kullanıcının amacını anlamaya çalış.",
        "-   **Sadece Sağlanan Bilgi:** DIŞ KAYNAKLARDAN (WEB ARAMASI YOK) bilgi EKLEME.",
        "-   **Kapsam Dışı Konular:** Metal piyasaları, finans ve sağlanan veriler dışındaki sorulara kibarca uzmanlık alanın olmadığını belirt.",
        f"\n**1. Güncel Uygulama Bağlamı ({metal_name_in_context} İçin):**",
        context_summary,
        f"\n{ml_prediction_info}", # ML bilgisini context özetine ekle
        f"\n**2. Temel Metal Bilgisi (RAG - {metal_name_in_context} İçin Varsa):**"
    ]
    if rag_content:
        prompt_parts.append(f"{rag_content[:1200]}...") # RAG içeriğini kısaltarak ekle
    else:
        prompt_parts.append(f"- '{metal_name_in_context}' için RAG bilgisi bulunamadı.")

    prompt_parts.append("\n**3. Önceki Sohbet Geçmişi:**")
    prompt_parts.append(formatted_history if formatted_history else "- Yok")

    prompt_parts.append("\n**Kullanıcının Son Sorusu:**")
    prompt_parts.append(user_query)

    prompt_parts.append("\n**Asistanın Analitik ve Sorudaki Metale Odaklı Yanıtı:**")

    final_prompt_for_api = "\n".join(prompt_parts)

    # Eğilim yorumu için prompt'taki placeholder'ı dinamik olarak doldur
    final_prompt_for_api = final_prompt_for_api.replace("{ML Trendi Varsa Belirt, Yoksa 'Yok'}", ml_trend if ml_trend else "Yok")

    response_text = _generate_gemini_content(final_prompt_for_api, temperature)

    # Yanıttan olası prompt başlığı kalıntılarını temizle
    response_text = re.sub(r"^\*\*Asistan(ın)?\s*(Analitik(, Dengeli)? ve (Eğilim Belirten|Sorudaki Metale Odaklı))?\s*Yanıtı:\*\*\s*", "", response_text, flags=re.IGNORECASE).strip()

    return response_text