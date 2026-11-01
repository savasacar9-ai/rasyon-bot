# -*- coding: utf-8 -*-
"""
Otomatik Web Fiyat Tarayıcısı (GTB & Ulusal Süt Konseyi)
Aylık olarak web sitelerini tarar ve yem fiyatlarını günceller:
1. Gaziantep Ticaret Borsası: https://www.gtb.org.tr/aylik-bulten
2. Ulusal Süt Konseyi: https://ulusalsutkonseyi.org.tr/yemlerin-ortalama-fiyatlari/
"""

import os
import re
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger("PriceCrawler")

GTB_URL = "https://www.gtb.org.tr/aylik-bulten"
USK_URL = "https://ulusalsutkonseyi.org.tr/yemlerin-ortalama-fiyatlari/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def fetch_gtb_prices() -> dict:
    """Gaziantep Ticaret Borsası aylık bülteninden ortalama kilogram fiyatlarını çeker."""
    prices = {}
    try:
        r = requests.get(GTB_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"GTB sayfası açılamadı: HTTP {r.status_code}")
            return prices

        tables = re.findall(r'<table.*?>(.*?)</table>', r.text, flags=re.DOTALL | re.IGNORECASE)
        for t in tables:
            rows = re.findall(r'<tr.*?>(.*?)</tr>', t, flags=re.DOTALL | re.IGNORECASE)
            for row in rows:
                cells = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', row, flags=re.DOTALL | re.IGNORECASE)
                clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                if len(clean) >= 4 and clean[0] != 'Ürün Adı':
                    name = clean[0].upper()
                    # ortalama fiyat clean[3]
                    ort_str = clean[3].replace('.', '').replace(',', '.')
                    try:
                        val = float(ort_str)
                    except ValueError:
                        continue

                    if "BUĞDAY KIRIK" in name or "BUGDAY KIRIK" in name:
                        prices["bugday_kirik"] = val
                    elif "BUĞDAY" in name or "BUGDAY" in name:
                        if "SAMAN" not in name and "UN" not in name and "KEPEK" not in name:
                            prices["bugday_tane"] = val
                    elif "MISIR" in name or "MISIR" in name:
                        if "DDGS" in name:
                            prices["misir_ddgs"] = val
                        elif "SİLAJ" not in name and "SILAJ" not in name:
                            prices["misir_tane"] = val
                    elif "KEPEK" in name:
                        prices["bugday_kepegi"] = val
                    elif "SOYA" in name and "KÜSPE" in name:
                        prices["soya_kuspesi_44"] = val
                    elif "BONKALİTE" in name or "BONKALITE" in name:
                        prices["un_bonkalite"] = val

        logger.info(f"GTB'den {len(prices)} ürün fiyatı başarıyla çekildi.")
    except Exception as e:
        logger.error(f"GTB fiyatları çekilirken hata oluştu: {e}")
    return prices

def fetch_usk_prices() -> dict:
    """Ulusal Süt Konseyi (USK) güncel yıllık tablosundan yem fiyatlarını çeker."""
    prices = {}
    try:
        r = requests.get(USK_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"USK sayfası açılamadı: HTTP {r.status_code}")
            return prices

        tables = re.findall(r'<table.*?>(.*?)</table>', r.text, flags=re.DOTALL | re.IGNORECASE)
        # 2026 veya en güncel yıla ait tabloları tara
        for t in tables:
            caption_m = re.findall(r'<caption.*?>(.*?)</caption>', t, flags=re.DOTALL | re.IGNORECASE)
            title = caption_m[0].lower() if caption_m else ""
            
            # Sadece 2026 yılı (veya bulunamazsa genel güncel) tabloları
            if "2026" not in title and caption_m:
                continue

            rows = re.findall(r'<tr.*?>(.*?)</tr>', t, flags=re.DOTALL | re.IGNORECASE)
            last_val = None
            for row in rows:
                cells = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', row, flags=re.DOTALL | re.IGNORECASE)
                clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                if len(clean) >= 2:
                    val_str = clean[1].replace(',', '.')
                    if val_str and val_str != '-' and re.match(r'^\d+(\.\d+)?$', val_str):
                        last_val = float(val_str)

            if last_val is not None:
                if "silaj" in title:
                    prices["misir_silaji"] = last_val
                elif "yonca" in title:
                    prices["yonca_kuru_otu"] = last_val
                elif "saman" in title:
                    prices["bugday_samani"] = last_val
                    prices["arpa_samani"] = round(last_val * 0.55, 2) # Arpa samanı buğday samanına göre %55 civarıdır
                elif "süt yemi" in title or "sut yemi" in title:
                    prices["usk_sut_yemi_19"] = last_val

        logger.info(f"USK'den {len(prices)} yem fiyatı başarıyla çekildi.")
    except Exception as e:
        logger.error(f"USK fiyatları çekilirken hata oluştu: {e}")
    return prices

def auto_update_all_web_prices() -> dict:
    """
    Her iki siteden (GTB ve USK) en son fiyatları çeker,
    feeds_data.json veritabanına yazar ve özet rapor döner.
    """
    from feed_database import FEED_DATABASE, save_feeds
    
    gtb = fetch_gtb_prices()
    usk = fetch_usk_prices()
    
    updated_items = []
    
    # 1. GTB öncelikli güncelleme
    for fid, price in gtb.items():
        if fid in FEED_DATABASE and price > 0:
            old_p = FEED_DATABASE[fid].get("default_price", 0)
            FEED_DATABASE[fid]["default_price"] = price
            updated_items.append((FEED_DATABASE[fid]["name"], old_p, price, "Gaziantep Ticaret Borsası"))

    # 2. USK öncelikli güncelleme (Silaj, Yonca, Saman için ulusal referans)
    for fid, price in usk.items():
        if fid in FEED_DATABASE and price > 0:
            old_p = FEED_DATABASE[fid].get("default_price", 0)
            FEED_DATABASE[fid]["default_price"] = price
            updated_items.append((FEED_DATABASE[fid]["name"], old_p, price, "Ulusal Süt Konseyi"))

    if updated_items:
        save_feeds()
        logger.info(f"Toplam {len(updated_items)} yem fiyatı webden güncellendi.")

    return {
        "status": "success",
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "updated_count": len(updated_items),
        "items": updated_items
    }

if __name__ == "__main__":
    res = auto_update_all_web_prices()
    print("Güncelleme Sonucu:")
    print(f"Zaman: {res['timestamp']}, Güncellenen Ürün Sayısı: {res['updated_count']}")
    for name, old_p, new_p, src in res['items']:
        print(f" - {name}: {old_p} TL -> {new_p} TL ({src})")
