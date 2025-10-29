import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client, Client
from groq import Groq
from dotenv import load_dotenv
import uuid
import datetime

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ------------------------------------------------------------
# Inisialisasi klien
# ------------------------------------------------------------
groq_client = Groq(api_key=GROQ_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# ------------------------------------------------------------
# Fungsi bantu
# ------------------------------------------------------------
def normalize_question(q):
    """Pastikan setiap soal punya struktur lengkap"""
    normalized = {
        "question": q.get("question") or q.get("pertanyaan") or q.get("soal") or "Pertanyaan tidak tersedia.",
        "options": q.get("options") or q.get("pilihan") or q.get("choices") or [],
        "answer": q.get("answer") or q.get("jawaban") or "A",
        "explanation": q.get("explanation") or q.get("penjelasan") or "",
    }
    if not isinstance(normalized["options"], list) or len(normalized["options"]) == 0:
        normalized["options"] = ["Tidak ada opsi A", "Tidak ada opsi B", "Tidak ada opsi C", "Tidak ada opsi D"]
    return normalized

async def generate_soal(full_prompt: str):
    """Menggunakan Groq untuk mengekstrak metadata dan menghasilkan soal dalam satu panggilan API."""
    prompt = f"""
    Dari permintaan pengguna berikut: "{full_prompt}",
    lakukan 2 langkah:
    1. Ekstrak 'topic' (kata kunci utama), 'difficulty' (wajib: mudah, sedang, atau sulit), dan 'jumlah_soal' (wajib: integer). Jika tidak disebutkan, gunakan default: difficulty='sedang', jumlah_soal=5.
    2. Buat soal kuis berdasarkan metadata yang diekstrak.
    
    Formatkan hasil **HANYA dalam JSON OBJECT** seperti ini tanpa teks, penjelasan, atau *backtick* tambahan:
    
    {{
      "topic": "kata kunci topik yang diekstrak",
      "difficulty": "mudah/sedang/sulit",
      "jumlah_soal": 5,
      "questions": [
        {{
          "question": "Soal pertama...",
          "options": ["Opsi A", "Opsi B", "Opsi C", "Opsi D"],
          "answer": "A",
          "explanation": "Penjelasan jawaban..."
        }}
      ]
    }}
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        result_text = chat_completion.choices[0].message.content.strip()
        
        # Pembersihan
        result_text = result_text.strip('`').strip()
        if result_text.lower().startswith("json"):
            result_text = result_text[4:].strip()
            
        data = json.loads(result_text.replace("'", '"'))
        
        # Ekstrak data yang dibutuhkan
        topic_keyword = data.get("topic", "Topik Umum")
        extracted_difficulty = data.get("difficulty", "sedang").lower()
        extracted_jumlah_soal = int(data.get("jumlah_soal", 5)) # Pastikan integer
        soal_list = data.get("questions", [])
        
        valid_soal = [normalize_question(s) for s in soal_list]
        
        return topic_keyword, extracted_difficulty, extracted_jumlah_soal, valid_soal
        
    except Exception as e:
        print(f"❌ Error parsing Groq result (Unified): {e}")
        return "Topik Umum", "sedang", 0, []

# ------------------------------------------------------------
# Logic untuk menyimpan dan menjalankan quiz
# ------------------------------------------------------------
active_sessions = {}

@bot.event
async def on_ready():
    print(f"✅ Bot siap login sebagai {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sinkronisasi {len(synced)} slash command")
    except Exception as e:
        print(f"❌ Error sync command: {e}")

@bot.tree.command(name="quiz", description="Buat kuis berdasarkan prompt kamu (cth: kuis integral kesulitan mudah jumlah 3)")
async def quiz(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    username = interaction.user.name
    
    supabase.table("users").upsert({"id": user_id, "username": username}).execute()

    # PANGGILAN TUNGGAL: Ekstraksi dan Generasi Soal
    topic_keyword, difficulty, jumlah_soal, questions = await generate_soal(prompt)
    
    if not questions or len(questions) == 0:
        await interaction.followup.send(f"❌ Gagal membuat soal dari prompt Anda: *{prompt}*. Coba lagi dengan format yang lebih jelas (misal: 'kuis materi integral kesulitan mudah jumlah 3').")
        return
        
    # Sesuaikan jumlah soal yang disimpan berdasarkan jumlah soal yang benar-benar dibuat
    jumlah_soal_sebenarnya = len(questions)
        
    # --- Simpan Sesi ---
    session_id = str(uuid.uuid4())
    supabase.table("quiz_sessions").insert({
        "id": session_id,
        "user_id": user_id,
        "topic": topic_keyword, 
        "difficulty": difficulty,
        "total_questions": jumlah_soal_sebenarnya
    }).execute()

    quiz_question_ids = []
    
    # --- Simpan Soal ---
    for i, q in enumerate(questions):
        qid = str(uuid.uuid4())
        
        supabase.table("questions").insert({
            "id": qid,
            "topic": topic_keyword,
            "difficulty": difficulty,
            "question_text": q["question"],
            "correct_answer": q["answer"],
            "explanation": q["explanation"]
        }).execute()
        
        # 2. Simpan ke tabel quiz_questions dan ambil ID yang baru di-generate
        # FIX KOMPATIBILITAS: Hapus .select("id") untuk menghindari AttributeError
        result_quiz_q = supabase.table("quiz_questions").insert({
            "session_id": session_id,
            "question_id": qid,
            "sequence": i + 1
        }).execute() 

        # Ambil ID yang benar dari hasil INSERT
        if result_quiz_q.data and len(result_quiz_q.data) > 0:
            qq_id = result_quiz_q.data[0]["id"]
            quiz_question_ids.append(qq_id)
        else:
            # Jika ini terjadi, artinya insert berhasil tapi ID tidak dikembalikan.
            # INI ADALAH TITIK KEGAGALAN JIKA LIBRARY TERLALU LAMA.
            print(f"❌ Gagal mendapatkan ID quiz_questions untuk soal {i+1}. Coba upgrade postgrest-py.")
            await interaction.followup.send("❌ Kesalahan fatal (DB-ID). Silakan coba lagi atau upgrade library Supabase/PostgREST Anda.")
            return

    # --- Simpan ke cache bot ---
    active_sessions[user_id] = {
        "session_id": session_id,
        "questions": questions,
        "quiz_question_ids": quiz_question_ids, 
        "topic": topic_keyword,
        "difficulty": difficulty,
        "current": 0,
        "score": 0,
        "start_time": datetime.datetime.now()
    }

    first_question = questions[0]
    options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(first_question["options"])])
    await interaction.followup.send(
        f"🎯 **Kuis Dimulai!**\nTopik: **{topic_keyword}**\nKesulitan: **{difficulty.upper()}**\nJumlah Soal: **{jumlah_soal_sebenarnya}**\n\n"
        f"**Pertanyaan 1:** {first_question['question']}\n\n{options_text}\n\n"
        f"Balas dengan `/answer <huruf>` untuk menjawab."
    )

@bot.tree.command(name="answer", description="Jawab pertanyaan kuis aktif kamu")
async def answer(interaction: discord.Interaction, pilihan: str):
    user_id = str(interaction.user.id)
    if user_id not in active_sessions:
        await interaction.response.send_message("❌ Kamu belum memulai kuis.")
        return

    session = active_sessions[user_id]
    idx = session["current"]
    questions = session["questions"]
    q = questions[idx]
    
    quiz_qq_id = session["quiz_question_ids"][idx] 

    benar = (pilihan.upper() == q["answer"].upper())
    session["score"] += 1 if benar else 0
    durasi = (datetime.datetime.now() - session["start_time"]).total_seconds()

    # Simpan jawaban ke DB
    supabase.table("quiz_answers").insert({
        "quiz_question_id": quiz_qq_id,
        "user_id": user_id,
        "user_answer": pilihan.upper(),
        "is_correct": benar,
        "duration_seconds": durasi
    }).execute()

    # Update performance_summary
    topic_prompt = session["topic"]
    perf = supabase.table("performance_summary").select("*").eq("user_id", user_id).eq("topic", topic_prompt).execute()
    
    if perf.data:
        data = perf.data[0]
        total_correct = data["total_correct"] + (1 if benar else 0)
        total_questions = data["total_questions"] + 1
        avg_score = total_correct / total_questions * 100
        supabase.table("performance_summary").update({
            "total_questions": total_questions,
            "total_correct": total_correct,
            "avg_score": avg_score,
            "last_updated": datetime.datetime.now().isoformat()
        }).eq("id", data["id"]).execute()
    else:
        supabase.table("performance_summary").insert({
            "user_id": user_id,
            "topic": topic_prompt,
            "difficulty": session["difficulty"],
            "total_sessions": 1,
            "total_questions": 1,
            "total_correct": (1 if benar else 0),
            "avg_score": (100 if benar else 0)
        }).execute()

    # Kirim feedback
    feedback = "✅ **Benar!**" if benar else f"❌ **Salah.** Jawaban benar: **{q['answer']}**\nPenjelasan: {q['explanation']}"
    await interaction.response.send_message(feedback)

    # Pindah ke soal berikutnya
    session["current"] += 1
    if session["current"] < len(questions):
        next_q = questions[session["current"]]
        options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(next_q["options"])])
        await interaction.followup.send(
            f"**Pertanyaan {session['current']+1}:** {next_q['question']}\n\n{options_text}\n\n"
            f"Balas dengan `/answer <huruf>` untuk menjawab."
        )
    else:
        await interaction.followup.send(f"🎉 **Kuis selesai!** Skor kamu: **{session['score']}/{len(questions)}**")
        del active_sessions[user_id]

@bot.tree.command(name="performance", description="Lihat performa kamu")
async def performance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    res = supabase.table("performance_summary").select("*").eq("user_id", user_id).execute()
    if not res.data:
        await interaction.response.send_message("📊 Belum ada data performa.")
        return

    text = "📈 **Performa Kamu:**\n"
    for row in res.data:
        text += f"---"
        text += f"🧩 Topik: **{row['topic']}** (Kesulitan: {row['difficulty']})\n"
        text += f"⭐ Akurasi: **{row['avg_score']:.2f}%** ({row['total_correct']}/{row['total_questions']} Benar)\n"
        text += f"📅 Terakhir diperbarui: {row['last_updated']}\n"
    await interaction.response.send_message(text)

# ------------------------------------------------------------
# Jalankan bot
# ------------------------------------------------------------
bot.run(DISCORD_TOKEN)