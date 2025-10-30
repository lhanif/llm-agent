import uuid
import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, List
from .database import db
from .ai_service import ai_service
from .quiz_manager import quiz_manager
from .study_manager import study_manager, StudySessionState
from .utils import send_long_message, ensure_user_registered

class StudyConfirmationView(discord.ui.View):
    def __init__(self, command_instance, study_plan: dict, channel: discord.TextChannel, original_prompt: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.command_instance = command_instance
        self.study_plan = study_plan
        self.channel = channel
        self.original_prompt = original_prompt

    @discord.ui.button(label="Mulai Belajar", style=discord.ButtonStyle.green)
    async def start_study(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        try:
            session = study_manager.create_session(
                user_id,
                self.study_plan["topic"],
                self.study_plan,
                self.channel
            )
            
            # Start the session
            await session.start_study_interval()
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            button.label = "Sesi Dimulai"
            await interaction.response.edit_message(view=self)
            
            # Send confirmation
            await interaction.followup.send(
                f"🎯 **Sesi Belajar Dimulai!**\n"
                f"Topik: **{self.study_plan['topic']}**\n"
                f"Durasi Total: **{self.study_plan['total_duration_minutes']}** menit\n"
                f"Jumlah Sesi: **{len(self.study_plan['sessions'])}**\n\n"
                f"Anda dapat mengajukan pertanyaan tentang topik ini selama sesi belajar!\n"
                f"Sesi pertama akan dimulai dalam beberapa detik..."
            )
            
        except Exception as e:
            print(f"❌ Error starting study session: {e}")
            await interaction.response.send_message(
                "❌ Terjadi kesalahan saat memulai sesi belajar. Silakan coba lagi.",
                ephemeral=True
            )

    @discord.ui.button(label="Perbaiki Rencana", style=discord.ButtonStyle.secondary)
    async def refine_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show modal for refinement input immediately
        modal = StudyPlanRefinementModal(self.original_prompt)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Batalkan", style=discord.ButtonStyle.red)
    async def cancel_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send(
            "❌ Rencana belajar dibatalkan. Gunakan `/ilham study` untuk membuat rencana baru.",
            ephemeral=True
        )

class StudyPlanRefinementModal(discord.ui.Modal, title="Perbaiki Rencana Belajar"):
    def __init__(self, original_prompt: str):
        super().__init__()
        self.original_prompt = original_prompt

    feedback = discord.ui.TextInput(
        label="Apa yang ingin Anda ubah dari rencana ini?",
        placeholder="Contoh: Kurangi durasi tiap sesi, tambah waktu istirahat, dsb.",
        style=discord.TextStyle.paragraph,
        required=True,
        min_length=10,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # First, acknowledge the modal submission
        await interaction.response.send_message("⏳ Membuat rencana belajar baru berdasarkan feedback Anda...")
        
        try:
            # Create refined prompt
            refined_prompt = (
                f"Rencana Awal: {self.original_prompt}\n"
                f"Feedback: {self.feedback.value}\n"
                f"Harap sesuaikan rencana belajar berdasarkan feedback tersebut."
            )
            
            # Disable the original message's view if it exists
            if interaction.message:
                try:
                    await interaction.message.edit(view=None)
                except:
                    pass  # Ignore if we can't edit the original message
            
            # Generate new study plan using ai_service directly
            study_plan = await ai_service.generate_study_plan(refined_prompt)
            if not study_plan:
                await interaction.followup.send(
                    "❌ Maaf, saya tidak dapat memahami rencana belajar dari feedback Anda. Mohon coba lagi dengan format yang lebih jelas.",
                    ephemeral=True
                )
                return

            # Format and display the new plan
            sessions_text = "\n".join([
                f"**Sesi {i+1}**\n"
                f"📚 Fokus: {session['focus']}\n"
                f"⏱️ Durasi: {session['duration']} menit\n"
                f"☕ Istirahat: {session['break']} menit"
                for i, session in enumerate(study_plan["sessions"])
            ])
            
            plan_text = (
                f"📋 **Rencana Belajar yang Disesuaikan**\n"
                f"Topik: **{study_plan['topic']}**\n"
                f"Total Waktu: **{study_plan['total_duration_minutes']}** menit\n"
                f"Deskripsi: {study_plan['description']}\n\n"
                f"**Detail Sesi:**\n{sessions_text}\n\n"
                f"Pilih opsi di bawah untuk melanjutkan:"
            )
            
            # Create and show new confirmation view
            view = StudyConfirmationView(
                interaction.client.tree.get_command("ilham").module,
                study_plan,
                interaction.channel,
                refined_prompt
            )
            
            # Delete the "creating plan" message
            await interaction.delete_original_response()
            
            # Send the new plan
            await interaction.followup.send(plan_text, view=view)
            
        except Exception as e:
            print(f"❌ Error refining study plan: {e}")
            await interaction.followup.send(
                "❌ Terjadi kesalahan saat memperbaiki rencana belajar. Silakan coba membuat rencana baru dengan /ilham study",
                ephemeral=True
            )

    async def on_timeout(self):
        # Disable the button when the view times out
        self.start_study.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

class QuizCommands(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="ilham", description="Ilham Commands")
        self.bot = bot

    @app_commands.command(name="quiz", description="Buat kuis berdasarkan prompt kamu (cth: kuis integral kesulitan mudah jumlah 3)")
    @ensure_user_registered()
    async def quiz(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        username = interaction.user.name
        
        # Save or update user
        db.upsert_user(user_id, username)

        # Generate questions
        topic_keyword, difficulty, jumlah_soal, questions = await ai_service.generate_soal(prompt)
        
        if not questions:
            await interaction.followup.send(f"❌ Gagal membuat soal dari prompt Anda: *{prompt}*. Coba lagi dengan format yang lebih jelas.")
            return
            
        # Match topic with existing ones
        existing_topics = db.get_existing_topics(difficulty)
        topic_to_save = await ai_service.match_topic(topic_keyword, difficulty, existing_topics)
        
        # Create quiz session in database
        session = quiz_manager.get_session(user_id)
        if session:
            quiz_manager.end_session(user_id)
            
        session_id = quiz_manager.create_session(user_id, questions, topic_to_save, difficulty, []).session_id
        db.create_quiz_session(session_id, user_id, topic_to_save, difficulty, len(questions))
        
        # Save questions and get IDs
        quiz_question_ids = []
        for i, q in enumerate(questions):
            qid = str(uuid.uuid4())
            db.save_question(qid, topic_to_save, difficulty, q["question"], q["answer"], q["explanation"])
            qq_id = db.save_quiz_question(session_id, qid, i + 1)
            if qq_id:
                quiz_question_ids.append(qq_id)
            else:
                await interaction.followup.send("❌ Kesalahan fatal (DB-ID). Silakan coba lagi.")
                return

        # Create new session with question IDs
        session = quiz_manager.create_session(user_id, questions, topic_to_save, difficulty, quiz_question_ids)
        
        # Send first question
        first_question = session.get_current_question()
        options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(first_question["options"])])
        await interaction.followup.send(
            f"🎯 **Kuis Dimulai!**\nTopik: **{topic_to_save.title()}**\nKesulitan: **{difficulty.upper()}**\n"
            f"Jumlah Soal: **{len(questions)}**\n\n"
            f"**Pertanyaan 1:** {first_question['question']}\n\n{options_text}\n\n"
            f"Balas dengan `/answer <huruf>` untuk menjawab."
        )

    @app_commands.command(name="answer", description="Jawab pertanyaan kuis aktif kamu")
    @ensure_user_registered()
    async def answer(self, interaction: discord.Interaction, pilihan: str):
        user_id = str(interaction.user.id)
        session = quiz_manager.get_session(user_id)
        
        if not session:
            await interaction.response.send_message("❌ Kamu belum memulai kuis.")
            return

        # Check answer
        is_correct = session.check_answer(pilihan)
        if is_correct:
            session.score += 1
            
        # Save answer to database
        qq_id = session.get_current_question_id()
        duration = session.get_answer_duration()
        db.save_answer(qq_id, user_id, pilihan.upper(), is_correct, duration)
        
        # Update performance summary
        db.update_performance(user_id, session.topic, session.difficulty, is_correct)

        # Send feedback
        current_q = session.get_current_question()
        feedback = "✅ **Benar!**" if is_correct else f"❌ **Salah.** Jawaban benar: **{current_q['answer']}**\n"
        feedback += f"Penjelasan: {current_q['explanation']}" if not is_correct else ""
        await interaction.response.send_message(feedback)

        # Move to next question
        session.move_to_next_question()
        
        if not session.is_finished():
            next_q = session.get_current_question()
            options_text = "\n".join([f"{chr(65+i)}. {opt}" for i, opt in enumerate(next_q["options"])])
            await interaction.followup.send(
                f"**Pertanyaan {session.current+1}:** {next_q['question']}\n\n{options_text}\n\n"
                f"Balas dengan `/answer <huruf>` untuk menjawab."
            )
        else:
            stats = session.get_final_stats()
            await interaction.followup.send(
                f"🎉 **Kuis selesai!**\n"
                f"✅ **Skor Kamu:** {stats['score']}/{stats['total_questions']} (**{stats['percentage']:.2f}%**)\n"
                f"⏱️ **Waktu Total:** {stats['total_duration']}\n"
                f"⏳ **Rata-rata Waktu/Soal:** {stats['avg_duration_per_q']:.2f} detik"
            )
            quiz_manager.end_session(user_id)

    @app_commands.command(name="performance", description="Lihat performa kamu dan dapatkan saran belajar")
    @ensure_user_registered()
    async def performance(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        performance_data = db.get_performance_summary(user_id)
        
        if not performance_data:
            await interaction.followup.send("📊 Belum ada data performa.")
            return

        # Generate performance text
        data_text = "📈 **Performa Kamu:**\n"
        for row in performance_data:
            data_text += "---\n"
            data_text += f"🧩 Topik: **{row['topic'].title()}** (Kesulitan: {row['difficulty']})\n" 
            data_text += f"⭐ Akurasi: **{row['avg_score']:.2f}%** ({row['total_correct']}/{row['total_questions']} Benar)\n"
            data_text += f"📅 Terakhir diperbarui: {row['last_updated'][:10]}\n"
        
        # Generate AI suggestion
        suggestion_text = await ai_service.generate_performance_suggestion(performance_data)

        # Send messages
        await send_long_message(interaction, data_text)
        await send_long_message(interaction, suggestion_text)

    @app_commands.command(
        name="recommend",
        description="Dapatkan rekomendasi belajar dan kuis personal berdasarkan riwayat pembelajaran Anda"
    )
    @ensure_user_registered()
    async def recommend(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            # Get comprehensive learning history
            learning_history = db.get_user_learning_history(user_id)
            
            if not learning_history["topics_data"]:
                await interaction.followup.send(
                    "❌ Belum ada riwayat pembelajaran. Coba selesaikan beberapa kuis atau sesi belajar terlebih dahulu!"
                )
                return
            
            # Generate recommendations
            recommendations = await ai_service.generate_recommendations(learning_history)
            
            # Send recommendations
            await send_long_message(
                interaction,
                f"📚 **Rekomendasi Pembelajaran Personal Anda**\n\n{recommendations}"
            )
            
        except Exception as e:
            print(f"❌ Error generating recommendations: {e}")
            await interaction.followup.send(
                "❌ Terjadi kesalahan saat menghasilkan rekomendasi. Silakan coba lagi nanti."
            )

    @app_commands.command(
        name="study",
        description="Mulai sesi belajar dengan durasi yang fleksibel (contoh: belajar kalkulus 2 jam)"
    )
    @app_commands.describe(
        prompt="Jelaskan apa yang ingin Anda pelajari dan berapa lama waktu yang tersedia"
    )
    @ensure_user_registered()
    async def study(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            # Check if user already has an active session
            if study_manager.get_session(user_id):
                await interaction.followup.send("❌ Anda sudah memiliki sesi belajar yang aktif!")
                return

            # Generate study plan from prompt
            study_plan = await ai_service.generate_study_plan(prompt)
            if not study_plan:
                await interaction.followup.send("❌ Maaf, saya tidak dapat memahami rencana belajar dari prompt Anda. Mohon coba lagi dengan format yang lebih jelas.")
                return

            # Extract details from first session
            topic = study_plan["topic"]
            first_session = study_plan["sessions"][0]
            duration = first_session["duration"]
            break_duration = first_session["break"]

            if duration < 1 or break_duration < 1:
                await interaction.followup.send("❌ Durasi belajar dan istirahat harus minimal 1 menit!")
                return

            # Show study plan and confirmation button
            sessions_text = "\n".join([
                f"**Sesi {i+1}**\n"
                f"📚 Fokus: {session['focus']}\n"
                f"⏱️ Durasi: {session['duration']} menit\n"
                f"☕ Istirahat: {session['break']} menit"
                for i, session in enumerate(study_plan["sessions"])
            ])
            
            plan_text = (
                f"📋 **Rencana Belajar**\n"
                f"Topik: **{topic}**\n"
                f"Total Waktu: **{study_plan['total_duration_minutes']}** menit\n"
                f"Deskripsi: {study_plan['description']}\n\n"
                f"**Detail Sesi:**\n{sessions_text}\n\n"
                f"Pilih opsi di bawah untuk melanjutkan:"
            )
            
            view = StudyConfirmationView(self, study_plan, interaction.channel, prompt)
            await interaction.followup.send(plan_text, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error starting study session: {str(e)}")
            study_manager.end_session(user_id)

    @app_commands.command(name="ask", description="Ask a question during your study session")
    @ensure_user_registered()
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        # Get active session
        session = study_manager.get_session(user_id)
        if not session:
            await interaction.followup.send("❌ You don't have an active study session! Start one with `/quiz_bot study`")
            return

        if not session.can_ask_questions():
            await interaction.followup.send("⏸️ You're on a break! Questions are paused during break intervals.")
            return

        # Get answer from AI
        answer = await ai_service.answer_study_question(session.topic, question)
        
        # Save question and answer to session history
        session.add_question(question, answer)
        
        await send_long_message(
            interaction,
            f"📝 **Your Question:** {question}\n\n"
            f"🤖 **Answer:**\n{answer}"
        )

    @app_commands.command(name="end_study", description="End your current study session")
    @ensure_user_registered()
    async def end_study(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        session = study_manager.get_session(user_id)
        if not session:
            await interaction.followup.send("❌ You don't have an active study session!")
            return

        await session.end_session()
        study_manager.end_session(user_id)
        await interaction.followup.send("✅ Study session ended successfully!")