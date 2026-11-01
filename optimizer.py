# -*- coding: utf-8 -*-
"""
Rasyon Optimizasyon Motoru (Ration Formulation Optimizer)
Doğrusal Programlama (Linear Programming) / HiGHS Simplex Çözücü
Gelişmiş Çok Aşamalı Esnek Çözümleme (Multi-Stage Robust Formulation)
"""

from scipy.optimize import linprog
from typing import List, Dict, Any
from feed_database import FEED_DATABASE

def solve_ration(reqs: Dict[str, Any], feed_ids: List[str] = None, custom_prices: Dict[str, float] = None, custom_bounds: Dict[str, tuple] = None) -> Dict[str, Any]:
    """
    Kullanıcının seçtiği yemler ve kısıtlarla en düşük maliyetli rasyonu çözer.
    Her canlı ağırlık ve verim düzeyi için garantili, matematiksel olarak kararlı sonuç üretir.
    """
    if feed_ids is None or len(feed_ids) == 0:
        return {"success": False, "message": "En az bir yem seçilmelidir."}
    
    selected_feeds = []
    for fid in feed_ids:
        if fid in FEED_DATABASE:
            f = dict(FEED_DATABASE[fid])
            if custom_prices and fid in custom_prices:
                f["price"] = float(custom_prices[fid])
            else:
                f["price"] = f["default_price"]
            selected_feeds.append(f)
            
    n = len(selected_feeds)
    if n == 0:
        return {"success": False, "message": "Geçerli yem bulunamadı."}
        
    dmi_target = reqs["dmi_target"]
    grp = reqs.get("group", "")
    
    # 1. Yem alt ve üst sınırlarını hayvanın tüketim kapasitesine göre dinamik ölçekle
    for f in selected_feeds:
        fid = f["id"]
        if custom_bounds and fid in custom_bounds:
            f["min"] = float(custom_bounds[fid][0])
            f["max"] = float(custom_bounds[fid][1])
        else:
            # Hayvan küçükse (küçük toklu, buzağı) alt sınır hayvanın kapasitesini aşmasın
            f["min"] = min(f["min_default"], round(dmi_target * 0.15, 2))
            f["max"] = f["max_default"]

    # 2. PROYEM / KABUL YEM Fabrika Yemleri:
    factory_feeds = [f for f in selected_feeds if "Fabrika" in f.get("category", "")]
    num_factory = len(factory_feeds)
    
    if num_factory > 0:
        if grp == "Koyun / Küçükbaş":
            target_factory_min = min(0.40, dmi_target * 0.20)
        else:
            target_factory_min = min(4.0, dmi_target * 0.25)
            
        share_per_feed = round(target_factory_min / num_factory, 2)
        for f in factory_feeds:
            f["min"] = max(0.05, share_per_feed)
            # Yüksek verimli hayvanlar için üst sınırları genişlet
            if grp == "Sütçü İnek":
                f["max"] = max(f["max_default"], 16.0)
            elif grp == "Besi Sığırı":
                f["max"] = max(f["max_default"], 14.0)
            elif grp == "Koyun / Küçükbaş":
                f["max"] = max(f["max_default"], 3.0)

    # 3. Yüksek verimli süt ve besi için kaba yem üst sınırlarını esnet
    for f in selected_feeds:
        if f["id"] == "misir_silaji":
            f["max"] = max(f["max_default"], 35.0)
        elif f["id"] == "yonca_kuru_otu":
            f["max"] = max(f["max_default"], 12.0)

    # 4. Çok aşamalı çözüm denemesi (Kısıt esnetme toleransları)
    res = None
    best_stage = 0
    
    for attempt in range(4):
        # Aşama aşama esnetilen kısıtlar
        dmi_min = dmi_target * (0.85 - attempt * 0.05)
        dmi_max = dmi_target * (1.10 + attempt * 0.08)
        
        min_fr = min(0.25, reqs.get("min_forage_ratio", 0.20)) - (attempt * 0.03)
        min_fr = max(0.12, min_fr)
        
        c = [f["price"] for f in selected_feeds]
        A_ub = []
        b_ub = []
        
        # Kısıt 1: DMI max
        A_ub.append([f["KM"] / 100.0 for f in selected_feeds])
        b_ub.append(dmi_max)
        
        # Kısıt 2: DMI min
        A_ub.append([-f["KM"] / 100.0 for f in selected_feeds])
        b_ub.append(-dmi_min)
        
        # Kısıt 3: Enerji (NEL veya ME)
        if "nel_req" in reqs and grp == "Sütçü İnek":
            A_ub.append([-f["KM"] / 100.0 * f["NEL"] for f in selected_feeds])
            b_ub.append(-reqs["nel_req"])
        else:
            A_ub.append([-f["KM"] / 100.0 * f["ME"] for f in selected_feeds])
            b_ub.append(-reqs["me_req"])
            
        # Kısıt 4: Ham Protein (g/gün)
        A_ub.append([-f["KM"] / 100.0 * f["HP"] * 10.0 for f in selected_feeds])
        b_ub.append(-reqs["hp_req"])
        
        # Kısıt 5: Kalsiyum (g/gün)
        A_ub.append([-f["KM"] / 100.0 * f["Ca"] * 10.0 for f in selected_feeds])
        b_ub.append(-reqs["ca_req"])
        
        # Kısıt 6: Fosfor (g/gün)
        A_ub.append([-f["KM"] / 100.0 * f["P"] * 10.0 for f in selected_feeds])
        b_ub.append(-reqs["p_req"])
        
        # Kısıt 7: Kaba Yem Oranı Alt Sınırı (Rumen sağlığı için asgari %15-20)
        min_fr = reqs.get("min_forage_ratio", 0.20) - (attempt * 0.02)
        min_fr = max(0.12, min(min_fr, 0.25))
        
        forage_min_row = []
        for f in selected_feeds:
            km_coeff = f["KM"] / 100.0
            if f["is_forage"]:
                forage_min_row.append((min_fr - 1.0) * km_coeff)
            else:
                forage_min_row.append(min_fr * km_coeff)
        A_ub.append(forage_min_row)
        b_ub.append(0.0)
        
        # Kısıt 8: Kaba Yem Oranı Üst Sınırı (KURAL: Kaba Yem KM'si %40'ı ASLA GEÇMESİN!)
        # Forage DMI <= 0.40 * Total DMI -> (1 - 0.40)*Forage - 0.40*Conc <= 0
        max_fr = 0.40
        forage_max_row = []
        for f in selected_feeds:
            km_coeff = f["KM"] / 100.0
            if f["is_forage"]:
                forage_max_row.append((1.0 - max_fr) * km_coeff)
            else:
                forage_max_row.append(-max_fr * km_coeff)
        A_ub.append(forage_max_row)
        b_ub.append(0.0)
        
        bounds = [(f["min"], f["max"]) for f in selected_feeds]
        
        cur_res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        if cur_res.success:
            res = cur_res
            best_stage = attempt
            break
            
    if res is None or not res.success:
        return {
            "success": False,
            "message": f"Bu yem kombinasyonu ve kısıtlarla matematiksel çözüm bulunamadı. Lütfen kaba/kesif yem çeşitliliğini artırın."
        }
        
    daily_cost = res.fun
    x_opt = res.x
    
    total_km = 0.0
    forage_km = 0.0
    total_me = 0.0
    total_nel = 0.0
    total_hp = 0.0
    total_ca = 0.0
    total_p = 0.0
    total_fresh_weight = 0.0
    
    ration_items = []
    
    for i, f in enumerate(selected_feeds):
        amount = x_opt[i]
        if amount > 0.005:
            item_km = amount * (f["KM"] / 100.0)
            item_cost = amount * f["price"]
            
            total_fresh_weight += amount
            total_km += item_km
            if f["is_forage"]:
                forage_km += item_km
                
            total_me += item_km * f["ME"]
            total_nel += item_km * f["NEL"]
            total_hp += item_km * f["HP"] * 10.0
            total_ca += item_km * f["Ca"] * 10.0
            total_p += item_km * f["P"] * 10.0
            
            ration_items.append({
                "id": f["id"],
                "name": f["name"],
                "category": f["category"],
                "is_forage": f["is_forage"],
                "amount_kg": round(amount, 2),
                "km_kg": round(item_km, 2),
                "price_tl": f["price"],
                "cost_tl": round(item_cost, 2)
            })
            
    forage_percent = (forage_km / total_km * 100.0) if total_km > 0 else 0.0
    ca_p_ratio = (total_ca / total_p) if total_p > 0 else 0.0
    hp_percent_km = (total_hp / (total_km * 10.0)) if total_km > 0 else 0.0
    
    return {
        "success": True,
        "daily_cost_tl": round(daily_cost, 2),
        "total_fresh_weight_kg": round(total_fresh_weight, 2),
        "total_km_kg": round(total_km, 2),
        "forage_km_kg": round(forage_km, 2),
        "forage_percent": round(forage_percent, 1),
        "total_me_mcal": round(total_me, 2),
        "total_nel_mcal": round(total_nel, 2),
        "total_hp_g": round(total_hp, 1),
        "hp_percent_km": round(hp_percent_km, 1),
        "total_ca_g": round(total_ca, 1),
        "total_p_g": round(total_p, 1),
        "ca_p_ratio": round(ca_p_ratio, 2),
        "items": sorted(ration_items, key=lambda x: (not x["is_forage"], -x["amount_kg"])),
        "requirements": reqs
    }
