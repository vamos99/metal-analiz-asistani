import os
from PyPDF2 import PdfReader
import logging

logger = logging.getLogger(__name__)

DATA_DIR = "data"

def get_rag_content(metal_name: str) -> str | None:
    """ Belirtilen metal için 'data' klasöründeki TXT veya PDF dosyasından içeriği okur. """
    safe_metal_name = metal_name.replace(" ", "_")
    base_filename_safe = f"{safe_metal_name}_bilgi"
    txt_path = os.path.join(DATA_DIR, f"{base_filename_safe}.txt")
    pdf_path = os.path.join(DATA_DIR, f"{base_filename_safe}.pdf")
    content = None

    logger.info(f"RAG içeriği aranıyor: {metal_name} (Dosya: {base_filename_safe}.txt/pdf)")

    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"RAG içeriği {txt_path} dosyasından okundu.")
        except Exception as e:
            logger.error(f"{txt_path} okuma hatası.", exc_info=True)
            return None
    elif os.path.exists(pdf_path):
        logger.info(f"PDF okuyucu kullanılıyor: {pdf_path}")
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            content = text.strip()
            logger.info(f"RAG içeriği {pdf_path} dosyasından okundu.")
        except Exception as e:
            logger.error(f"{pdf_path} okuma hatası.", exc_info=True)
            return None
    else:
        logger.warning(f"{metal_name} için RAG dosyası ({txt_path} veya {pdf_path}) bulunamadı.")
        return None

    return content if content else None