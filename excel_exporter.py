# -*- coding: utf-8 -*-
"""
Çiftlik Rasyon Raporu Excel Üreteci (Excel Exporter)
Yüksek Mühendis M. Fatih CEYHAN Çiftlik ve Rasyon Raporu
"""

import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_farm_excel(farm_data: dict) -> str:
    """
    Çiftlik ve rasyon verilerinden profesyonel, renkli ve resmi formatta
    bir Excel raporu oluşturup dosya yolunu döner.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Rasyon ve Sürü Raporu"
    ws.views.sheetView[0].showGridLines = True
    
    # Renk Paleti (Kurumsal Zirai Yeşili & Lacivert)
    COLOR_HEADER_BG = "1E4D2B"       # Koyu Zirai Yeşil
    COLOR_HEADER_TEXT = "FFFFFF"     # Beyaz
    COLOR_SECTION_BG = "D8EAD3"      # Açık Yeşil
    COLOR_ACCENT = "EAF2F8"          # Açık Mavi/Gri zebra
    COLOR_TOTAL_BG = "FFF2CC"        # Açık Sarı Vurgu
    COLOR_BORDER = "B0BEC5"          # Yumuşak gri kenarlık
    
    font_title = Font(name="Calibri", size=16, bold=True, color="1E4D2B")
    font_subtitle = Font(name="Calibri", size=11, bold=True, color="455A64")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E4D2B")
    font_tbl_header = Font(name="Calibri", size=11, bold=True, color=COLOR_HEADER_TEXT)
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    font_note = Font(name="Calibri", size=10, italic=True, color="546E7A")
    
    fill_tbl_header = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
    fill_section = PatternFill(start_color=COLOR_SECTION_BG, end_color=COLOR_SECTION_BG, fill_type="solid")
    fill_zebra = PatternFill(start_color=COLOR_ACCENT, end_color=COLOR_ACCENT, fill_type="solid")
    fill_total = PatternFill(start_color=COLOR_TOTAL_BG, end_color=COLOR_TOTAL_BG, fill_type="solid")
    
    thin_side = Side(style="thin", color=COLOR_BORDER)
    med_side = Side(style="medium", color=COLOR_HEADER_BG)
    double_side = Side(style="double", color=COLOR_HEADER_BG)
    
    border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    border_total = Border(top=thin_side, bottom=double_side, left=thin_side, right=thin_side)
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    # 1. Başlık Alanı
    ws.merge_cells("A1:G1")
    ws["A1"] = "ÇİFTLİK RASYON VE SÜRÜ YÖNETİM RAPORU"
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center
    ws.row_dimensions[1].height = 28
    
    ws.merge_cells("A2:G2")
    ws["A2"] = "Hazırlayan: Yüksek Mühendis M. Fatih CEYHAN | Hayvan Besleme ve Rasyon Uzmanı"
    ws["A2"].font = font_subtitle
    ws["A2"].alignment = align_center
    ws.row_dimensions[2].height = 20
    
    # 2. Çiftlik ve Ziyaret Bilgileri Kutusu
    r = 4
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"] = "  📌 ÇİFTLİK VE İŞLETME BİLGİLERİ"
    ws[f"A{r}"].font = font_section
    ws[f"A{r}"].fill = fill_section
    ws.row_dimensions[r].height = 24
    
    farm_name = farm_data.get("farm_name", "Belirtilmedi")
    visit_date = farm_data.get("visit_date", datetime.now().strftime("%d.%m.%Y"))
    head_count = int(farm_data.get("head_count", 1))
    group_name = farm_data.get("group", "Besi Sığırı")
    live_weight = farm_data.get("live_weight", 450)
    target_str = farm_data.get("target_str", "-")
    
    meta_rows = [
        ("İşletme / Çiftlik Adı:", farm_name, "Rapor Tarihi:", visit_date),
        ("Hayvan Grubu / Irkı:", group_name, "Toplam Hayvan Sayısı:", f"{head_count} Baş"),
        ("Ortalama Canlı Ağırlık:", f"{live_weight} kg", "Hedef Verim / Artış:", target_str),
    ]
    
    r += 1
    for m in meta_rows:
        ws[f"A{r}"] = m[0]
        ws[f"A{r}"].font = font_bold
        ws.merge_cells(f"B{r}:C{r}")
        ws[f"B{r}"] = m[1]
        ws[f"B{r}"].font = font_regular
        
        ws[f"E{r}"] = m[2]
        ws[f"E{r}"].font = font_bold
        ws.merge_cells(f"F{r}:G{r}")
        ws[f"F{r}"] = m[3]
        ws[f"F{r}"].font = font_regular
        ws.row_dimensions[r].height = 20
        r += 1
        
    # 3. Günlük Yem Reçetesi ve Sürü Tüketim Tablosu
    r += 1
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"] = "  📋 GÜNLÜK RASYON REÇETESİ VE SÜRÜ İHTİYAÇ TABLOSU"
    ws[f"A{r}"].font = font_section
    ws[f"A{r}"].fill = fill_section
    ws.row_dimensions[r].height = 24
    
    r += 1
    headers = [
        ("A", "YEM ADI"),
        ("B", "KATEGORİ"),
        ("C", "BİRİM FİYAT (₺/kg)"),
        ("D", "HAYVAN BAŞI (kg/gün)"),
        ("E", "GÜNLÜK MALİYET (₺/baş)"),
        ("F", f"SÜRÜ GÜNLÜK ({head_count} Baş / kg)"),
        ("G", f"30 GÜNLÜK SÜRÜ (kg / Ton)")
    ]
    
    for col_letter, title in headers:
        cell = ws[f"{col_letter}{r}"]
        cell.value = title
        cell.font = font_tbl_header
        cell.fill = fill_tbl_header
        cell.alignment = align_center
        cell.border = border_cell
    ws.row_dimensions[r].height = 26
    
    res = farm_data.get("result", {})
    items = res.get("items", [])
    total_cost_head = res.get("daily_cost_tl", 0.0)
    total_fresh_head = res.get("total_fresh_weight_kg", 0.0)
    
    start_item_row = r + 1
    r += 1
    for idx, it in enumerate(items):
        is_even = (idx % 2 == 0)
        curr_fill = fill_zebra if is_even else None
        
        amount_head = it["amount_kg"]
        cost_head = it["cost_tl"]
        price_unit = it["price_tl"]
        herd_daily = amount_head * head_count
        herd_monthly = herd_daily * 30
        monthly_display = f"{herd_monthly/1000.0:.2f} Ton" if herd_monthly >= 1000 else f"{herd_monthly:.0f} kg"
        
        row_vals = [
            ("A", it["name"], align_left),
            ("B", it["category"], align_center),
            ("C", f"{price_unit:.2f} ₺", align_right),
            ("D", f"{amount_head:.2f} kg", align_right),
            ("E", f"{cost_head:.2f} ₺", align_right),
            ("F", f"{herd_daily:.1f} kg", align_right),
            ("G", monthly_display, align_right)
        ]
        for col_letter, val, al in row_vals:
            c = ws[f"{col_letter}{r}"]
            c.value = val
            c.font = font_regular
            c.alignment = al
            c.border = border_cell
            if curr_fill:
                c.fill = curr_fill
        ws.row_dimensions[r].height = 21
        r += 1
        
    # Toplam Satırı
    ws[f"A{r}"] = "TOPLAM"
    ws[f"A{r}"].font = font_bold
    ws[f"A{r}"].fill = fill_total
    ws[f"A{r}"].border = border_total
    
    ws[f"B{r}"] = "-"
    ws[f"B{r}"].alignment = align_center
    ws[f"B{r}"].fill = fill_total
    ws[f"B{r}"].border = border_total
    
    ws[f"C{r}"] = "-"
    ws[f"C{r}"].alignment = align_center
    ws[f"C{r}"].fill = fill_total
    ws[f"C{r}"].border = border_total
    
    ws[f"D{r}"] = f"{total_fresh_head:.2f} kg"
    ws[f"D{r}"].font = font_bold
    ws[f"D{r}"].alignment = align_right
    ws[f"D{r}"].fill = fill_total
    ws[f"D{r}"].border = border_total
    
    ws[f"E{r}"] = f"{total_cost_head:.2f} ₺"
    ws[f"E{r}"].font = font_bold
    ws[f"E{r}"].alignment = align_right
    ws[f"E{r}"].fill = fill_total
    ws[f"E{r}"].border = border_total
    
    total_herd_daily = total_fresh_head * head_count
    total_herd_monthly = total_herd_daily * 30
    ws[f"F{r}"] = f"{total_herd_daily:.1f} kg"
    ws[f"F{r}"].font = font_bold
    ws[f"F{r}"].alignment = align_right
    ws[f"F{r}"].fill = fill_total
    ws[f"F{r}"].border = border_total
    
    ws[f"G{r}"] = f"{total_herd_monthly/1000.0:.2f} Ton"
    ws[f"G{r}"].font = font_bold
    ws[f"G{r}"].alignment = align_right
    ws[f"G{r}"].fill = fill_total
    ws[f"G{r}"].border = border_total
    ws.row_dimensions[r].height = 24
    
    # 4. Sürü Maliyet Projeksiyonu Kutusu
    r += 2
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"] = "  💰 SÜRÜ MALİYET VE EKONOMİK PROJEKSİYON"
    ws[f"A{r}"].font = font_section
    ws[f"A{r}"].fill = fill_section
    ws.row_dimensions[r].height = 24
    
    r += 1
    herd_daily_cost = total_cost_head * head_count
    herd_monthly_cost = herd_daily_cost * 30
    
    econ_rows = [
        ("Hayvan Başı Günlük Yem Maliyeti:", f"{total_cost_head:.2f} ₺ / baş / gün"),
        (f"Tüm Sürü Günlük Yem Maliyeti ({head_count} Baş):", f"{herd_daily_cost:,.2f} ₺ / gün".replace(",", "X").replace(".", ",").replace("X", ".")),
        (f"Tüm Sürü Aylık (30 Günlük) Yem Bütçesi:", f"{herd_monthly_cost:,.2f} ₺ / ay".replace(",", "X").replace(".", ",").replace("X", "."))
    ]
    if group_name == "Besi Sığırı" and "daily_gain_grams" in farm_data:
        adg_kg = float(farm_data["daily_gain_grams"]) / 1000.0
        cost_per_kg_gain = total_cost_head / adg_kg if adg_kg > 0 else 0.0
        econ_rows.append(("1 kg Canlı Ağırlık Artışı Yem Maliyeti:", f"{cost_per_kg_gain:.2f} ₺ / kg et"))
    elif group_name == "Sütçü İnek" and "milk_yield_kg" in farm_data:
        milk_lt = float(farm_data["milk_yield_kg"])
        cost_per_lt = total_cost_head / milk_lt if milk_lt > 0 else 0.0
        econ_rows.append(("1 Litre Süt Yem Maliyeti:", f"{cost_per_lt:.2f} ₺ / Litre süt"))
        
    for item in econ_rows:
        ws.merge_cells(f"A{r}:C{r}")
        ws[f"A{r}"] = item[0]
        ws[f"A{r}"].font = font_bold
        ws.merge_cells(f"D{r}:G{r}")
        ws[f"D{r}"] = item[1]
        ws[f"D{r}"].font = font_bold
        ws[f"D{r}"].alignment = align_left
        ws.row_dimensions[r].height = 20
        r += 1
        
    # 5. Besin Maddesi Dengesi Tablosu
    r += 1
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"] = "  🔬 BESİN MADDESİ ANALİZİ VE SAĞLANMA ORANLARI"
    ws[f"A{r}"].font = font_section
    ws[f"A{r}"].fill = fill_section
    ws.row_dimensions[r].height = 24
    
    r += 1
    reqs = res.get("requirements", {})
    nutrients = [
        ("Kuru Madde (KM)", f"{res.get('total_km_kg', 0):.2f} kg", f"{reqs.get('dmi_target', 0):.2f} kg", "Normal"),
        ("Ham Protein (HP)", f"{res.get('total_hp_g', 0):.0f} g (KM'de %{res.get('hp_percent_km', 0):.1f})", f"{reqs.get('hp_req', 0):.0f} g", "Dengeli"),
        ("Metabolik Enerji (ME)", f"{res.get('total_me_mcal', 0):.2f} Mcal", f"{reqs.get('me_req', 0):.2f} Mcal", "Karşılandı"),
        ("Kalsiyum (Ca)", f"{res.get('total_ca_g', 0):.1f} g", f"{reqs.get('ca_req', 0):.1f} g", "Tamam"),
        ("Fosfor (P)", f"{res.get('total_p_g', 0):.1f} g", f"{reqs.get('p_req', 0):.1f} g", "Tamam"),
        ("Ca / P Oranı", f"{res.get('ca_p_ratio', 0):.2f}", "1.50 - 2.00", "İdeal"),
        ("Kaba Yem Oranı", f"%{res.get('forage_percent', 0):.1f}", f"En az %{int(reqs.get('min_forage_ratio', 0.3)*100)}", "Rumen Güvenli")
    ]
    
    nut_headers = [("A", "PARAMETRE"), ("C", "RASYONDAN GELEN"), ("E", "İHTİYAÇ / HEDEF"), ("G", "DURUM")]
    ws.merge_cells(f"A{r}:B{r}")
    ws[f"A{r}"] = "PARAMETRE"
    ws.merge_cells(f"C{r}:D{r}")
    ws[f"C{r}"] = "RASYONDAN GELEN"
    ws.merge_cells(f"E{r}:F{r}")
    ws[f"E{r}"] = "İHTİYAÇ / REFERANS"
    ws[f"G{r}"] = "DURUM"
    for col_l in ["A", "B", "C", "D", "E", "F", "G"]:
        ws[f"{col_l}{r}"].font = font_tbl_header
        ws[f"{col_l}{r}"].fill = fill_tbl_header
        ws[f"{col_l}{r}"].alignment = align_center
        ws[f"{col_l}{r}"].border = border_cell
    ws.row_dimensions[r].height = 24
    
    r += 1
    for n_item in nutrients:
        ws.merge_cells(f"A{r}:B{r}")
        ws[f"A{r}"] = n_item[0]
        ws[f"A{r}"].font = font_bold
        
        ws.merge_cells(f"C{r}:D{r}")
        ws[f"C{r}"] = n_item[1]
        ws[f"C{r}"].alignment = align_center
        
        ws.merge_cells(f"E{r}:F{r}")
        ws[f"E{r}"] = n_item[2]
        ws[f"E{r}"].alignment = align_center
        
        ws[f"G{r}"] = n_item[3]
        ws[f"G{r}"].alignment = align_center
        
        for col_l in ["A", "B", "C", "D", "E", "F", "G"]:
            ws[f"{col_l}{r}"].border = border_cell
            ws[f"{col_l}{r}"].font = font_regular
        ws[f"A{r}"].font = font_bold
        ws.row_dimensions[r].height = 20
        r += 1
        
    # 6. Yüksek Mühendis M. Fatih CEYHAN Uzman Yorumu ve Çiftlik Notları
    r += 1
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"] = "  🧠 YÜKSEK MÜHENDİS M. FATİH CEYHAN UZMAN YORUMU VE TAVSİYELERİ"
    ws[f"A{r}"].font = font_section
    ws[f"A{r}"].fill = fill_section
    ws.row_dimensions[r].height = 24
    
    r += 1
    notes = [
        "1. Rasyon Değişikliği: Yeni rasyona geçişte en az 7-10 günlük kademeli alıştırma periyodu uygulanmalıdır.",
        "2. TMR Karıştırma: Kaba ve kesif yemlerin homojen karışması sağlanmalı, hayvanların yem seçmesine engel olunmalıdır.",
        "3. Su İhtiyacı: Hayvanların önünde her zaman temiz, taze ve ılık su kesintisiz (ad-libitum) bulundurulmalıdır.",
        "4. Rumen Sağlığı: Kaba yem partikül boyutu geviş getirmeyi teşvik edecek uzunlukta (en az 3-5 cm) tutulmalıdır.",
        "5. İşletme Takibi: Hayvanların gübre kıvamı, geviş getirme sıklığı ve kondisyon skorları haftalık izlenmelidir."
    ]
    for note in notes:
        ws.merge_cells(f"A{r}:G{r}")
        ws[f"A{r}"] = note
        ws[f"A{r}"].font = font_regular
        ws[f"A{r}"].alignment = align_wrap
        ws.row_dimensions[r].height = 20
        r += 1
        
    # 7. İmza ve Onay Alanı
    r += 2
    ws.merge_cells(f"E{r}:G{r}")
    ws[f"E{r}"] = "Raporu Onaylayan:"
    ws[f"E{r}"].font = font_bold
    ws[f"E{r}"].alignment = align_center
    r += 1
    ws.merge_cells(f"E{r}:G{r}")
    ws[f"E{r}"] = "Yüksek Mühendis M. Fatih CEYHAN"
    ws[f"E{r}"].font = Font(name="Calibri", size=11, bold=True, color="1E4D2B")
    ws[f"E{r}"].alignment = align_center
    r += 1
    ws.merge_cells(f"E{r}:G{r}")
    ws[f"E{r}"] = "Hayvan Besleme & Sürü Yönetim Uzmanı"
    ws[f"E{r}"].font = font_note
    ws[f"E{r}"].alignment = align_center
    
    # Sütun genişliklerini otomatik ayarla
    col_widths = {
        "A": 28,
        "B": 22,
        "C": 18,
        "D": 20,
        "E": 22,
        "F": 22,
        "G": 22
    }
    for col_l, width in col_widths.items():
        ws.column_dimensions[col_l].width = width
        
    # Dosyayı kaydet
    clean_farm_name = "".join(c for c in farm_name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    if not clean_farm_name:
        clean_farm_name = "Ciftlik"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Rasyon_Raporu_{clean_farm_name}_{timestamp}.xlsx"
    export_dir = r"C:\Users\savas\.gemini\antigravity\scratch\rasyon_bot\exports"
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, filename)
    
    wb.save(filepath)
    return filepath
