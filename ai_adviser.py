# -*- coding: utf-8 -*-
"""
Yapay Zekâ Zooteknist ve Veteriner Hekim Danışmanı (AI Rasyon Danışmanı)
Rasyon sonuçlarını değerlendirir, rumen sağlığı, asidoz riski ve maliyet projeksiyonu sunar.
"""

from typing import Dict, Any

def generate_expert_report(result: Dict[str, Any]) -> str:
    """
    Rasyon optimizasyon sonucundan Telegram için profesyonel Markdown raporu üretir.
    """
    if not result.get("success"):
        return f"❌ **Rasyon Hesaplanamadı:**\n{result.get('message', 'Bilinmeyen hata')}"
        
    reqs = result["requirements"]
    group = reqs.get("group", "Bilinmeyen")
    cost = result["daily_cost_tl"]
    total_km = result["total_km_kg"]
    forage_pct = result["forage_percent"]
    ca_p = result["ca_p_ratio"]
    hp_pct = result["hp_percent_km"]
    items = result["items"]
    
    # Başlık ve Hayvan Tanımı
    report = []
    if group == "Besi Sığırı":
        report.append("🐂 **PROFESYONEL BESİ RASYONU RAPORU**")
        report.append(f"• **Canlı Ağırlık:** {reqs['live_weight']} kg")
        report.append(f"• **Hedef Günlük Artış:** {reqs['daily_gain_grams']} g/gün")
        
        # 1 kg et maliyeti (GCAA üzerinden)
        kg_et_cost = cost / (reqs['daily_gain_grams'] / 1000.0)
        fcr = total_km / (reqs['daily_gain_grams'] / 1000.0) # FCR (KM bazında)
        report.append(f"• **1 kg Canlı Ağırlık Yem Maliyeti:** `{kg_et_cost:.2f} ₺`")
        report.append(f"• **Yemden Yararlanma (FCR):** `{fcr:.2f}` kg KM/kg kazanç")
        
    elif group == "Sütçü İnek":
        report.append("🥛 **PROFESYONEL SÜT RASYONU RAPORU**")
        report.append(f"• **Canlı Ağırlık:** {reqs['live_weight']} kg")
        report.append(f"• **Günlük Süt:** {reqs['milk_yield_kg']} kg (Yağ: %{reqs['milk_fat_percent']})")
        
        # 1 Litre süt yem maliyeti
        lt_sut_cost = cost / reqs['milk_yield_kg']
        report.append(f"• **1 Litre Süt Yem Maliyeti:** `{lt_sut_cost:.2f} ₺`")
        report.append(f"• **Süt/Yem Oranı:** `{reqs['milk_yield_kg'] / total_km:.2f}` kg süt / kg KM")
        
    elif group == "Koyun / Küçükbaş":
        report.append("🐑 **PROFESYONEL KOYUN / KUZU RASYONU**")
        report.append(f"• **Fizyolojik Durum:** {reqs.get('desc', 'Koyun')}")
        report.append(f"• **Canlı Ağırlık:** {reqs['live_weight']} kg")
        
    report.append("")
    report.append("📋 **GÜNLÜK YEM REÇETESİ (BAŞ BAŞINA)**")
    report.append("`────────────────────────────────────────`")
    
    for it in items:
        icon = "🌾" if it["is_forage"] else ("⚡" if "Enerji" in it["category"] else ("🥩" if "Protein" in it["category"] else "⚪"))
        report.append(f"{icon} **{it['name']}:** `{it['amount_kg']:.2f} kg`  *(%{it['km_kg']/total_km*100:.1f} KM | {it['cost_tl']:.2f} ₺)*")
        
    report.append("`────────────────────────────────────────`")
    report.append(f"💰 **Toplam Günlük Maliyet:** `{cost:.2f} ₺ / baş / gün`")
    report.append(f"⚖️ **Toplam Tüketim (Doğal Halde):** `{result['total_fresh_weight_kg']:.2f} kg/gün`")
    report.append(f"🌾 **Toplam Kuru Madde (KM):** `{total_km:.2f} kg` (Hedef: {reqs['dmi_target']} kg)")
    report.append("")
    
    # Besin Maddesi Dengesi
    report.append("🔬 **BESİN MADDESİ DENGESİ**")
    report.append(f"• **Ham Protein (HP):** `{result['total_hp_g']:.0f} g` *(KM'de %{hp_pct:.1f})* | İhtiyaç: {reqs['hp_req']:.0f} g")
    if "total_nel_mcal" in result and result.get("total_nel_mcal", 0) > 0 and group == "Sütçü İnek":
        report.append(f"• **Net Enerji Laktasyon (NEL):** `{result['total_nel_mcal']:.2f} Mcal` | İhtiyaç: {reqs['nel_req']:.2f} Mcal")
    else:
        report.append(f"• **Metabolik Enerji (ME):** `{result['total_me_mcal']:.2f} Mcal` | İhtiyaç: {reqs['me_req']:.2f} Mcal")
    report.append(f"• **Kalsiyum (Ca):** `{result['total_ca_g']:.1f} g` | İhtiyaç: {reqs['ca_req']:.1f} g")
    report.append(f"• **Fosfor (P):** `{result['total_p_g']:.1f} g` | İhtiyaç: {reqs['p_req']:.1f} g")
    report.append(f"• **Ca / P Oranı:** `{ca_p:.2f}` (İdeal: 1.5 - 2.0)")
    report.append(f"• **Kaba Yem Oranı:** `%{forage_pct:.1f}`")
    report.append("")
    
    # Yüksek Mühendis M. Fatih Ceyhan Uzman Yorumu
    report.append("🧠 **YÜKSEK MÜHENDİS M. FATİH CEYHAN UZMAN YORUMU**")
    
    # Asidoz ve Kaba Yem Değerlendirmesi
    if forage_pct < 25.0:
        report.append("⚠️ **Asidoz Riski Yüksek:** Kaba yem oranı %25'in altında. Yemliğe geviş getirmeyi teşvik edecek uzun lifli kaba yem (yonca/saman) veya sodyum bikarbonat (soda) takviyesi önerilir.")
    elif forage_pct < 35.0:
        report.append("✅ **Yoğun Besi Düzeyi:** Kaba yem oranı %25-%35 aralığında. Yüksek enerji alımı sağlar; öğünleri gün içine yayarak (en az 2-3 öğün) asidoz kontrol altında tutulmalıdır.")
    else:
        report.append("✅ **Rumen Sağlığı İdeal:** Kaba yem oranı %35 üzerinde. Rumen hareketleri, geviş getirme ve sindirim güvenliği mükemmel.")
        
    # Ca / P Oranı Değerlendirmesi
    if ca_p < 1.2:
        report.append("⚠️ **Mineral Uyarısı:** Ca/P oranı 1.2'nin altında (idrar yolu taşı riski artar). Mermer tozu miktarı bir miktar artırılmalıdır.")
    elif ca_p > 2.5:
        report.append("ℹ️ **Kalsiyum Yüksek:** Kalsiyum oranı yüksek ancak toksik değildir.")
    else:
        report.append("✅ **Mineral Dengesi Mükemmel:** Ca/P oranı ideal fizyolojik aralıkta (1.4 - 2.0).")
        
    # Pratik Saha Tavsiyeleri
    report.append("")
    report.append("📌 **ÇİFTLİK VE YEMLEME TAVSİYELERİ:**")
    report.append("1. Rasyon değişikliklerine geçerken en az **7-10 günlük alıştırma süresi** uygulayın.")
    report.append("2. Temiz ve ılık suyun **serbest (ad-libitum)** olarak hayvanın önünde bulunmasını sağlayın.")
    report.append("3. Karma yemi (TMR) homojen karıştırın; hayvanların dane yemleri seçmesine izin vermeyin.")
    
    return "\n".join(report)
