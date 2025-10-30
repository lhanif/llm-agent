from groq import Groq
import json
from typing import Dict, List, Tuple
from .config import config

class AIService:
    def __init__(self):
        self.groq_client = Groq(api_key=config.GROQ_API_KEY)

    async def generate_soal(self, full_prompt: str) -> Tuple[str, str, int, List[Dict]]:
        """Generate quiz questions using Groq AI."""
        prompt = f"""
        Dari permintaan pengguna berikut: "{full_prompt}",
        lakukan 2 langkah:
        1. Ekstrak 'topic' (kata kunci utama), 'difficulty' (wajib: mudah, sedang, atau sulit), dan 'jumlah_soal' (wajib: integer). Jika tidak disebutkan, gunakan default: difficulty='sedang', jumlah_soal=5.
        2. Buat soal kuis berdasarkan metadata yang diekstrak.
        
        Formatkan hasil **HANYA dalam JSON OBJECT** seperti ini tanpa teks tambahan:
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
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            result_text = chat_completion.choices[0].message.content.strip()
            
            # Clean up response
            result_text = result_text.strip('`').strip()
            if result_text.lower().startswith("json"):
                result_text = result_text[4:].strip()
                
            data = json.loads(result_text.replace("'", '"'))
            
            # Extract data
            topic_keyword = data.get("topic", "Topik Umum")
            extracted_difficulty = data.get("difficulty", "sedang").lower()
            extracted_jumlah_soal = int(data.get("jumlah_soal", 5))
            soal_list = data.get("questions", [])
            
            valid_soal = [self.normalize_question(s) for s in soal_list]
            
            return topic_keyword, extracted_difficulty, extracted_jumlah_soal, valid_soal
            
        except Exception as e:
            print(f"❌ Error generating questions: {e}")
            return "Topik Umum", "sedang", 0, []

    async def match_topic(self, new_topic: str, current_difficulty: str, existing_topics: List[str]) -> str:
        """Match new topic with existing topics."""
        if not existing_topics or new_topic in existing_topics:
            return new_topic

        topic_list = ", ".join(existing_topics)
        prompt = f"""
        Anda adalah penormalisasi topik. Tugas Anda adalah mencocokkan Topik Baru dengan salah satu Topik yang Sudah Ada, MENGINGAT KESULITANNYA SAMA.
        Jika ada kecocokan yang kuat, kembalikan Topik yang Sudah Ada tersebut. Jika tidak ada kecocokan, kembalikan Topik Baru.
        
        Kesulitan Saat Ini: {current_difficulty}
        Topik Baru: "{new_topic}"
        Topik yang Sudah Ada dengan Kesulitan SAMA: {topic_list}
        
        Tentukan Topik yang Sudah Ada mana yang paling sesuai. Jika tidak ada yang cocok, kembalikan Topik Baru.
        
        Formatkan respons Anda **HANYA dalam JSON OBJECT**:
        {{"matched_topic": "hasil topik yang dipilih (dari daftar atau topik baru)"}}
        """
        
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            result_text = chat_completion.choices[0].message.content.strip()
            result_text = result_text.strip('`').strip()
            if result_text.lower().startswith("json"):
                result_text = result_text[4:].strip()
                
            data = json.loads(result_text.replace("'", '"'))
            matched_topic = data.get("matched_topic", new_topic).lower()
            
            return matched_topic if matched_topic in existing_topics else new_topic

        except Exception as e:
            print(f"❌ Error matching topic: {e}")
            return new_topic

    async def generate_performance_suggestion(self, performance_data: List[Dict]) -> str:
        """Generate performance analysis and suggestions."""
        data_string = "\n".join([
            f"Topik: {d['topic']}, Kesulitan: {d['difficulty']}, Akurasi: {d['avg_score']:.2f}%, Total Soal: {d['total_questions']}"
            for d in performance_data
        ])
        
        prompt = f"""
        Analisis data performa kuis Anda berikut dan berikan ringkasan dan 3 saran spesifik untuk peningkatan. **Gunakan kata 'Anda' dan nada bicara yang personal dan langsung saat memberikan saran.**

        Data Performa:
        ---
        {data_string}
        ---

        Formatkan respons Anda **HANYA** dalam format Markdown, dimulai dengan heading '## 🎯 Ringkasan & Saran Belajar'.
        """

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Error generating suggestion: {e}")
            return "\n---\n## ⚠️ Analisis Gagal\nGagal mendapatkan saran dari AI. Coba lagi nanti."

    async def answer_study_question(self, topic: str, question: str) -> str:
        """Answer a question during study session."""
        prompt = f"""
        Sebagai asisten belajar, jawablah pertanyaan tentang {topic} ini:

        Pertanyaan: {question}

        Berikan jawaban yang jelas, ringkas, dan akurat yang membantu pemahaman.
        Fokus pada penjelasan konsep dasar dan berikan contoh jika relevan.
        Gunakan Bahasa Indonesia yang baik dan benar.
        """

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return "Maaf, saya mengalami kesulitan dalam menghasilkan jawaban. Silakan coba lagi."

    async def generate_recommendations(self, learning_history: Dict) -> str:
        """Generate personalized study and quiz recommendations."""
        topics_data = learning_history["topics_data"]
        recent_sessions = learning_history["recent_study_sessions"]
        recent_performance = learning_history["recent_performance"]
        
        # Create a detailed prompt for the AI
        topics_summary = []
        for topic, data in topics_data.items():
            summary = (
                f"Topik: {topic}\n"
                f"Performa Kuis: {data['avg_score']:.1f}% dalam {data['quiz_attempts']} percobaan\n"
                f"Sesi Belajar: {data['study_sessions']} sesi, "
                f"Total Waktu Belajar: {data['total_study_time']} menit\n"
                f"Tingkat Kesulitan: {', '.join(data['difficulty_levels'])}"
            )
            topics_summary.append(summary)

        prompt = f"""
        Sebagai asisten AI pendidikan, analisis riwayat belajar ini dan berikan rekomendasi personal:

        STATUS PEMBELAJARAN SAAT INI:
        {'-' * 40}
        {'\\n'.join(topics_summary)}
        
        Aktivitas Terkini:
        - Sesi belajar terakhir: {', '.join(s['topic'] for s in recent_sessions[:3])}
        - Performa kuis terkini: {', '.join(f"{p['topic']} ({p['avg_score']:.1f}%)" for p in recent_performance[:3])}

        Berikan rekomendasi dalam format berikut (dalam Bahasa Indonesia):
        1. Fokus Belajar: Topik mana yang membutuhkan perhatian lebih dan mengapa
        2. Strategi Kuis: Rekomendasi tingkat kesulitan dan topik
        3. Jadwal Belajar: Saran sesi Pomodoro
        4. Alur Pembelajaran: Topik selanjutnya yang perlu dipelajari
        5. Area yang Perlu Direview: Topik yang membutuhkan pengulangan

        Format respons dalam Markdown dengan header dan poin yang sesuai.
        Berikan rekomendasi spesifik untuk nama topik dan waktu belajar.
        Gunakan Bahasa Indonesia yang baik dan benar.
        """

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Error generating recommendations: {e}")
            return "Failed to generate recommendations. Please try again later."

    async def generate_study_summary(self, topic: str, duration_minutes: float, 
                                   completed_intervals: int, questions: List[Dict]) -> str:
        """Generate a summary of the study session with interval details."""
        # Format questions summary
        questions_summary = "\\n".join([
            f"Q: {q['question']}\\nA: {q['answer']}"
            for q in questions[:5]  # Limit to 5 questions for summary
        ])

        # Calculate completion percentage
        completion_percentage = (completed_intervals / (completed_intervals + 1)) * 100 if completed_intervals > 0 else 0

        prompt = f"""
        Buatlah ringkasan sesi belajar berikut dalam Bahasa Indonesia:

        Topik: {topic}
        Total Durasi: {int(duration_minutes)} menit
        Progress: {completed_intervals} interval selesai ({completion_percentage:.1f}% dari rencana)

        Pertanyaan yang Dibahas:
        {questions_summary}

        Berikan ringkasan yang mencakup:
        1. Konsep utama yang dipelajari (berdasarkan pertanyaan)
        2. Evaluasi kemajuan belajar
        3. Satu rekomendasi spesifik untuk sesi berikutnya

        Format dalam Markdown dan gunakan bahasa yang jelas dan mudah dipahami.
        """

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return "Failed to generate study session summary."

    async def generate_study_plan(self, prompt: str) -> Dict:
        """Generate a study plan based on user's natural language prompt."""
        ai_prompt = f"""
        Sebagai asisten belajar, buatkan rencana belajar berdasarkan input pengguna berikut:

        Input Pengguna: {prompt}

        Analisis input tersebut dan buat rencana belajar yang efektif dengan format JSON berikut:
        {{
            "topic": "topik yang akan dipelajari",
            "total_duration_minutes": waktu_total_dalam_menit,
            "sessions": [
                {{
                    "duration": durasi_sesi_dalam_menit,
                    "break": durasi_istirahat_dalam_menit,
                    "focus": "fokus pembelajaran untuk sesi ini"
                }},
                ...
            ],
            "description": "deskripsi rencana belajar dalam bahasa Indonesia"
        }}

        Aturan pembuatan rencana:
        1. Sesi belajar maksimal 50 menit
        2. Istirahat minimal 5 menit, maksimal 15 menit
        3. Setiap sesi harus memiliki fokus spesifik
        4. Total durasi harus sesuai dengan waktu yang tersedia
        5. Berikan deskripsi yang detail dan memotivasi
        """

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": ai_prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            result = json.loads(chat_completion.choices[0].message.content.strip())
            
            # Validate plan format
            if not all(key in result for key in ["topic", "total_duration_minutes", "sessions", "description"]):
                raise ValueError("Format rencana tidak lengkap")
                
            return result

        except Exception as e:
            print(f"❌ Error generating study plan: {e}")
            return None

    @staticmethod
    def normalize_question(q: Dict) -> Dict:
        """Normalize question structure."""
        normalized = {
            "question": q.get("question") or q.get("pertanyaan") or q.get("soal") or "Pertanyaan tidak tersedia.",
            "options": q.get("options") or q.get("pilihan") or q.get("choices") or [],
            "answer": q.get("answer") or q.get("jawaban") or "A",
            "explanation": q.get("explanation") or q.get("penjelasan") or "",
        }
        if not isinstance(normalized["options"], list) or len(normalized["options"]) == 0:
            normalized["options"] = ["Tidak ada opsi A", "Tidak ada opsi B", "Tidak ada opsi C", "Tidak ada opsi D"]
        return normalized

ai_service = AIService()