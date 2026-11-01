# -*- coding: utf-8 -*-
"""
Hugging Face Spaces - Ücretsiz 7/24 Web Başlatıcı
Yüksek Mühendis M. Fatih CEYHAN Rasyon Yönetim Sistemi
"""

import threading
import gradio as gr
from bot import run_bot

# Telegram botunu arka planda kesintisiz çalıştıran thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

def get_status():
    return "🟢 AKTİF - Telegram Botu (@Rasyonfatih_bot) 7/24 çalışıyor!"

with gr.Blocks(title="Rasyon Robotu - Yk. Müh. M. Fatih CEYHAN") as demo:
    gr.Markdown("# 🐂 Yapay Zekâ Destekli Rasyon Robotu")
    gr.Markdown("### **Yüksek Mühendis M. Fatih CEYHAN** Çiftlik ve Rasyon Yönetim Sistemi")
    
    with gr.Row():
        status_box = gr.Textbox(value=get_status(), label="Sistem Durumu", interactive=False)
        
    gr.Markdown(
        """
        ---
        ### 📱 Telegram Botuna Bağlanın:
        * **Bot Adresi:** [@Rasyonfatih_bot](https://t.me/Rasyonfatih_bot)
        * **Özellikler:** 
          * NRC ve Selçuk Üniversitesi standartlarında en ucuz rasyon çözümü
          * Sürü 30 günlük yem tonaj ve maliyet Excel (.xlsx) raporu
          * Telegram üzerinden anlık yem fiyatı ve yeni yem güncelleme
        """
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
