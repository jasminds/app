import streamlit as st
import google.generativeai as genai
import pandas as pd
import pdfplumber
from io import BytesIO
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI Researcher Assistant", layout="wide")

st.title("🤖 AI Jurnal IMRaD Extractor")
st.markdown("""
Aplikasi ini menggunakan **Google Gemini Pro** untuk membaca jurnalmu.
Dia paham konteks (ID/EN), jadi tidak masalah apakah itu "Method", "Material", atau "Metode Penelitian".
""")

# --- INPUT API KEY ---
# Di sidebar agar rapi
with st.sidebar:
    st.header("🔑 Kunci Akses")
    api_key = st.text_input("Masukkan Google Gemini API Key", type="password")
    st.markdown("[Dapatkan API Key Gratis di sini](https://aistudio.google.com/app/apikey)")
    st.info("Privasi: File PDF diproses di memori dan dikirim ke Google untuk dibaca, tidak disimpan permanen.")

# --- FUNGSI EKSTRAKSI ---
def extract_data_with_gemini(text_content, api_key):
    # Konfigurasi Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # Menggunakan model flash agar cepat dan murah

    # Prompt (Perintah) untuk AI - Ini kuncinya!
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

    4. Format output HARUS berupa JSON murni agar bisa saya convert ke Excel. Jangan ada markdown ```json```.

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

    4. Pastikan output JSON murni, JANGAN ada kata pengantar, penutup, atau Markdown JSON (e.g., JANGAN gunakan ```json ... ```).
    Berikut adalah teks jurnalnya (dipotong 30.000 karakter pertama agar muat):
    {text_content[:30000]}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# --- FUNGSI BACA PDF ---
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extract = page.extract_text()
            if extract: text += extract + "\n"
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

            # 2. Kirim ke AI
            try:
                json_string = extract_data_with_gemini(raw_text, api_key)

                # Membersihkan format JSON dari AI (kadang AI nambahin ```json di awal)
                json_string = json_string.replace("```json", "").replace("```", "").strip()

                import json
                data_dict = json.loads(json_string)
                data_dict["Filename"] = file.name # Tambah nama file
                results.append(data_dict)

            except Exception as e:
                st.error(f"Gagal memproses {file.name}. Error: {e}")

            progress_bar.progress((i + 1) / len(uploaded_files))
            time.sleep(1) # Istirahat sebentar agar tidak kena limit

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
