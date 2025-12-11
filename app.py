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
        # Menggunakan gemini-2.5-flash karena stabil dan tersedia luas
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
        # BARIS 100 YANG SUDAH KITA PERBAIKI:
        st.error(f"Gagal membaca PDF: Pastikan file tidak terproteksi atau korup. Error: {e}")
        return None
    return text

# --- MAIN APP ---
uploaded_files = st.file_uploader("Upload PDF Jurnal (Bisa Banyak)", type=["pdf"], accept_multiple_files=True)

if uploaded_files and api_key:
    if st.button("🚀 Mulai Ekstraksi dengan AI"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, file in enumerate(uploaded_files):
            status_text.text(f"Sedang membaca: {file.name}...")
            
            # 1. Baca Teks Mentah
            raw_text = read_pdf(file)
            if raw_text is None:
                continue

            # 2. Kirim ke AI
            try:
                json_string = extract_data_with_gemini(raw_text, api_key)
                
                # --- LOGIKA PEMBERSAHAN JSON AGAR LEBIH TANGGUH ---
                json_string = json_string.replace("```json", "").replace("```", "").strip()
                
                # Cari kurawal buka { pertama dan kurawal tutup } terakhir untuk mengisolasi JSON murni
                start_index = json_string.find('{')
                end_index = json_string.rfind('}')
                
                if start_index != -1 and end_index != -1 and end_index > start_index:
                    json_string = json_string[start_index : end_index + 1]
                else:
                    # Jika tidak ada { dan } yang valid
                    st.warning(f"File {file.name} gagal menghasilkan format JSON yang valid. Output AI mentah: {json_string[:100]}...")
                    continue

                # Cek apakah ada pesan error dari API yang muncul di output
                if "Error: Failed API Call" in json_string:
                    st.error(f"Gagal memproses {file.name}. Pesan API: {json_string}") 
                    continue

                # Coba load JSON
                data_dict = json.loads(json_string)
                data_dict["Filename"] = file.name # Tambah nama file
                results.append(data_dict)
                
            except json.JSONDecodeError as e:
                # Menangani kasus di mana pembersihan di atas masih gagal
                st.error(f"Gagal memproses {file.name}. Error JSON: {e}. Output mentah AI mungkin kosong atau rusak.")
                st.text(f"Output mentah yang gagal diproses: {json_string[:200]}...")
            except Exception as e:
                st.error(f"Gagal memproses {file.name}. Error tak terduga: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
            time.sleep(1) 

        status_text.text("Selesai!")
        
        # Tampilkan Hasil
        if results:
            df = pd.DataFrame(results)
            
            # Atur urutan kolom agar rapi
            cols = ["Filename", "Title", "Authors", "Year", "Institution", "Abstract_ID", "Abstract_EN", "Keywords", "Introduction", "Method", "Result", "Discussion", "Result_Discussion", "Conclusion"]
            # Filter kolom yang ada saja (jaga-jaga error)
            cols = [c for c in cols if c in df.columns]
            df = df[cols]

            st.dataframe(df)

            # Download Button
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Excel Hasil Ekstraksi",
                data=output.getvalue(),
                file_name="hasil_ekstraksi_ai.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif uploaded_files and not api_key:
    st.warning("⚠️ Mohon masukkan API Key di sidebar sebelah kiri dulu ya.")
