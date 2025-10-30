## Ilham : Personal Learning Assistant

Eduardus Bagus Wicaksono (22/493128/TK/53996)
Luthfi Hanif (22/497890/TK/54589)

Repositori ini berisi grup perintah Discord (`/ilham`) untuk workflow kuis dan belajar, wrapper layanan AI, serta layer penyimpanan sederhana.

## Fitur
- Membuat kuis dari prompt bahasa alami (/ilham quiz)
- Menjawab pertanyaan kuis dan melihat performa (/ilham answer, /ilham performance)
- Membuat rencana belajar dan menjalankan sesi belajar terjadwal (/ilham study, /ilham ask, /ilham end_study)
- Menyimpan kuis, jawaban, performa, dan sesi belajar ke Supabase
- Integrasi AI untuk pembuatan soal, penjelasan, dan rekomendasi

## Cara Instalasi & Menjalankan (Windows / PowerShell)
1. Clone repo dan buka terminal di folder project.

2. Buat dan aktifkan virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependensi:

```powershell
pip install -r requirements.txt
```

4. Salin file contoh environment dan isi kredensial Anda:

```powershell
copy .env.example .env
# Edit .env dengan API key dan URL Anda
```

5. Jalankan bot secara lokal:

```powershell
python main.py
```

Catatan:
- `main.py` akan menjalankan bot Discord menggunakan variabel dari `.env`.
- Gunakan server Discord pengembangan untuk testing sebelum dipasang di server produksi.

## Konfigurasi (.env)

Semua konfigurasi sensitif disimpan di file `.env` pada root project. Jangan pernah commit data rahasia ke repository.

Buat `.env` dari `.env.example` dan isi variabel berikut:

- DISCORD_TOKEN — Token bot Discord Anda
- SUPABASE_URL — URL project Supabase
- SUPABASE_KEY — Service key Supabase (atau anon key untuk akses terbatas)
- OPENAI_API_KEY — API key untuk provider AI (jika digunakan)
- WHATSAPP_INTEGRATION — Placeholder (lihat bagian WhatsApp di bawah)

File `.env.example` sudah tersedia sebagai template.

## .env.example (file contoh)
File `.env.example` berisi placeholder seperti berikut:

```text
# Discord
DISCORD_TOKEN=token-bot-discord-anda

# Supabase
SUPABASE_URL=https://url-supabase-anda.supabase.co
SUPABASE_KEY=service-key-supabase-anda

# Provider AI (OpenAI / lainnya)
GROQ_API_KEY=api-key-openai-anda
```

## Daftar Perintah (/ilham)

Semua perintah tersedia di `quiz_bot/commands.py` sebagai grup perintah app bernama `ilham`.

- /ilham quiz <prompt>
  - Sintaks: `/ilham quiz prompt:"<topik> <kesulitan> jumlah <n>"`
  - Fungsi: Membuat kuis dari prompt bahasa alami. Contoh: `kuis integral kesulitan mudah jumlah 3`.

- /ilham answer <huruf>
  - Sintaks: `/ilham answer pilihan:"A|B|C|D"`
  - Fungsi: Menjawab pertanyaan kuis aktif. Bot akan mengevaluasi, menyimpan jawaban, memperbarui performa, dan lanjut ke soal berikutnya.

- /ilham performance
  - Sintaks: `/ilham performance`
  - Fungsi: Melihat performa kuis terbaru dan mendapatkan saran belajar dari AI berdasarkan data performa.

- /ilham recommend
  - Sintaks: `/ilham recommend`
  - Fungsi: Mendapatkan rekomendasi belajar dan kuis personal berdasarkan riwayat pembelajaran Anda.

- /ilham study <prompt>
  - Sintaks: `/ilham study prompt:"<apa yang ingin dipelajari + waktu tersedia>"`
  - Fungsi: Membuat rencana belajar (sesi/interval), menampilkan tombol konfirmasi, dan menjalankan sesi belajar terjadwal.

- /ilham ask <pertanyaan>
  - Sintaks: `/ilham ask question:"<pertanyaan tentang topik belajar saat ini>"`
  - Fungsi: Bertanya selama sesi belajar aktif; AI akan menjawab dan pertanyaan disimpan di riwayat sesi.

- /ilham end_study
  - Sintaks: `/ilham end_study`
  - Fungsi: Mengakhiri sesi belajar aktif dan menyimpan data ringkasan.

Catatan:
- Bot menggunakan decorator (`ensure_user_registered`) untuk memastikan user terdaftar di database secara otomatis.
- Lihat `quiz_bot/commands.py` untuk detail format pesan dan alur.

## Arsitektur Sistem

![Arsitektur placeholder](assets\image.png)



## Menjalankan Tes

Jalankan unit test dan functional test dengan pytest:

```powershell
pip install -r requirements.txt
pytest -q
```

Struktur test ada di folder `tests/` dengan subfolder `unit/` dan `functional/`.

