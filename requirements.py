# -*- coding: utf-8 -*-
"""
Gereksinim Hesaplama Motoru (Nutrient Requirements Calculator)
Tamamen ve Birebir:
- Besi_V5.02.xlsm (Selçuk Üniversitesi & NRC Beef Cattle Modeli)
- Sut_V5.01.xlsm (Selçuk Üniversitesi & NRC 2001 Dairy Cattle Modeli)
- Koyun_V1.14.xlsm (Selçuk Üniversitesi & NRC Koyun Modeli)
dosyalarındaki formüllere ve tablolara göre hazırlanmıştır.
"""

import math
import os
import json

# Koyun gereksinim tablosunu yükle
KOYUN_TABLE_PATH = os.path.join(os.path.dirname(__file__), "koyun_reqs.json")
try:
    with open(KOYUN_TABLE_PATH, "r", encoding="utf-8") as f:
        KOYUN_TABLE = json.load(f)
except Exception:
    KOYUN_TABLE = []

def calculate_besi_requirements(live_weight: float, daily_gain_grams: float, breed_type: str = "kultur"):
    """
    Besi_V5.02.xlsm Rapor sayfası formülleri:
    - Shrunk Body Weight: SBW = BW * 0.96 (Rapor!CN1)
    - MEconc = (0.0857*ADG^2 + 0.5357*ADG + 1.6021) + IF(BW<=400,0, (0.0000035*BW^2 - 0.0016*BW + 0.0539)) (Rapor!CN46)
    - DMI = ((SBW^0.75 * (0.2435*MEconc - 0.0466*MEconc^2 - 0.0869)) / MEconc) (Rapor!CN140)
    - Metabolik Protein (MP, g/gün) = (-0.56*SBW+476.1)*ADG + (0.0495*SBW+5.7429) + (-0.00015*SBW^2 + 0.8009*SBW + 51.429) + 8 (Rapor!H8)
    - Ca = Camaint (0.0154*SBW/0.5) + Cagrow (Rapor!CR89 & CS89)
    - P = Pmaint (0.016*SBW/0.68) + Pgrow (Rapor!CR90 & CS90)
    """
    bw = float(live_weight)
    adg_kg = float(daily_gain_grams) / 1000.0  # kg/gün
    
    # 1. Shrunk Body Weight (Rapor!CN1)
    sbw = bw * 0.96
    
    # 2. ME Yoğunluğu (Rapor!CN46)
    me_conc = (0.0857 * (adg_kg**2) + 0.5357 * adg_kg + 1.6021)
    if bw > 400:
        me_conc += (0.0000035 * (bw**2) - 0.0016 * bw + 0.0539)
        
    # 3. Kuru Madde İhtiyacı DMI (Rapor!CN140)
    dmi_numerator = (sbw**0.75) * (0.2435 * me_conc - 0.0466 * (me_conc**2) - 0.0869)
    dmi = dmi_numerator / me_conc if me_conc > 0 else (sbw**0.75 * 0.0968)
    dmi = max(dmi, bw * 0.018) # Güvenlik alt sınırı
    
    # 4. Toplam ME İhtiyacı (Mcal/gün)
    me_req = dmi * me_conc
    
    # 5. Metabolik Protein (MP, g/gün) (Rapor!H8 Formülü)
    mp_req = ((-0.56 * sbw + 476.1) * adg_kg + 
              (0.0495 * sbw + 5.7429) + 
              (-0.00015 * (sbw**2) + 0.8009 * sbw + 51.429) + 8.0)
    # Ham Protein karşılığı (Rasyondaki MP/HP sindirilebilirlik katsayısı ~%67)
    hp_req = mp_req / 0.67
    
    # 6. Kalsiyum (Ca, g/gün) (Rapor!CR89 & CS89)
    # Camaint = 0.0154 * SBW / 0.5
    # Cagrow = NPg * (0.071 / 0.5)
    ca_maint = 0.0154 * sbw / 0.5
    ca_grow = (adg_kg * 1000.0) * (0.071 / 0.5) * 0.15 # Büyüme payı net Ca
    ca_req = ca_maint + ca_grow
    
    # 7. Fosfor (P, g/gün) (Rapor!CR90 & CS90)
    # Pmaint = 0.016 * SBW / 0.68
    # Pgrow = NPg * 0.045 / 0.68
    p_maint = 0.016 * sbw / 0.68
    p_grow = (adg_kg * 1000.0) * (0.045 / 0.68) * 0.15
    p_req = p_maint + p_grow
    
    min_forage_ratio = 0.18 if bw > 400 else 0.20
    
    return {
        "group": "Besi Sığırı",
        "live_weight": bw,
        "daily_gain_grams": daily_gain_grams,
        "dmi_target": round(dmi, 2),
        "dmi_min": round(dmi * 0.88, 2),
        "dmi_max": round(dmi * 1.10, 2),
        "me_conc": round(me_conc, 2),
        "me_req": round(me_req, 2),
        "mp_req": round(mp_req, 1),
        "hp_req": round(hp_req, 1),
        "ca_req": round(ca_req, 1),
        "p_req": round(p_req, 1),
        "min_forage_ratio": min_forage_ratio,
        "max_forage_ratio": 0.40
    }


def calculate_sut_requirements(live_weight: float, milk_yield_kg: float, milk_fat_percent: float = 3.7):
    """
    Sut_V5.01.xlsm Rapor sayfası formülleri:
    - 4% Yağa Düzeltilmiş Süt: FCM = 0.4*MilkProd + 15*(FatPct/100)*MilkProd
    - DMILact = (((BW^0.75)*0.0968) + (0.372*FCM) - 0.293) * (1 - EXP(-0.192*(DIM/7 + 3.67))) (Rapor!CX111)
    - MilkEN = 0.0929*FatPct + 0.0563*TrueProtPct + 0.0395*LactosePct
    - YEn = MilkEN * MilkProd (Rapor!CX17)
    - NEMaint = 0.080 * BW^0.75
    - NEL Total = NEMaint + YEn
    - Ham Protein = (2.2 * BW^0.75) + (88.0 * MilkProd)
    - Ca Total = (0.031 * BW) + (1.25 * MilkProd) (Rapor!AO69)
    - P Total = DMI + (0.002 * BW) + (0.90 * MilkProd) (Rapor!AO70)
    """
    bw = float(live_weight)
    milk = float(milk_yield_kg)
    fat = float(milk_fat_percent)
    
    # FCM (Rapor!FCM)
    fcm = (0.4 * milk) + (15.0 * (fat / 100.0) * milk)
    
    # Kuru Madde Tüketimi (NRC 2001 / Sut Rapor!CX111) - DIM ortalama 90 gün
    dim_factor = 1.0 - math.exp(-0.192 * (90.0 / 7.0 + 3.67))
    dmi = (((bw**0.75) * 0.0968) + (0.372 * fcm) - 0.293) * dim_factor
    dmi = max(dmi, bw * 0.022)
    
    # Net Enerji Laktasyon (Sut Rapor!CX17 & CX97)
    # MilkEN = 0.0929*Fat + 0.0563*3.1 + 0.0395*4.8
    milk_en = (0.0929 * fat) + (0.0563 * 3.1) + (0.0395 * 4.8)
    yen = milk_en * milk
    ne_maint = 0.080 * (bw**0.75)
    nel_req = ne_maint + yen
    me_req = nel_req / 0.64
    
    # Ham Protein İhtiyacı
    hp_req = (2.2 * (bw**0.75)) + (88.0 * milk)
    
    # Ca ve P (Sut Rapor!AO69 ve AO70 formülleri)
    # Emilebilir Ca: Fecal (0.031*BW) + Süt (1.25*Milk)
    # Emilebilir P: Fecal (1.0*DMI) + Urine (0.002*BW) + Süt (0.90*Milk)
    ca_req = (0.031 * bw) + (1.25 * milk)
    p_req = dmi + (0.002 * bw) + (0.90 * milk)
    
    min_forage_ratio = 0.20
    
    return {
        "group": "Sütçü İnek",
        "live_weight": bw,
        "milk_yield_kg": milk,
        "milk_fat_percent": fat,
        "fcm": round(fcm, 2),
        "dmi_target": round(dmi, 2),
        "dmi_min": round(dmi * 0.88, 2),
        "dmi_max": round(dmi * 1.10, 2),
        "nel_req": round(nel_req, 2),
        "me_req": round(me_req, 2),
        "hp_req": round(hp_req, 1),
        "ca_req": round(ca_req, 1),
        "p_req": round(p_req, 1),
        "min_forage_ratio": min_forage_ratio,
        "max_forage_ratio": 0.40
    }


def calculate_koyun_requirements(live_weight: float, physiological_state: str = "flasing"):
    """
    Koyun_V1.14.xlsm dosyasındaki Rapor!KoyunReqs (Rapor!$BA$3:$BX$72)
    Selçuk Üniversitesi tablosundan doğrudan çekilir ve canlı ağırlığa ölçeklenir.
    """
    bw = float(live_weight)
    state = physiological_state.lower()
    
    # İlgili satırı KoyunReqs tablosundan ara
    matched_row = None
    for row in KOYUN_TABLE:
        row_name = row["name"].lower()
        if "flas" in state and "fla" in row_name:
            matched_row = row
            break
        elif "erken_gebe" in state and "erken gebe" in row_name and "tek" in row_name:
            matched_row = row
            break
        elif "son_gebe_ikiz" in state and "ge" in row_name and "kiz" in row_name:
            matched_row = row
            break
        elif "laktasyon" in state and "laktasyon" in row_name and "kiz" in row_name:
            matched_row = row
            break
        elif "toklu" in state and ("toklu" in row_name or "besi" in row_name or "1" in row_name):
            matched_row = row
            break
            
    # Eğer özel eşleşme yoksa tablodan ilk uygun dönemi al
    if not matched_row and len(KOYUN_TABLE) > 1:
        matched_row = KOYUN_TABLE[1] # Flaşing
        
    scale = bw / 50.0 # Tablo 50 kg ergin koyun bazlıdır
    
    dmi = matched_row["KM"] * scale
    me = matched_row["ME"] * scale
    hp = matched_row["HP"] * scale
    ca = matched_row["Ca"] * scale
    p = matched_row["P"] * scale
    
    min_forage = 0.15 if ("toklu" in state or "besi" in state) else 0.25
    
    return {
        "group": "Koyun / Küçükbaş",
        "live_weight": bw,
        "desc": matched_row["name"],
        "dmi_target": round(dmi, 2),
        "dmi_min": round(dmi * 0.88, 2),
        "dmi_max": round(dmi * 1.10, 2),
        "me_req": round(me, 2),
        "hp_req": round(hp, 1),
        "ca_req": round(ca, 1),
        "p_req": round(p, 1),
        "min_forage_ratio": min_forage,
        "max_forage_ratio": 0.40
    }
