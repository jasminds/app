import streamlit as st
import google.generativeai as genai
import pandas as pd
import pdfplumber
from io import BytesIO
import time
import json 
import re 

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Researcher Assistant", layout="wide")

st.title("🤖 AI Jurnal IMRaD Extractor (Final Vibe Coder)")
st.markdown("""
Aplikasi ini menggunakan model **Gemini 2.5 Flash** yang stabil untuk mengekstrak struktur IMRaD dari PDF jurnal.
""")

# --- INPUT API KEY ---
with st.sidebar:
    st.header("🔑 Kunci Akses")
    api_key = st.text_input("Masukkan Google Gemini API Key", type="password")
    st.markdown("[Dapatkan API Key Gratis di Google AI Studio](https://aistudio.google.com/app/apikey)")
    st.info("Key hanya disimpan di memori browser Anda selama sesi ini.")

# --- FUNGSI EKSTRAKSI ---
def extract_data_with_gemini(text_content, api_key):
    # Konfigurasi Gemini
    try:
        genai.configure(api_key=api_key)
        # Menggunakan gemini-2.5-flash karena lebih stabil dan tersedia luas daripada 1.5
        model = genai.GenerativeModel('gemini-2.5-flash') 
    except Exception as e:
        return f"Error: API Key Configuration Failed - {e}"

    # Prompt (Perintah) untuk AI - Instruksi Ketat
    prompt = f"""
    Kamu adalah asisten peneliti ahli teks korpus. Tugasmu adalah mengekstrak struktur IMRaD dari teks jurnal ilmiah berikut.
    
    Instruksi Khusus:
    1. Teks jurnal ini bisa dalam Bahasa Indonesia atau Inggris. Pahami konteksnya.
    2. Ekstrak bagian-bagian berikut secara TEPAT (copy-paste isi teksnya, jangan meringkas/summarize kecuali diminta):
       - Title (Judul)
       - Authors (Penulis)
       - Year (Tahun)
       - Institution (Afiliasi)
       - Abstract_ID (Abstrak Indo)
       - Abstract_EN (Abstrak Inggris)
       - Keywords
       - Introduction (Pendahuluan/Latar Belakang)
       - Method (Metode/Material/Cara Kerja/Metodologi)
       - Result (Hasil/Temuan - Jika terpisah dari diskusi)
       - Discussion (Pembahasan/Diskusi - Jika terpisah)
       - Result_Discussion (Jika Hasil dan Pembahasan digabung dalam satu bab, taruh disini)
       - Conclusion (Kesimpulan/Penutup)
    
    3. Jika bagian tertentu tidak ada, isi dengan "TIDAK DITEMUKAN".
    
    4. Format output HARUS berupa JSON murni agar bisa saya convert ke Excel. 
    
    PENTING: JANGAN ada teks pengantar seperti "Berikut hasil ekstraksinya:" atau "Tentu, ini JSON-nya.".
    Berikan HANYA dan SELURUHNYA string JSON, dimulai dari karakter {{ dan diakhiri dengan karakter }}.
    JANGAN gunakan format Markdown JSON (e.g., JANGAN gunakan ```json ... ```).

    Format JSON yang diinginkan:
    {{
        "Title": "...",
        "Authors": "...",
        "Year": "...",
        "Institution": "...",
        "Abstract_ID": "...",
        "Abstract_EN": "...",
        "Keywords": "...",
        "Introduction": "...",
        "Method": "...",
        "Result": "...",
        "Discussion": "...",
        "Result_Discussion": "...",
        "Conclusion": "..."
    }}

    Berikut adalah teks jurnalnya (dipotong 30.000 karakter pertama agar muat):
    {text_content[:30000]} 
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: Failed API Call - {e}"

# --- FUNGSI BACA PDF ---
def read_pdf(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                extract = page.extract_text()
                if extract: text += extract + "\n"
    except Exception as e:
        st.error(f"Gagal membaca PDF: Pastikan file tidak terproteksi atau korup. Error: {
