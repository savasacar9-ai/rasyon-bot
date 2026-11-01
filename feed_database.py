# -*- coding: utf-8 -*-
"""
Yem Kütüphanesi ve Kalıcı Veritabanı (Persistent Feed Database)
Tüm değişiklikler (fiyat güncellemeleri, yeni yem eklemeleri) kalıcı olarak
'feeds_data.json' dosyasına yazılır ve bot kapansa dahi korunur.
"""

import os
import json
import logging

logger = logging.getLogger("FeedDB")
DB_FILE = os.path.join(os.path.dirname(__file__), "feeds_data.json")

# Varsayılan başlangıç yem kütüphanesi
INITIAL_FEEDS = {
    # 1. KABA YEMLER
    "arpa_samani": {
        "id": "arpa_samani",
        "name": "Arpa Samanı",
        "category": "Kaba Yem",
        "KM": 90.0, "ME": 1.45, "NEL": 0.90, "HP": 3.8, "NDF": 72.0, "ADF": 46.0,
        "Ca": 0.35, "P": 0.10, "is_forage": True,
        "default_price": 2.0, "min_default": 0.5, "max_default": 4.0
    },
    "bugday_samani": {
        "id": "bugday_samani",
        "name": "Buğday Samanı",
        "category": "Kaba Yem",
        "KM": 90.0, "ME": 1.40, "NEL": 0.85, "HP": 3.2, "NDF": 75.0, "ADF": 48.0,
        "Ca": 0.30, "P": 0.08, "is_forage": True,
        "default_price": 1.8, "min_default": 0.5, "max_default": 4.0
    },
    "yonca_kuru_otu": {
        "id": "yonca_kuru_otu",
        "name": "Yonca Kuru Otu (%16 HP)",
        "category": "Kaba Yem",
        "KM": 88.0, "ME": 2.15, "NEL": 1.35, "HP": 16.5, "NDF": 45.0, "ADF": 33.0,
        "Ca": 1.45, "P": 0.25, "is_forage": True,
        "default_price": 8.0, "min_default": 0.5, "max_default": 7.0
    },
    "misir_silaji": {
        "id": "misir_silaji",
        "name": "Mısır Silajı (%30 KM)",
        "category": "Sulu Kaba Yem",
        "KM": 30.0, "ME": 2.45, "NEL": 1.55, "HP": 8.2, "NDF": 44.0, "ADF": 26.0,
        "Ca": 0.28, "P": 0.22, "is_forage": True,
        "default_price": 2.5, "min_default": 2.0, "max_default": 25.0
    },
    "pancar_posasi_yas": {
        "id": "pancar_posasi_yas",
        "name": "Şeker Pancarı Posası (Yaş)",
        "category": "Sulu Kaba Yem",
        "KM": 18.0, "ME": 2.50, "NEL": 1.60, "HP": 9.5, "NDF": 45.0, "ADF": 24.0,
        "Ca": 0.60, "P": 0.12, "is_forage": True,
        "default_price": 1.8, "min_default": 0.0, "max_default": 12.0
    },

    # 2. HAMMADDE ENERJİ & PROTEİN
    "arpa_ezme": {
        "id": "arpa_ezme",
        "name": "Arpa (Ezme / Kırma)",
        "category": "Enerji Yemi",
        "KM": 88.0, "ME": 2.95, "NEL": 1.85, "HP": 11.5, "NDF": 19.0, "ADF": 6.5,
        "Ca": 0.08, "P": 0.38, "is_forage": False,
        "default_price": 8.5, "min_default": 0.0, "max_default": 7.0
    },
    "misir_tane": {
        "id": "misir_tane",
        "name": "Mısır (Tane / Kırma)",
        "category": "Enerji Yemi",
        "KM": 87.0, "ME": 3.15, "NEL": 1.95, "HP": 9.0, "NDF": 10.5, "ADF": 3.5,
        "Ca": 0.04, "P": 0.30, "is_forage": False,
        "default_price": 8.8, "min_default": 0.0, "max_default": 6.0
    },
    "bugday_kepegi": {
        "id": "bugday_kepegi",
        "name": "Buğday Kepeği",
        "category": "Enerji/Yan Ürün",
        "KM": 88.0, "ME": 2.30, "NEL": 1.45, "HP": 15.0, "NDF": 42.0, "ADF": 13.0,
        "Ca": 0.14, "P": 1.05, "is_forage": False,
        "default_price": 6.5, "min_default": 0.0, "max_default": 3.0
    },
    "aycicegi_kuspesi_28": {
        "id": "aycicegi_kuspesi_28",
        "name": "Ayçiçeği Küspesi (%28 HP)",
        "category": "Protein Yemi",
        "KM": 90.0, "ME": 2.10, "NEL": 1.30, "HP": 28.0, "NDF": 38.0, "ADF": 26.0,
        "Ca": 0.38, "P": 0.95, "is_forage": False,
        "default_price": 9.5, "min_default": 0.0, "max_default": 3.5
    },
    "pamuk_kuspesi_28": {
        "id": "pamuk_kuspesi_28",
        "name": "Pamuk Küspesi (%28 HP)",
        "category": "Protein Yemi",
        "KM": 90.0, "ME": 2.35, "NEL": 1.45, "HP": 28.0, "NDF": 35.0, "ADF": 22.0,
        "Ca": 0.22, "P": 0.90, "is_forage": False,
        "default_price": 11.0, "min_default": 0.0, "max_default": 3.0
    },
    "soya_kuspesi_44": {
        "id": "soya_kuspesi_44",
        "name": "Soya Küspesi (%44 HP)",
        "category": "Protein Yemi",
        "KM": 89.0, "ME": 3.05, "NEL": 1.95, "HP": 44.0, "NDF": 14.0, "ADF": 8.0,
        "Ca": 0.32, "P": 0.65, "is_forage": False,
        "default_price": 18.0, "min_default": 0.0, "max_default": 2.5
    },

    # 3. BUZAĞI YEMLERİ
    "pro_vira_buzagi": {
        "id": "pro_vira_buzagi",
        "name": "Pro-Vira Buzağı (%18 HP)",
        "category": "Fabrika Buzağı Yemi",
        "KM": 88.0, "ME": 3.12, "NEL": 1.88, "HP": 18.0, "NDF": 22.0, "ADF": 8.0,
        "Ca": 1.15, "P": 0.60, "is_forage": False,
        "default_price": 13.5, "min_default": 0.0, "max_default": 5.0
    },
    "pro_tutku_buzagi": {
        "id": "pro_tutku_buzagi",
        "name": "Pro-Tutku Buzağı (%17 HP)",
        "category": "Fabrika Buzağı Yemi",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 17.0, "NDF": 23.0, "ADF": 9.0,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 13.0, "min_default": 0.0, "max_default": 5.0
    },

    # 4. PROYEM & KABUL YEM - BESİ YEMLERİ
    "pro_tosun_besi": {
        "id": "pro_tosun_besi",
        "name": "Pro Tosun Besi (%14 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 2.84, "NEL": 1.70, "HP": 14.0, "NDF": 28.0, "ADF": 12.0,
        "Ca": 1.00, "P": 0.50, "is_forage": False,
        "default_price": 11.5, "min_default": 0.0, "max_default": 8.0
    },
    "pro_spr_tosun": {
        "id": "pro_spr_tosun",
        "name": "Pro Spr Tosun Besi (%15 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 15.0, "NDF": 26.0, "ADF": 10.0,
        "Ca": 1.05, "P": 0.52, "is_forage": False,
        "default_price": 12.2, "min_default": 0.0, "max_default": 8.0
    },
    "pro_sah_besi": {
        "id": "pro_sah_besi",
        "name": "Pro Şah Besi (%16 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 16.0, "NDF": 25.0, "ADF": 9.5,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 12.8, "min_default": 0.0, "max_default": 8.0
    },
    "pro_mat_besi_bitir": {
        "id": "pro_mat_besi_bitir",
        "name": "Pro Mat Besi Bitir (%14 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 3.18, "NEL": 1.95, "HP": 14.0, "NDF": 22.0, "ADF": 8.0,
        "Ca": 1.00, "P": 0.50, "is_forage": False,
        "default_price": 12.5, "min_default": 0.0, "max_default": 8.0
    },
    "pro_tahil_besi": {
        "id": "pro_tahil_besi",
        "name": "Pro Tahıl Besi (%20 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 20.0, "NDF": 30.0, "ADF": 14.0,
        "Ca": 1.20, "P": 0.60, "is_forage": False,
        "default_price": 13.5, "min_default": 0.0, "max_default": 8.0
    },
    "pro_tane_besi_toz": {
        "id": "pro_tane_besi_toz",
        "name": "Pro Tane Besi Toz (%14 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 2.95, "NEL": 1.78, "HP": 14.0, "NDF": 27.0, "ADF": 11.0,
        "Ca": 1.00, "P": 0.50, "is_forage": False,
        "default_price": 11.8, "min_default": 0.0, "max_default": 8.0
    },
    "kabul_cusse": {
        "id": "kabul_cusse",
        "name": "Kabul Cüsse Besi (%14 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 14.0, "NDF": 29.0, "ADF": 13.0,
        "Ca": 1.00, "P": 0.50, "is_forage": False,
        "default_price": 11.2, "min_default": 0.0, "max_default": 8.0
    },
    "kabul_besi_toz": {
        "id": "kabul_besi_toz",
        "name": "Kabul Besi Toz (%14 HP)",
        "category": "Fabrika Besi Yemi",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 14.0, "NDF": 29.0, "ADF": 13.0,
        "Ca": 1.00, "P": 0.50, "is_forage": False,
        "default_price": 11.0, "min_default": 0.0, "max_default": 8.0
    },

    # 5. PROYEM & KABUL YEM - SÜT YEMLERİ
    "pro_aktif": {
        "id": "pro_aktif",
        "name": "Pro-Aktif Süt (%18 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 18.0, "NDF": 28.0, "ADF": 12.0,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 12.5, "min_default": 0.0, "max_default": 9.0
    },
    "pro_enerji": {
        "id": "pro_enerji",
        "name": "Pro-Enerji Süt (%19 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 19.0, "NDF": 26.0, "ADF": 10.0,
        "Ca": 1.15, "P": 0.55, "is_forage": False,
        "default_price": 13.2, "min_default": 0.0, "max_default": 9.0
    },
    "pro_4x4": {
        "id": "pro_4x4",
        "name": "Pro-4x4 Süt (%19 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.12, "NEL": 1.88, "HP": 19.0, "NDF": 25.0, "ADF": 9.5,
        "Ca": 1.15, "P": 0.55, "is_forage": False,
        "default_price": 13.5, "min_default": 0.0, "max_default": 9.0
    },
    "pro_kanit": {
        "id": "pro_kanit",
        "name": "Pro Kanıt Süt (%20 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.18, "NEL": 1.92, "HP": 20.0, "NDF": 24.0, "ADF": 9.0,
        "Ca": 1.20, "P": 0.58, "is_forage": False,
        "default_price": 13.8, "min_default": 0.0, "max_default": 9.0
    },
    "pro_41": {
        "id": "pro_41",
        "name": "Pro-41 Süt (%21 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.12, "NEL": 1.88, "HP": 21.0, "NDF": 24.0, "ADF": 9.5,
        "Ca": 1.20, "P": 0.58, "is_forage": False,
        "default_price": 14.0, "min_default": 0.0, "max_default": 9.0
    },
    "pro_cizgi": {
        "id": "pro_cizgi",
        "name": "Pro Çizgi Süt (%21 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.18, "NEL": 1.92, "HP": 21.0, "NDF": 23.0, "ADF": 9.0,
        "Ca": 1.20, "P": 0.60, "is_forage": False,
        "default_price": 14.2, "min_default": 0.0, "max_default": 9.0
    },
    "pro_balans": {
        "id": "pro_balans",
        "name": "Pro-Balans Süt (%26 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 2.84, "NEL": 1.72, "HP": 26.0, "NDF": 26.0, "ADF": 11.0,
        "Ca": 1.30, "P": 0.65, "is_forage": False,
        "default_price": 15.5, "min_default": 0.0, "max_default": 9.0
    },
    "pro_dogus": {
        "id": "pro_dogus",
        "name": "Pro-Doğuş Süt (%23 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.29, "NEL": 2.00, "HP": 23.0, "NDF": 22.0, "ADF": 8.5,
        "Ca": 1.25, "P": 0.60, "is_forage": False,
        "default_price": 15.0, "min_default": 0.0, "max_default": 9.0
    },
    "pro_kuru_donem": {
        "id": "pro_kuru_donem",
        "name": "Pro Kuru Dönem (%18 HP)",
        "category": "Fabrika Süt/Kuru",
        "KM": 88.0, "ME": 2.72, "NEL": 1.62, "HP": 18.0, "NDF": 28.0, "ADF": 12.0,
        "Ca": 0.80, "P": 0.50, "is_forage": False,
        "default_price": 12.8, "min_default": 0.0, "max_default": 5.0
    },
    "pro_son_60": {
        "id": "pro_son_60",
        "name": "Pro Son 60 (%22 HP)",
        "category": "Fabrika Süt/Geçiş",
        "KM": 88.0, "ME": 2.84, "NEL": 1.72, "HP": 22.0, "NDF": 25.0, "ADF": 10.0,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 14.5, "min_default": 0.0, "max_default": 5.0
    },
    "pro_duve": {
        "id": "pro_duve",
        "name": "Pro Düve (%18 HP)",
        "category": "Fabrika Düve Yemi",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 18.0, "NDF": 28.0, "ADF": 12.0,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 12.5, "min_default": 0.0, "max_default": 6.0
    },
    "pro_tane_sut_toz": {
        "id": "pro_tane_sut_toz",
        "name": "Pro Tane Süt Toz (%18 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 18.0, "NDF": 26.0, "ADF": 11.0,
        "Ca": 1.15, "P": 0.55, "is_forage": False,
        "default_price": 12.8, "min_default": 0.0, "max_default": 9.0
    },
    "kabul_dira": {
        "id": "kabul_dira",
        "name": "Kabul Dira Süt (%18 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 2.84, "NEL": 1.70, "HP": 18.0, "NDF": 27.0, "ADF": 11.0,
        "Ca": 1.10, "P": 0.55, "is_forage": False,
        "default_price": 12.0, "min_default": 0.0, "max_default": 9.0
    },
    "kabul_nisan": {
        "id": "kabul_nisan",
        "name": "Kabul Nişan Süt (%21 HP)",
        "category": "Fabrika Süt Yemi",
        "KM": 88.0, "ME": 2.95, "NEL": 1.78, "HP": 21.0, "NDF": 25.0, "ADF": 10.0,
        "Ca": 1.15, "P": 0.55, "is_forage": False,
        "default_price": 13.0, "min_default": 0.0, "max_default": 9.0
    },

    # 6. PROYEM - KÜÇÜKBAŞ YEMLERİ
    "pro_kuzu_yemi": {
        "id": "pro_kuzu_yemi",
        "name": "Pro Kuzu Yemi (%16 HP)",
        "category": "Fabrika Küçükbaş",
        "KM": 88.0, "ME": 3.06, "NEL": 1.85, "HP": 16.0, "NDF": 22.0, "ADF": 8.0,
        "Ca": 1.05, "P": 0.50, "is_forage": False,
        "default_price": 13.0, "min_default": 0.0, "max_default": 1.8
    },
    "skor_kuzu_besi": {
        "id": "skor_kuzu_besi",
        "name": "Skor Kuzu Besi (%16 HP)",
        "category": "Fabrika Küçükbaş",
        "KM": 88.0, "ME": 3.23, "NEL": 1.95, "HP": 16.0, "NDF": 20.0, "ADF": 7.0,
        "Ca": 1.10, "P": 0.50, "is_forage": False,
        "default_price": 13.5, "min_default": 0.0, "max_default": 1.8
    },
    "pro_toklu_besi": {
        "id": "pro_toklu_besi",
        "name": "Pro Toklu Besi (%13 HP)",
        "category": "Fabrika Küçükbaş",
        "KM": 88.0, "ME": 3.01, "NEL": 1.82, "HP": 13.0, "NDF": 24.0, "ADF": 9.0,
        "Ca": 0.95, "P": 0.45, "is_forage": False,
        "default_price": 12.0, "min_default": 0.0, "max_default": 1.8
    },
    "pro_taneli_toklu": {
        "id": "pro_taneli_toklu",
        "name": "Pro Taneli Toklu (%12 HP)",
        "category": "Fabrika Küçükbaş",
        "KM": 88.0, "ME": 3.12, "NEL": 1.90, "HP": 12.0, "NDF": 22.0, "ADF": 8.0,
        "Ca": 0.90, "P": 0.45, "is_forage": False,
        "default_price": 12.2, "min_default": 0.0, "max_default": 1.8
    },
    "pro_koyun_sut": {
        "id": "pro_koyun_sut",
        "name": "Pro Koyun Süt (%18 HP)",
        "category": "Fabrika Küçükbaş",
        "KM": 88.0, "ME": 2.72, "NEL": 1.65, "HP": 18.0, "NDF": 26.0, "ADF": 11.0,
        "Ca": 1.15, "P": 0.55, "is_forage": False,
        "default_price": 12.8, "min_default": 0.0, "max_default": 1.8
    },

    # 7. MİNERAL VE KATKILAR
    "mermer_tozu": {
        "id": "mermer_tozu",
        "name": "Mermer Tozu (Kireçtaşı - Ca)",
        "category": "Mineral",
        "KM": 99.0, "ME": 0.0, "NEL": 0.0, "HP": 0.0, "NDF": 0.0, "ADF": 0.0,
        "Ca": 38.0, "P": 0.02, "is_forage": False,
        "default_price": 2.0, "min_default": 0.03, "max_default": 0.15
    },
    "tuz": {
        "id": "tuz",
        "name": "Tuz (Yem Tuzu)",
        "category": "Mineral",
        "KM": 99.0, "ME": 0.0, "NEL": 0.0, "HP": 0.0, "NDF": 0.0, "ADF": 0.0,
        "Ca": 0.0, "P": 0.0, "is_forage": False,
        "default_price": 2.0, "min_default": 0.02, "max_default": 0.06
    },
    "sodyum_bikarbonat": {
        "id": "sodyum_bikarbonat",
        "name": "Sodyum Bikarbonat (Soda)",
        "category": "Katkı",
        "KM": 99.0, "ME": 0.0, "NEL": 0.0, "HP": 0.0, "NDF": 0.0, "ADF": 0.0,
        "Ca": 0.0, "P": 0.0, "is_forage": False,
        "default_price": 15.0, "min_default": 0.0, "max_default": 0.15
    },
    "vitamin_mineral": {
        "id": "vitamin_mineral",
        "name": "Vitamin-Mineral Premiksi",
        "category": "Premiks",
        "KM": 98.0, "ME": 0.0, "NEL": 0.0, "HP": 0.0, "NDF": 0.0, "ADF": 0.0,
        "Ca": 15.0, "P": 5.0, "is_forage": False,
        "default_price": 35.0, "min_default": 0.02, "max_default": 0.08
    }
}

# Bellek içi aktif veritabanı
FEED_DATABASE = {}

def load_feeds():
    """Kalıcı JSON dosyasından yemleri yükler, yoksa INITIAL_FEEDS ile başlatır."""
    global FEED_DATABASE
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                FEED_DATABASE = dict(INITIAL_FEEDS)
                FEED_DATABASE.update(saved)
                return
        except Exception as e:
            logger.error(f"Error loading feeds_data.json: {e}")
    FEED_DATABASE = dict(INITIAL_FEEDS)
    save_feeds()

def save_feeds():
    """Tüm yem ve fiyat verilerini kalıcı JSON dosyasına kaydeder."""
    global FEED_DATABASE
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(FEED_DATABASE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving feeds_data.json: {e}")

def update_feed_price(feed_id: str, new_price: float) -> bool:
    """Belirli bir yemin fiyatını günceller ve diske kaydeder."""
    global FEED_DATABASE
    if feed_id in FEED_DATABASE:
        FEED_DATABASE[feed_id]["default_price"] = float(new_price)
        save_feeds()
        return True
    return False

def add_new_custom_feed(feed_data: dict) -> str:
    """Kullanıcının girdiği yeni yemi veritabanına ekler ve diske kaydeder."""
    global FEED_DATABASE
    name = feed_data.get("name", "Yeni Yem")
    # feed_id oluştur
    feed_id = "".join(c for c in name.lower() if c.isalnum() or c == "_")
    if not feed_id:
        feed_id = f"custom_feed_{len(FEED_DATABASE)+1}"
        
    feed_entry = {
        "id": feed_id,
        "name": name,
        "category": feed_data.get("category", "Genel Yem"),
        "KM": float(feed_data.get("KM", 88.0)),
        "ME": float(feed_data.get("ME", 2.5)),
        "NEL": float(feed_data.get("NEL", feed_data.get("ME", 2.5) * 0.62)),
        "HP": float(feed_data.get("HP", 14.0)),
        "NDF": float(feed_data.get("NDF", 30.0)),
        "ADF": float(feed_data.get("ADF", 15.0)),
        "Ca": float(feed_data.get("Ca", 0.5)),
        "P": float(feed_data.get("P", 0.3)),
        "is_forage": ("kaba" in feed_data.get("category", "").lower() or "silaj" in name.lower() or "saman" in name.lower() or "yonca" in name.lower()),
        "default_price": float(feed_data.get("default_price", 10.0)),
        "min_default": 0.0,
        "max_default": 8.0
    }
    FEED_DATABASE[feed_id] = feed_entry
    save_feeds()
    return feed_id

def normalize_tr(text: str) -> str:
    """Türkçe karakterleri normalize eder."""
    tr_map = {
        'ı': 'i', 'I': 'i', 'İ': 'i',
        'ş': 's', 'Ş': 's',
        'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o',
        'ç': 'c', 'Ç': 'c'
    }
    t = text.lower()
    for tr, en in tr_map.items():
        t = t.replace(tr, en)
    return t.strip()

COMMON_ALIASES = {
    "arpa": "arpa_ezme",
    "arpa ezme": "arpa_ezme",
    "arpa samani": "arpa_samani",
    "saman": "bugday_samani",
    "bugday samani": "bugday_samani",
    "yonca": "yonca_kuru_otu",
    "yonca otu": "yonca_kuru_otu",
    "silaj": "misir_silaji",
    "misir silaji": "misir_silaji",
    "misir": "misir_tane",
    "misir tane": "misir_tane",
    "kepek": "bugday_kepegi",
    "aycicek": "aycicegi_kuspesi_28",
    "aycicegi kuspesi": "aycicegi_kuspesi_28",
    "pamuk": "pamuk_kuspesi_28",
    "pamuk kuspesi": "pamuk_kuspesi_28",
    "soya": "soya_kuspesi_44",
    "soya kuspesi": "soya_kuspesi_44",
    "bugday": "bugday_tane",
    "tane bugday": "bugday_tane",
    "kirik bugday": "bugday_kirik",
    "ddgs": "misir_ddgs",
    "bonkalite": "un_bonkalite",
    "mercimek samani": "mercimek_samani",
    "protek": "pro_protek_besi",
    "protek besi": "pro_protek_besi",
    "kuru donem": "pro_kuru_donem",
    "son 60": "pro_son_60",
    "tosun": "pro_tosun_besi",
    "pro tosun": "pro_tosun_besi",
    "super tosun": "pro_spr_tosun",
    "sah besi": "pro_sah_besi",
    "mat besi": "pro_mat_besi_bitir",
    "vira": "pro_vira_buzagi",
    "tutku": "pro_tutku_buzagi",
    "aktif": "pro_aktif",
    "enerji": "pro_enerji",
    "4x4": "pro_4x4",
    "kanit": "pro_kanit",
    "cizgi": "pro_cizgi",
    "balans": "pro_balans",
    "dogus": "pro_dogus",
    "duve": "pro_duve",
    "kuzu": "pro_kuzu_yemi",
    "toklu": "pro_toklu_besi",
    "skor": "skor_kuzu_besi",
    "mermer": "mermer_tozu",
    "tuz": "tuz",
    "karbonat": "sodyum_bikarbonat",
    "bikarbonat": "sodyum_bikarbonat",
    "vitamin": "vitamin_mineral"
}

def find_feed_by_fuzzy_name(search_term: str):
    """Kullanıcının yazdığı isimle en uygun yemi bulur."""
    norm = normalize_tr(search_term)
    
    # 1. Alias kontrolü
    if norm in COMMON_ALIASES:
        target_id = COMMON_ALIASES[norm]
        if target_id in FEED_DATABASE:
            return target_id, FEED_DATABASE[target_id]
            
    # 2. Tam id veya ad eşleşmesi
    for fid, f in FEED_DATABASE.items():
        if norm == normalize_tr(fid) or norm == normalize_tr(f["name"]):
            return fid, f
            
    # 3. İsim içinde geçen eşleşme
    for fid, f in FEED_DATABASE.items():
        f_norm = normalize_tr(f["name"])
        if norm in f_norm or f_norm in norm:
            return fid, f
            
    # 4. Kelime bazlı eşleşme
    words = norm.split()
    for fid, f in FEED_DATABASE.items():
        f_norm = normalize_tr(f["name"])
        if all(w in f_norm for w in words):
            return fid, f
            
    return None, None

def delete_custom_feed(feed_id: str) -> bool:
    """Kullanıcı tarafından eklenen özel bir yemi siler."""
    global FEED_DATABASE
    if feed_id in FEED_DATABASE:
        del FEED_DATABASE[feed_id]
        save_feeds()
        return True
    return False

def reset_to_defaults() -> bool:
    """Veritabanını ilk varsayılan değerlere döndürür."""
    global FEED_DATABASE
    FEED_DATABASE = json.loads(json.dumps(INITIAL_FEEDS))
    save_feeds()
    return True

def get_feed_keys_by_group(group: str):
    """Gruba özel yem listesini döner."""
    common_forages = ["arpa_samani", "bugday_samani", "yonca_kuru_otu", "misir_silaji", "pancar_posasi_yas"]
    common_grains = ["arpa_ezme", "misir_tane", "bugday_kepegi", "aycicegi_kuspesi_28", "pamuk_kuspesi_28"]
    common_minerals = ["mermer_tozu", "tuz", "vitamin_mineral"]

    # Kullanıcı tarafından sonradan eklenen özel yemler
    custom_added = [fid for fid in FEED_DATABASE if fid not in INITIAL_FEEDS]

    if group == "besi":
        besi_factory = [
            "pro_vira_buzagi", "pro_tutku_buzagi",
            "pro_tosun_besi", "pro_spr_tosun", "pro_sah_besi",
            "pro_mat_besi_bitir", "pro_tahil_besi", "pro_tane_besi_toz",
            "kabul_cusse", "kabul_besi_toz"
        ]
        return common_forages + common_grains + besi_factory + common_minerals + custom_added

    elif group == "sut":
        sut_factory = [
            "pro_vira_buzagi", "pro_tutku_buzagi",
            "pro_aktif", "pro_enerji", "pro_4x4", "pro_kanit",
            "pro_41", "pro_cizgi", "pro_balans", "pro_dogus",
            "pro_kuru_donem", "pro_son_60", "pro_duve", "pro_tane_sut_toz",
            "kabul_dira", "kabul_nisan"
        ]
        sut_grains = common_grains + ["soya_kuspesi_44"]
        sut_minerals = common_minerals + ["sodyum_bikarbonat"]
        return common_forages + sut_grains + sut_factory + sut_minerals + custom_added

    elif group == "koyun":
        koyun_forages = ["arpa_samani", "bugday_samani", "yonca_kuru_otu"]
        koyun_factory = [
            "pro_kuzu_yemi", "skor_kuzu_besi", "pro_toklu_besi",
            "pro_taneli_toklu", "pro_koyun_sut"
        ]
        return koyun_forages + common_grains + koyun_factory + common_minerals + custom_added

    return list(FEED_DATABASE.keys())

def get_default_feed_list_for_group(group: str):
    if group == "besi":
        return ["arpa_samani", "yonca_kuru_otu", "misir_silaji", "pro_tosun_besi", "mermer_tozu", "tuz", "vitamin_mineral"]
    elif group == "sut":
        return ["bugday_samani", "yonca_kuru_otu", "misir_silaji", "pro_enerji", "mermer_tozu", "tuz", "sodyum_bikarbonat", "vitamin_mineral"]
    elif group == "koyun":
        return ["arpa_samani", "yonca_kuru_otu", "pro_toklu_besi", "mermer_tozu", "tuz", "vitamin_mineral"]
    return list(FEED_DATABASE.keys())

# Başlangıçta yükle
load_feeds()
