# -*- coding: utf-8 -*-
"""
Telegram Rasyon Robotu (@Rasyonfatih_bot)
Yüksek Mühendis M. Fatih CEYHAN Çiftlik ve Rasyon Yönetim Sistemi

Selçuk Üniversitesi Veteriner Fakültesi standartları ve Doğrusal Programlama (Simplex LP)
ile en düşük maliyetli bilimsel rasyon formülasyonu, Çiftlik Excel (.xlsx) Raporlama Motoru
ve Telegram Üzerinden Tam Otonom Yem & Fiyat Güncelleme Yönetim Sistemi.
"""

import time
import json
import logging
import requests
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Set

from feed_database import (
    FEED_DATABASE,
    get_default_feed_list_for_group,
    get_feed_keys_by_group,
    update_feed_price,
    add_new_custom_feed,
    find_feed_by_fuzzy_name,
    delete_custom_feed,
    reset_to_defaults
)
from requirements import (
    calculate_besi_requirements,
    calculate_sut_requirements,
    calculate_koyun_requirements
)
from optimizer import solve_ration
from ai_adviser import generate_expert_report
from excel_exporter import generate_farm_excel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RasyonBot")

TOKEN = "8630473334:AAH7JsK4K0L5cDyc4EorLFpdariD6TyTeKk"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Kullanıcı oturum durumları
user_sessions: Dict[int, Dict[str, Any]] = {}

def get_session(chat_id: int) -> Dict[str, Any]:
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            "state": "START",
            "group": None,            # 'besi', 'sut', 'koyun'
            "live_weight": 400,       # kg
            "target": None,           # gcaa, süt verimi veya koyun dönemi
            "milk_fat": 3.7,          # % süt yağı
            "selected_feeds": set(),  # set of feed_ids
            "custom_prices": {},      # feed_id: price
            "last_result": None,
            "farm_name": "Çiftlik",
            "head_count": 1,
            "editing_feed_id": None   # Fiyatı güncellenen yem
        }
    return user_sessions[chat_id]

def reset_session(chat_id: int):
    user_sessions[chat_id] = {
        "state": "START",
        "group": None,
        "live_weight": 400,
        "target": None,
        "milk_fat": 3.7,
        "selected_feeds": set(),
        "custom_prices": {},
        "last_result": None,
        "farm_name": "Çiftlik",
        "head_count": 1,
        "editing_feed_id": None
    }
    return user_sessions[chat_id]

# --- Telegram API Çağrıları ---

def tg_send_message(chat_id: int, text: str, reply_markup: dict = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API_URL}/sendMessage", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        return {}

def tg_edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API_URL}/editMessageText", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        logger.error(f"Error editing message {message_id}: {e}")
        return {}

def tg_edit_message_reply_markup(chat_id: int, message_id: int, reply_markup: dict = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "message_id": message_id
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API_URL}/editMessageReplyMarkup", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        logger.error(f"Error editing markup {message_id}: {e}")
        return {}

def tg_answer_callback(callback_query_id: str, text: str = None) -> dict:
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        r = requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"Error answering callback {callback_query_id}: {e}")
        return {}

def tg_send_document(chat_id: int, file_path: str, caption: str = None) -> dict:
    url = f"{API_URL}/sendDocument"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "Markdown"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            r = requests.post(url, data=data, files=files, timeout=40)
            return r.json()
    except Exception as e:
        logger.error(f"Error sending document to {chat_id}: {e}")
        return {}

# --- Klavye Menüleri (Inline Keyboards) ---

def make_start_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🥩 Besi Sığırı Rasyonu", "callback_data": "group_besi"},
                {"text": "🥛 Sütçü İnek Rasyonu", "callback_data": "group_sut"}
            ],
            [
                {"text": "🐑 Koyun / Küçükbaş Rasyonu", "callback_data": "group_koyun"}
            ],
            [
                {"text": "📑 Çiftlik Ziyaret Kaydı & Excel Raporu", "callback_data": "menu_farm_excel"}
            ],
            [
                {"text": "⚙️ Yem & Fiyat Yönetimi (Güncelle / Ekle)", "callback_data": "menu_settings"}
            ],
            [
                {"text": "ℹ️ Bot Hakkında & Nasıl Çalışır?", "callback_data": "about_bot"}
            ]
        ]
    }

def make_settings_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "💰 Yem Fiyatlarını Güncelle", "callback_data": "set_prices_list"}
            ],
            [
                {"text": "➕ Yeni Yem Ekle", "callback_data": "set_add_feed"}
            ],
            [
                {"text": "📋 Tüm Yem & Fiyat Listesini Gör", "callback_data": "set_view_all_prices"}
            ],
            [
                {"text": "🔙 Ana Menü", "callback_data": "back_to_start"}
            ]
        ]
    }

def make_price_edit_list_keyboard():
    """Tüm yemleri tıklanabilir buton olarak listeler."""
    buttons = []
    feed_items = sorted(FEED_DATABASE.items(), key=lambda x: (x[1]["category"], x[1]["name"]))
    
    row = []
    for fid, f in feed_items:
        short_name = f["name"].split("(")[0].strip()
        if len(short_name) > 16:
            short_name = short_name[:16]
        btn_text = f"{short_name}: {f['default_price']:.1f}₺"
        row.append({"text": btn_text, "callback_data": f"editp_{fid}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([{"text": "🔙 Ayarlar Menüsü", "callback_data": "menu_settings"}])
    return {"inline_keyboard": buttons}

def make_weight_keyboard(group: str):
    if group == "besi":
        return {
            "inline_keyboard": [
                [
                    {"text": "300 kg (Besi Başı)", "callback_data": "weight_300"},
                    {"text": "400 kg (Besi Ortası)", "callback_data": "weight_400"}
                ],
                [
                    {"text": "500 kg (Besi Sonu)", "callback_data": "weight_500"},
                    {"text": "550 kg (Ağır Besi)", "callback_data": "weight_550"}
                ],
                [
                    {"text": "✍️ Farklı Kilo (Yazarak Gir)", "callback_data": "weight_custom"}
                ],
                [
                    {"text": "🔙 Ana Menü", "callback_data": "back_to_start"}
                ]
            ]
        }
    elif group == "sut":
        return {
            "inline_keyboard": [
                [
                    {"text": "550 kg (Hafif Irk / Jersey)", "callback_data": "weight_550"},
                    {"text": "600 kg (Standart Simental)", "callback_data": "weight_600"}
                ],
                [
                    {"text": "650 kg (Büyük Holstein)", "callback_data": "weight_650"},
                    {"text": "700 kg (Ağır Damızlık)", "callback_data": "weight_700"}
                ],
                [
                    {"text": "✍️ Farklı Kilo (Yazarak Gir)", "callback_data": "weight_custom"}
                ],
                [
                    {"text": "🔙 Ana Menü", "callback_data": "back_to_start"}
                ]
            ]
        }
    elif group == "koyun":
        return {
            "inline_keyboard": [
                [
                    {"text": "45 kg", "callback_data": "weight_45"},
                    {"text": "55 kg", "callback_data": "weight_55"},
                    {"text": "65 kg", "callback_data": "weight_65"}
                ],
                [
                    {"text": "✍️ Farklı Kilo (Yazarak Gir)", "callback_data": "weight_custom"}
                ],
                [
                    {"text": "🔙 Ana Menü", "callback_data": "back_to_start"}
                ]
            ]
        }

def make_target_keyboard(group: str):
    if group == "besi":
        return {
            "inline_keyboard": [
                [
                    {"text": "1000 g/gün (Normal Artış)", "callback_data": "target_1000"},
                    {"text": "1200 g/gün (İyi Besi)", "callback_data": "target_1200"}
                ],
                [
                    {"text": "1400 g/gün (Hızlı Besi)", "callback_data": "target_1400"},
                    {"text": "1600 g/gün (Maksimum Kazanç)", "callback_data": "target_1600"}
                ],
                [
                    {"text": "✍️ Kendim Yazacağım", "callback_data": "target_custom"}
                ],
                [
                    {"text": "🔙 Kilo Değiştir", "callback_data": "back_to_weight"}
                ]
            ]
        }
    elif group == "sut":
        return {
            "inline_keyboard": [
                [
                    {"text": "20 Litre / gün", "callback_data": "target_20"},
                    {"text": "25 Litre / gün", "callback_data": "target_25"}
                ],
                [
                    {"text": "30 Litre / gün", "callback_data": "target_30"},
                    {"text": "35 Litre / gün", "callback_data": "target_35"}
                ],
                [
                    {"text": "✍️ Kendim Yazacağım", "callback_data": "target_custom"}
                ],
                [
                    {"text": "🔙 Kilo Değiştir", "callback_data": "back_to_weight"}
                ]
            ]
        }
    elif group == "koyun":
        return {
            "inline_keyboard": [
                [
                    {"text": "🐑 Flaşing (Koç Katımı)", "callback_data": "target_flasing"},
                    {"text": "🤰 Erken Gebelik", "callback_data": "target_erken_gebe"}
                ],
                [
                    {"text": "👶 Son Dönem Gebe (İkiz)", "callback_data": "target_son_gebe_ikiz"},
                    {"text": "🥛 Laktasyon (İkiz Emziren)", "callback_data": "target_laktasyon"}
                ],
                [
                    {"text": "🥩 Toklu Besi (250 g/gün)", "callback_data": "target_toklu_besi"}
                ],
                [
                    {"text": "🔙 Kilo Değiştir", "callback_data": "back_to_weight"}
                ]
            ]
        }

def make_feed_selection_keyboard(selected_feeds: Set[str], group: str):
    buttons = []
    feed_keys = get_feed_keys_by_group(group)
    
    row = []
    for fid in feed_keys:
        if fid not in FEED_DATABASE:
            continue
        f = FEED_DATABASE[fid]
        is_sel = fid in selected_feeds
        icon = "✅" if is_sel else "⬜"
        
        name = f["name"]
        short_name = name.replace(" Tohumu", "").replace(" Kuru Otu", " Otu").replace(" (Ezme / Kırma)", " Ezme")
        if len(short_name) > 19:
            short_name = short_name[:19]
            
        btn_text = f"{icon} {short_name}"
        row.append({"text": btn_text, "callback_data": f"toggle_{fid}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    count = len(selected_feeds)
    buttons.append([
        {"text": "🔘 Tümünü Seç", "callback_data": "feeds_select_all"},
        {"text": "⚪ Temizle", "callback_data": "feeds_clear_all"}
    ])
    buttons.append([
        {"text": f"🚀 Seçilen Yemlerle Rasyonu Hesapla ({count} Yem)", "callback_data": "do_calculate"}
    ])
    buttons.append([
        {"text": "🔙 Hedef Değiştir", "callback_data": "back_to_target"},
        {"text": "🔄 Baştan Başla", "callback_data": "back_to_start"}
    ])
    
    return {"inline_keyboard": buttons}

def make_result_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📑 Bu Rasyonu Çiftlik Excel Raporu Yap (.xlsx)", "callback_data": "export_current_to_excel"}
            ],
            [
                {"text": "🌾 Yemleri Değiştirip Tekrar Çöz", "callback_data": "back_to_feed_select"}
            ],
            [
                {"text": "🔄 Yeni Rasyon / Ana Menü", "callback_data": "back_to_start"}
            ]
        ]
    }

# --- Mesaj İşleyiciler (Handlers) ---

def handle_start(chat_id: int):
    reset_session(chat_id)
    text = (
        "👋 **Merhaba! Yapay Zekâ Destekli Rasyon Robotuna Hoş Geldiniz!**\n\n"
        "Bu sistem **Yüksek Mühendis M. Fatih CEYHAN** tarafından hazırlanmıştır. "
        "İşletmenizdeki mevcut yemlere göre en düşük maliyetli, bilimsel ve dengeli rasyonu hazırlar.\n\n"
        "Lütfen yapmak istediğiniz işlemi seçin:"
    )
    tg_send_message(chat_id, text, make_start_keyboard())

def prompt_feed_selection(chat_id: int, message_id: int = None):
    session = get_session(chat_id)
    group = session.get("group") or "besi"
    bw = session.get("live_weight") or 400
    target = session.get("target") or (1200 if group == "besi" else (25 if group == "sut" else "toklu_besi"))
    
    group_titles = {
        "besi": "🥩 BESİ SIĞIRI YEMLERİ (Çiftlik Yemleri + PROYEM Besi & Buzağı)",
        "sut": "🥛 SÜT SIĞIRI YEMLERİ (Çiftlik Yemleri + PROYEM Süt & Buzağı)",
        "koyun": "🐑 KÜÇÜKBAŞ YEMLERİ (Çiftlik Yemleri + PROYEM Kuzu/Toklu)"
    }
    
    if group == "besi":
        target_str = f"{target} g/gün Canlı Ağırlık Artışı"
    elif group == "sut":
        target_str = f"{target} Litre/gün Günlük Süt Verimi"
    elif group == "koyun":
        target_str = f"{target}"
    else:
        target_str = f"{target}"
        
    text = (
        f"🎯 **Hayvan Bilgileri:**\n"
        f"• **Grup:** `{(group or 'BESİ').upper()}`\n"
        f"• **Canlı Ağırlık:** `{bw} kg`\n"
        f"• **Hedef:** `{target_str}`\n\n"
        f"🌾 **Adım 3: {group_titles.get(group, 'İşletmenizdeki Yemleri Seçin')}**\n"
        f"Aşağıdaki listeden elinizde bulunan çiftlik kaba/kesif yemleri ve hazır fabrika yemlerini "
        f"dokunarak işaretleyin (`✅` seçili, `⬜` seçili değil).\n\n"
        f"Seçiminiz bitince en alttaki **🚀 Seçilen Yemlerle Rasyonu Hesapla** butonuna basın:"
    )
    kb = make_feed_selection_keyboard(session["selected_feeds"], group)
    if message_id:
        tg_edit_message(chat_id, message_id, text, kb)
    else:
        tg_send_message(chat_id, text, kb)

def handle_quick_price_command(chat_id: int, text: str, state: str) -> bool:
    """
    Kullanıcının Telegram'dan yazdığı 'fiyat arpa 9.5', 'arpa 9.5', 'fiyat saman 2.5' gibi
    hızlı komutları yakalar ve veritabanını anında günceller.
    """
    clean_text = text.lower().strip()
    
    # 1. 'fiyatlar' veya 'liste' yazıldığında tüm listeyi göster
    if clean_text in ["fiyatlar", "yemler", "liste", "/fiyatlar", "/yemler", "/liste"]:
        txt_all = ["📋 **GÜNCEL YEM VE FİYAT VERİTABANI:**\n"]
        for fid, f in sorted(FEED_DATABASE.items(), key=lambda x: (x[1]["category"], x[1]["name"])):
            txt_all.append(f"• **{f['name']}:** `{f['default_price']:.2f} ₺/kg` ({f['category']})")
        txt_all.append("\n💡 _Fiyat değiştirmek için: `fiyat <yem_adı> <yeni_fiyat>` yazabilirsiniz. (Örn: `fiyat arpa 9.5`)_")
        tg_send_message(chat_id, "\n".join(txt_all), make_settings_keyboard())
        return True

    # 2. 'fiyat <yem> <fiyat>' veya 'arpa 9.5' (START veya SETTINGS durumunda)
    match = re.match(r"^(?:fiyat|fiyatlar|ücret)\s+([a-zA-ZçğıöşüÇĞİÖŞÜ0-9\s\-_]+?)\s+([0-9]+(?:[\.,][0-9]+)?)\s*(?:tl|tl\/kg|₺)?$", clean_text)
    if not match and state in ["START", "SETTINGS", None]:
        # 'arpa 9.5' veya 'tosun 13.5' gibi doğrudan giriş
        match = re.match(r"^([a-zA-ZçğıöşüÇĞİÖŞÜ\s\-_]+?)\s*(?:=|\:|\s+)\s*([0-9]+(?:[\.,][0-9]+)?)\s*(?:tl|tl\/kg|₺)?$", clean_text)

    if match:
        feed_name_part = match.group(1).strip()
        price_str = match.group(2).replace(",", ".")
        try:
            new_p = float(price_str)
            if new_p <= 0 or new_p > 500:
                return False
            fid, f_obj = find_feed_by_fuzzy_name(feed_name_part)
            if fid:
                update_feed_price(fid, new_p)
                tg_send_message(
                    chat_id,
                    f"✅ **FİYAT GÜNCELLENDİ VE KAYDEDİLDİ!**\n\n"
                    f"🌾 **Yem:** `{f_obj['name']}`\n"
                    f"💰 **Yeni Fiyat:** `{new_p:.2f} ₺/kg`\n\n"
                    f"_Bu değişiklik kalıcı olarak kaydedilmiştir; IDE kapalı olsa bile yapacağınız tüm rasyonlarda ve Excel çıktılarında bu fiyat kullanılacaktır._",
                    make_settings_keyboard()
                )
                return True
            else:
                tg_send_message(
                    chat_id,
                    f"⚠️ '{feed_name_part}' isminde bir yem bulunamadı.\n"
                    f"Mevcut yem isimlerini görmek için **fiyatlar** yazabilir veya menüyü kullanabilirsiniz."
                )
                return True
        except ValueError:
            pass

    # 3. 'sil <yem_adi>' komutu
    if clean_text.startswith("sil ") or clean_text.startswith("yem sil "):
        feed_name_part = clean_text.replace("yem sil ", "").replace("sil ", "").strip()
        fid, f_obj = find_feed_by_fuzzy_name(feed_name_part)
        if fid:
            del_name = f_obj["name"]
            delete_custom_feed(fid)
            tg_send_message(
                chat_id,
                f"🗑️ **{del_name}** veritabanından kaldırıldı.",
                make_settings_keyboard()
            )
            return True
        else:
            tg_send_message(chat_id, f"⚠️ Silinecek '{feed_name_part}' isimli yem bulunamadı.")
            return True

    return False

def handle_text(chat_id: int, text: str):
    session = get_session(chat_id)
    state = session["state"]
    
    # 1. Hızlı komut kontrolü (Örn: 'fiyat arpa 9.5', 'arpa 9.5', 'fiyatlar')
    if handle_quick_price_command(chat_id, text, state):
        return

    if text.startswith("/start"):
        handle_start(chat_id)
        return
    elif text.startswith("/fiyat") or text.startswith("/ayarlar") or text.startswith("/guncelle"):
        text_menu = (
            "⚙️ **YEM VE FİYAT YÖNETİM MERKEZİ**\n\n"
            "Buradan işletmenizdeki yem fiyatlarını değiştirebilir, yeni yem ekleyebilir veya güncel listeyi görebilirsiniz.\n"
            "Tüm değişiklikler bot kapansa bile **kalıcı olarak** saklanır."
        )
        tg_send_message(chat_id, text_menu, make_settings_keyboard())
        return
    elif text.startswith("/help") or text.startswith("/yardim"):
        about_text = (
            "📖 **Rasyonfatih_bot Kullanım Kılavuzu**\n\n"
            "Bu sistem **Yüksek Mühendis M. Fatih CEYHAN** tarafından hazırlanmıştır.\n\n"
            "⚡ **Hızlı Telegram Komutları:**\n"
            "• `fiyat arpa 9.5` veya `arpa 9.5` -> Arpa fiyatını anında 9.5 ₺ yapar.\n"
            "• `fiyat saman 2.2` -> Saman fiyatını anında 2.2 ₺ yapar.\n"
            "• `fiyat tosun 12.5` -> Pro Tosun Besi fiyatını günceller.\n"
            "• `fiyatlar` -> Tüm yemlerin güncel fiyat listesini döker.\n"
            "• `/ayarlar` -> Yem ve fiyat yönetim menüsünü açar.\n\n"
            "Her zaman `/start` yazarak ana menüye dönebilirsiniz."
        )
        tg_send_message(chat_id, about_text, make_start_keyboard())
        return
        tg_send_message(chat_id, about_text, make_start_keyboard())
        return
        
    # Tek Yem Fiyatı Güncelleme Bekleyişi
    if state == "WAIT_SINGLE_PRICE":
        fid = session.get("editing_feed_id")
        if fid and fid in FEED_DATABASE:
            try:
                new_p = float(text.replace(",", ".").strip())
                if new_p <= 0 or new_p > 500:
                    tg_send_message(chat_id, "⚠️ Lütfen 0 ile 500 ₺ arasında geçerli bir fiyat girin:")
                    return
                update_feed_price(fid, new_p)
                f_name = FEED_DATABASE[fid]["name"]
                session["state"] = "START"
                tg_send_message(
                    chat_id,
                    f"✅ **{f_name}** fiyatı başarıyla **{new_p:.2f} ₺/kg** olarak güncellendi ve diske kaydedildi!",
                    make_settings_keyboard()
                )
            except ValueError:
                tg_send_message(chat_id, "⚠️ Lütfen sadece sayı girin (Örn: `9.5` veya `12`):")
        return

    # Yeni Yem Ekleme Metni
    elif state == "WAIT_NEW_FEED_DATA":
        # Format: Ad, Kategori, KM, HP, ME, Fiyat
        raw = text.strip()
        data = {}
        # Parse key-value or comma separated
        parts = re.split(r"[,;\n]", raw)
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if "ad" in k or "isim" in k: data["name"] = v
                elif "kat" in k: data["category"] = v
                elif "km" in k: data["KM"] = float(v.replace(",", "."))
                elif "hp" in k or "protein" in k: data["HP"] = float(v.replace(",", "."))
                elif "me" in k or "enerji" in k: data["ME"] = float(v.replace(",", "."))
                elif "fiyat" in k: data["default_price"] = float(v.replace(",", "."))
                
        if "name" in data and ("HP" in data or "ME" in data):
            fid = add_new_custom_feed(data)
            session["state"] = "START"
            tg_send_message(
                chat_id,
                f"🎉 **YENİ YEM BAŞARIYLA EKLENDİ!**\n\n"
                f"🌾 **Yem:** `{data['name']}`\n"
                f"📂 **Kategori:** `{data.get('category', 'Genel Yem')}`\n"
                f"🧪 **Besin Değerleri:** KM: %{data.get('KM', 88)} | HP: %{data.get('HP', 14)} | ME: {data.get('ME', 2.5)} Mcal\n"
                f"💰 **Fiyat:** `{data.get('default_price', 10.0):.2f} ₺/kg`\n\n"
                f"_Bu yem artık rasyon seçim listelerinizde görünür ve kullanılabilir!_",
                make_start_keyboard()
            )
            return
        else:
            tg_send_message(
                chat_id,
                "⚠️ Girdiğiniz bilgiler tam anlaşılamadı. Lütfen şu formatta yazıp tekrar deneyin:\n\n"
                "`Ad: Korunga Kuru Otu, Kategori: Kaba Yem, KM: 88, HP: 15, ME: 2.1, Fiyat: 7.5`"
            )
            return

    # Canlı ağırlık elle girişi
    elif state == "WAIT_WEIGHT":
        try:
            val = float(text.replace(",", "."))
            if val < 10 or val > 1200:
                tg_send_message(chat_id, "⚠️ Lütfen 10 ile 1200 kg arasında geçerli bir canlı ağırlık girin:")
                return
            session["live_weight"] = val
            session["state"] = "SELECT_TARGET"
            tg_send_message(chat_id, f"✅ Canlı Ağırlık: `{val} kg` olarak kaydedildi.\n\nŞimdi hedefinizi belirleyin:", make_target_keyboard(session["group"]))
        except ValueError:
            tg_send_message(chat_id, "⚠️ Lütfen sadece sayı olarak kilo girin (Örn: `420` veya `550`):")
            
    # Hedef verim elle girişi
    elif state == "WAIT_TARGET":
        group = session["group"]
        try:
            val = float(text.replace(",", "."))
            if group == "besi":
                if val < 400 or val > 2500:
                    tg_send_message(chat_id, "⚠️ Besi için günlük artış 400 ile 2500 g/gün arasında olmalıdır. Tekrar girin:")
                    return
                session["target"] = val
            elif group == "sut":
                if val < 5 or val > 70:
                    tg_send_message(chat_id, "⚠️ Süt verimi 5 ile 70 litre/gün arasında olmalıdır. Tekrar girin:")
                    return
                session["target"] = val
            session["state"] = "SELECT_FEEDS"
            prompt_feed_selection(chat_id)
        except ValueError:
            tg_send_message(chat_id, "⚠️ Lütfen sadece sayı girin (Örn: Besi için `1300`, Süt için `28`):")
            
    # Excel Raporu için Çiftlik Adı Girişi
    elif state == "WAIT_FARM_NAME":
        farm_name = text.strip()
        if not farm_name:
            farm_name = "Örnek Çiftlik"
        session["farm_name"] = farm_name
        session["state"] = "WAIT_HEAD_COUNT"
        tg_send_message(
            chat_id,
            f"✅ İşletme Adı: **{farm_name}** kaydedildi.\n\n"
            f"🔢 **Bu grupta toplam kaç baş hayvan var?**\n"
            f"(Örn: `20`, `50`, `100` vb. - Sürü toplam günlük ve 30 günlük yem tüketimi buna göre hesaplanacaktır):"
        )
        
    # Excel Raporu için Hayvan Sayısı Girişi
    elif state == "WAIT_HEAD_COUNT":
        try:
            count = int(text.replace(".", "").replace(",", "").strip())
            if count <= 0 or count > 50000:
                tg_send_message(chat_id, "⚠️ Lütfen 1 ile 50.000 arasında geçerli bir hayvan sayısı girin:")
                return
            session["head_count"] = count
            session["state"] = "DONE_EXCEL"
            send_farm_excel_report(chat_id)
        except ValueError:
            tg_send_message(chat_id, "⚠️ Lütfen sadece tam sayı olarak hayvan sayısını girin (Örn: `50`):")
            
    else:
        tg_send_message(chat_id, "Lütfen menü butonlarını kullanarak ilerleyin ya da baştan başlamak için `/start` yazın.", make_start_keyboard())

def send_farm_excel_report(chat_id: int):
    session = get_session(chat_id)
    last_res = session.get("last_result")
    
    if not last_res or not last_res.get("success"):
        tg_send_message(chat_id, "⚠️ Önce bir rasyon hesaplamanız gerekmektedir. Lütfen menüden hayvan grubunuzu seçip rasyonu oluşturun.", make_start_keyboard())
        return
        
    tg_send_message(chat_id, "⏳ _Çiftlik rasyon ve sürü yönetim Excel dosyası hazırlanıyor..._")
    
    group = session.get("group") or "besi"
    grp_map = {"besi": "Besi Sığırı", "sut": "Sütçü İnek", "koyun": "Koyun / Küçükbaş"}
    
    target = session.get("target")
    if group == "besi":
        target_str = f"{target} g/gün Canlı Ağırlık Artışı"
    elif group == "sut":
        target_str = f"{target} Litre/gün Günlük Süt Verimi"
    elif group == "koyun":
        target_str = f"{target}"
    else:
        target_str = str(target)
        
    farm_data = {
        "farm_name": session.get("farm_name", "Çiftlik"),
        "visit_date": time.strftime("%d.%m.%Y"),
        "head_count": session.get("head_count", 1),
        "group": grp_map.get(group, group),
        "live_weight": session.get("live_weight", 450),
        "target_str": target_str,
        "daily_gain_grams": target if group == "besi" else 0,
        "milk_yield_kg": target if group == "sut" else 0,
        "result": last_res
    }
    
    try:
        excel_path = generate_farm_excel(farm_data)
        caption = (
            f"✅ **ÇİFTLİK RASYON VE SÜRÜ RAPORU HAZIRLANDI!**\n\n"
            f"🏛 **İşletme:** `{farm_data['farm_name']}`\n"
            f"🐂 **Sürü Bilgisi:** {farm_data['group']} ({farm_data['head_count']} Baş)\n"
            f"👨‍💼 **Onaylayan:** Yüksek Mühendis M. Fatih CEYHAN\n\n"
            f"📊 _Excel dosyasında hayvan başı rasyon, sürü günlük/aylık yem tonajı, maliyet analizi ve besin dengesi detaylandırılmıştır._"
        )
        tg_send_document(chat_id, excel_path, caption=caption)
        tg_send_message(chat_id, "Başka bir işlem yapmak için menüyü kullanabilirsiniz:", make_result_keyboard())
    except Exception as e:
        logger.error(f"Excel export error: {e}", exc_info=True)
        tg_send_message(chat_id, f"❌ Excel raporu oluşturulurken hata meydana geldi: {e}")

def handle_callback(chat_id: int, message_id: int, callback_data: str, query_id: str):
    session = get_session(chat_id)
    
    # 1. Ana Menü ve Grup Seçimi
    if callback_data.startswith("group_"):
        tg_answer_callback(query_id)
        grp = callback_data.replace("group_", "")
        session["group"] = grp
        session["selected_feeds"] = set(get_default_feed_list_for_group(grp))
        session["state"] = "SELECT_WEIGHT"
        
        name_map = {"besi": "🥩 Besi Sığırı", "sut": "🥛 Sütçü İnek", "koyun": "🐑 Koyun / Küçükbaş"}
        text = f"Harika! **{name_map.get(grp)}** seçildi.\n\nLütfen hayvanın ortalama **canlı ağırlığını (kg)** seçin veya kendiniz girin:"
        tg_edit_message(chat_id, message_id, text, make_weight_keyboard(grp))
        
    elif callback_data == "menu_settings":
        tg_answer_callback(query_id)
        text = (
            "⚙️ **YEM VE FİYAT YÖNETİM MERKEZİ**\n\n"
            "Buradan yapacağınız değişiklikler sunucuya kalıcı olarak kaydedilir. "
            "IDE kapalı olsa dahi telefonunuzdan dilediğiniz zaman fiyatları güncelleyebilir veya yeni yem ekleyebilirsiniz.\n\n"
            "Lütfen yapmak istediğiniz işlemi seçin:"
        )
        tg_edit_message(chat_id, message_id, text, make_settings_keyboard())
        
    elif callback_data == "set_prices_list":
        tg_answer_callback(query_id)
        text = (
            "💰 **Fiyatını Değiştirmek İstediğiniz Yeme Dokunun:**\n\n"
            "_Aşağıdaki listeden bir yeme dokunduğunuzda sizden yeni kg fiyatı istenecektir._\n\n"
            "💡 _İpucu: Dilerseniz sohbete doğrudan `fiyat arpa 9.5` veya `fiyat saman 2.2` yazarak da anında güncelleyebilirsiniz!_"
        )
        tg_edit_message(chat_id, message_id, text, make_price_edit_list_keyboard())
        
    elif callback_data.startswith("editp_"):
        tg_answer_callback(query_id)
        fid = callback_data.replace("editp_", "")
        if fid in FEED_DATABASE:
            f = FEED_DATABASE[fid]
            session["editing_feed_id"] = fid
            session["state"] = "WAIT_SINGLE_PRICE"
            text = (
                f"💰 **Fiyat Güncelleme:**\n\n"
                f"🌾 **Yem:** `{f['name']}`\n"
                f"🏷️ **Mevcut Fiyat:** `{f['default_price']:.2f} ₺/kg`\n\n"
                f"✍️ Lütfen yeni **kg fiyatını (TL)** yazıp gönderin (Örn: `9.5` veya `12`):"
            )
            tg_edit_message(chat_id, message_id, text)
            
    elif callback_data == "set_add_feed":
        tg_answer_callback(query_id)
        session["state"] = "WAIT_NEW_FEED_DATA"
        text = (
            "➕ **YENİ YEM EKLEME FORMU**\n\n"
            "Eklemek istediğiniz yeni yemin bilgilerini lütfen şu formatta tek mesaj olarak yazıp gönderin:\n\n"
            "`Ad: Korunga Kuru Otu, Kategori: Kaba Yem, KM: 88, HP: 15, ME: 2.1, Fiyat: 7.5`\n\n"
            "*(Kategori olarak: `Kaba Yem`, `Enerji Yemi`, `Protein Yemi`, `Fabrika Besi Yemi`, `Fabrika Süt Yemi` yazabilirsiniz)*"
        )
        tg_edit_message(chat_id, message_id, text)
        
    elif callback_data == "set_view_all_prices":
        tg_answer_callback(query_id)
        txt_all = ["📋 **GÜNCEL YEM VE FİYAT VERİTABANI:**\n"]
        for fid, f in sorted(FEED_DATABASE.items(), key=lambda x: (x[1]["category"], x[1]["name"])):
            txt_all.append(f"• **{f['name']}:** `{f['default_price']:.2f} ₺/kg` ({f['category']})")
        txt_all.append("\n_Fiyatları değiştirmek için `fiyat <yem_adı> <yeni_fiyat>` yazabilirsiniz._")
        tg_edit_message(chat_id, message_id, "\n".join(txt_all), make_settings_keyboard())

    elif callback_data == "menu_farm_excel":
        tg_answer_callback(query_id)
        if session.get("last_result") and session["last_result"].get("success"):
            session["state"] = "WAIT_FARM_NAME"
            text = (
                "📑 **Çiftlik Ziyaret ve Rasyon Excel Raporu**\n\n"
                "Hesaplanan rasyonu çiftliğe özel resmi bir Excel tablosuna (.xlsx) dönüştüreceğiz.\n\n"
                "🏷️ **Lütfen Çiftlik / İşletme Adını Girin:**\n"
                "(Örn: `Bereket Besi Çiftliği` veya `Ahmet Yılmaz Süt Çiftliği`)"
            )
            tg_edit_message(chat_id, message_id, text)
        else:
            session["state"] = "SELECT_ANIMAL_FOR_EXCEL"
            text = (
                "📑 **Çiftlik Ziyaret ve Rasyon Excel Raporu**\n\n"
                "Çiftlik için Excel raporu oluşturmak üzere önce hayvan grubunu seçin:\n"
                "Sistem rasyonu çözüp otomatik olarak sürü mevcuduyla Excel'e dökecektir."
            )
            tg_edit_message(chat_id, message_id, text, make_start_keyboard())
            
    elif callback_data == "export_current_to_excel":
        tg_answer_callback(query_id)
        session["state"] = "WAIT_FARM_NAME"
        text = (
            "📑 **Çiftlik Excel Raporu Oluşturma**\n\n"
            "🏷️ **Lütfen Ziyaret Ettiğiniz Çiftlik / İşletme Adını Girin:**\n"
            "(Örn: `Yılmaz Besi Çiftliği` veya `Özlem Süt Çiftliği`)"
        )
        tg_send_message(chat_id, text)
        
    elif callback_data == "about_bot":
        tg_answer_callback(query_id)
        about_text = (
            "ℹ️ **Rasyonfatih_bot Hakkında**\n\n"
            "Bu sistem **Yüksek Mühendis M. Fatih CEYHAN** tarafından hazırlanmıştır.\n\n"
            "🔬 **Özellikler:**\n"
            "• **Selçuk Üniversitesi Veteriner Fakültesi** ve **NRC** bilimsel standartları\n"
            "• **Doğrusal Programlama (Simplex LP)** ile en ucuz maliyet garantisi\n"
            "• **Telegram Üzerinden Fiyat & Yem Yönetimi:** Dilediğiniz an cepten yem fiyatlarını değiştirebilir, yeni yem ekleyebilirsiniz.\n"
            "• **Excel (.xlsx) Sürü Tablosu:** Sürünün 30 günlük yem tonaj ihtiyacını ve maliyet tablosunu tek tıkla indirir.\n\n"
            "Hemen başlamak için aşağıdaki menüden hayvan grubunuzu seçin:"
        )
        tg_edit_message(chat_id, message_id, about_text, make_start_keyboard())
        
    elif callback_data == "back_to_start":
        tg_answer_callback(query_id)
        reset_session(chat_id)
        text = (
            "👋 **Merhaba! Yapay Zekâ Destekli Rasyon Robotuna Hoş Geldiniz!**\n\n"
            "Bu sistem **Yüksek Mühendis M. Fatih CEYHAN** tarafından hazırlanmıştır. "
            "İşletmenizdeki mevcut yemlere göre en düşük maliyetli, bilimsel ve dengeli rasyonu hazırlar.\n\n"
            "Lütfen yapmak istediğiniz işlemi seçin:"
        )
        tg_edit_message(chat_id, message_id, text, make_start_keyboard())
        
    # 2. Canlı Ağırlık Seçimi
    elif callback_data.startswith("weight_"):
        tg_answer_callback(query_id)
        val_str = callback_data.replace("weight_", "")
        if val_str == "custom":
            session["state"] = "WAIT_WEIGHT"
            tg_edit_message(chat_id, message_id, "✍️ Lütfen hayvanın canlı ağırlığını klavyeden kg cinsinden yazıp gönderin (Örn: `420` veya `580`):")
        else:
            session["live_weight"] = float(val_str)
            session["state"] = "SELECT_TARGET"
            tg_edit_message(chat_id, message_id, f"✅ Canlı Ağırlık: `{val_str} kg`\n\nŞimdi hedefinizi belirleyin:", make_target_keyboard(session["group"]))
            
    elif callback_data == "back_to_weight":
        tg_answer_callback(query_id)
        grp = session.get("group") or "besi"
        session["state"] = "SELECT_WEIGHT"
        tg_edit_message(chat_id, message_id, "Lütfen canlı ağırlığı seçin:", make_weight_keyboard(grp))
        
    # 3. Hedef Verim Seçimi -> Doğrudan Yem Seçim Ekranına Geçiş
    elif callback_data.startswith("target_"):
        tg_answer_callback(query_id)
        val_str = callback_data.replace("target_", "")
        grp = session.get("group") or "besi"
        if val_str == "custom":
            session["state"] = "WAIT_TARGET"
            if grp == "besi":
                msg = "✍️ Lütfen hedeflenen günlük canlı ağırlık artışını gram cinsinden yazıp gönderin (Örn: `1250` veya `1500`):"
            elif grp == "sut":
                msg = "✍️ Lütfen günlük hedeflenen süt miktarını litre cinsinden yazıp gönderin (Örn: `26` veya `32`):"
            else:
                msg = "Lütfen hedefinizi yazın:"
            tg_edit_message(chat_id, message_id, msg)
        else:
            if grp == "besi" or grp == "sut":
                session["target"] = float(val_str)
            else:
                session["target"] = val_str
            session["state"] = "SELECT_FEEDS"
            prompt_feed_selection(chat_id, message_id=message_id)
            
    elif callback_data == "back_to_target":
        tg_answer_callback(query_id)
        grp = session.get("group") or "besi"
        session["state"] = "SELECT_TARGET"
        tg_edit_message(chat_id, message_id, "Lütfen hedefinizi seçin:", make_target_keyboard(grp))

    elif callback_data == "back_to_feed_select":
        tg_answer_callback(query_id)
        session["state"] = "SELECT_FEEDS"
        prompt_feed_selection(chat_id, message_id=message_id)
        
    # 4. Yem Seçimi Toggle Butonları
    elif callback_data.startswith("toggle_"):
        fid = callback_data.replace("toggle_", "")
        if fid in session["selected_feeds"]:
            session["selected_feeds"].remove(fid)
            status_text = "Çıkarıldı"
        else:
            session["selected_feeds"].add(fid)
            status_text = "Eklendi"
        tg_answer_callback(query_id, f"{FEED_DATABASE[fid]['name']} {status_text}")
        
        kb = make_feed_selection_keyboard(session["selected_feeds"], session.get("group") or "besi")
        tg_edit_message_reply_markup(chat_id, message_id, kb)
        
    elif callback_data == "feeds_select_all":
        tg_answer_callback(query_id, "Tüm yemler seçildi")
        grp = session.get("group") or "besi"
        group_keys = get_feed_keys_by_group(grp)
        session["selected_feeds"] = set(group_keys)
        kb = make_feed_selection_keyboard(session["selected_feeds"], grp)
        tg_edit_message_reply_markup(chat_id, message_id, kb)
        
    elif callback_data == "feeds_clear_all":
        tg_answer_callback(query_id, "Tüm seçimler temizlendi")
        grp = session.get("group") or "besi"
        session["selected_feeds"] = set()
        kb = make_feed_selection_keyboard(session["selected_feeds"], grp)
        tg_edit_message_reply_markup(chat_id, message_id, kb)

    # 5. Rasyon Hesaplama
    elif callback_data == "do_calculate":
        selected_list = list(session["selected_feeds"])
        
        if len(selected_list) == 0:
            tg_answer_callback(query_id, "⚠️ Lütfen en az bir yem seçin!", text="Lütfen en az bir yem seçin!")
            tg_send_message(chat_id, "⚠️ **Uyarı:** Hiçbir yem seçmediniz. Lütfen işletmenizde bulunan yemleri yukarıdaki listeden işaretleyin.")
            return
            
        has_forage = any(FEED_DATABASE[fid]["is_forage"] for fid in selected_list if fid in FEED_DATABASE)
        if not has_forage:
            tg_answer_callback(query_id, "⚠️ En az bir kaba yem (saman, yonca, silaj) seçmelisiniz!")
            tg_send_message(chat_id, "⚠️ **Uyarı:** Rasyonda hiç kaba yem (saman, yonca, silaj vb.) seçilmedi. Rumen sağlığı ve asidoz önleme için en az bir kaba yem seçmelisiniz.")
            return

        tg_answer_callback(query_id, "Rasyon hesaplanıyor...")
        
        grp = session.get("group") or "besi"
        bw = session.get("live_weight") or 400
        target = session.get("target") or (1200 if grp == "besi" else (25 if grp == "sut" else "toklu_besi"))
        
        # Gereksinimleri hesapla
        if grp == "besi":
            reqs = calculate_besi_requirements(bw, float(target))
        elif grp == "sut":
            reqs = calculate_sut_requirements(bw, float(target), session.get("milk_fat", 3.7))
        elif grp == "koyun":
            reqs = calculate_koyun_requirements(bw, str(target))
        else:
            reqs = calculate_besi_requirements(400, 1200)
            
        tg_send_message(chat_id, "⏳ _Seçtiğiniz yemlerle rasyon optimize ediliyor, yapay zekâ analizleri hazırlanıyor..._")
        
        result = solve_ration(reqs, feed_ids=selected_list, custom_prices=session.get("custom_prices"))
        session["last_result"] = result
        
        report_text = generate_expert_report(result)
        tg_send_message(chat_id, report_text, make_result_keyboard())

# --- Bulut Sunucu Sağlık Kontrolü (Cloud Health Check) ---

class CloudHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = (
            "<html><head><title>Rasyon Robotu</title></head>"
            "<body style='font-family:sans-serif; text-align:center; padding:50px; background:#f4f6f9;'>"
            "<h1 style='color:#2e7d32;'>🌱 Rasyonfatih_bot 7/24 Aktif!</h1>"
            "<p><b>Yüksek Mühendis M. Fatih CEYHAN</b> Çiftlik ve Rasyon Yönetim Sistemi</p>"
            "<p>Telegram Bot: <a href='https://t.me/Rasyonfatih_bot'>@Rasyonfatih_bot</a></p>"
            "<p style='color:#666;'>Durum: Aktif ve İstekleri Dinliyor...</p>"
            "</body></html>"
        )
        self.wfile.write(html.encode('utf-8'))
        
    def log_message(self, format, *args):
        pass

def start_cloud_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), CloudHealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Bulut Web Portu Aktif Edildi: {port}")
    except Exception as e:
        logger.warning(f"Web port dinleme başlatılamadı: {e}")

# --- Bot Long-Polling Döngüsü ---

def run_bot():
    start_cloud_health_server()
    logger.info("Rasyon Telegram Botu Başlatılıyor...")
    offset = 0
    
    try:
        me = requests.get(f"{API_URL}/getMe", timeout=10).json()
        logger.info(f"Bot Başarıyla Bağlandı: @{me.get('result', {}).get('username')}")
    except Exception as e:
        logger.error(f"Bot bağlantı hatası: {e}")
        return

    while True:
        try:
            r = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        
                        if "message" in update:
                            msg = update["message"]
                            chat_id = msg["chat"]["id"]
                            text = msg.get("text", "")
                            if text:
                                handle_text(chat_id, text)
                                
                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            query_id = cb["id"]
                            chat_id = cb["message"]["chat"]["id"]
                            message_id = cb["message"]["message_id"]
                            cb_data = cb.get("data", "")
                            handle_callback(chat_id, message_id, cb_data, query_id)
            else:
                logger.warning(f"getUpdates error: HTTP {r.status_code}")
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ağ bağlantı uyarısı: {e}")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Beklenmeyen döngü hatası: {e}", exc_info=True)
            time.sleep(2)

if __name__ == "__main__":
    run_bot()
