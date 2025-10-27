import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from groq import Groq

# Muat variabel lingkungan
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Inisialisasi klien Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# Inisialisasi bot Discord dengan intents
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f"🧩 Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Sync failed: {e}")

@tree.command(name="ping", description="Cek apakah bot online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Bot online dan siap belajar!")

@tree.command(name="coba", description="Kirim string ke Groq API dan tampilkan hasil")
async def coba(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()  # menandakan bot sedang memproses

    try:
        # Mengirim permintaan ke Groq API
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        result_text = chat_completion.choices[0].message.content
    except Exception as e:
        result_text = f"❌ Terjadi error saat menghubungi Groq API: {e}"

    # Chunking agar tidak melebihi batas Discord 2000 karakter
    print(result_text)
    chunk_size = 1000
    for i in range(0, len(result_text), chunk_size):
        chunk = result_text[i:i+chunk_size]
        await interaction.followup.send(f"💡 Hasil dari Groq API:\n{chunk}" if i == 0 else chunk)


# Jalankan bot
bot.run(TOKEN)
