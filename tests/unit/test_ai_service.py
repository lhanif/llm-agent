import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from quiz_bot.ai_service import AIService

pytestmark = pytest.mark.asyncio

class TestAIService:
    """Test suite for AIService class."""

    @pytest.fixture
    def mock_groq_response(self):
        """Create a mock Groq response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "topic": "Python Basics",
                        "difficulty": "sedang",
                        "jumlah_soal": 2,
                        "questions": [
                            {
                                "question": "What is Python?",
                                "options": ["A snake", "A programming language", "A game", "A book"],
                                "answer": "B",
                                "explanation": "Python is a high-level programming language."
                            },
                            {
                                "question": "Who created Python?",
                                "options": ["Guido van Rossum", "Bill Gates", "Steve Jobs", "Mark Zuckerberg"],
                                "answer": "A",
                                "explanation": "Python was created by Guido van Rossum."
                            }
                        ]
                    })
                )
            )
        ]
        return mock_response

    async def test_generate_soal_success(self, mock_groq_response, mock_ai_service, mock_groq_client):
        """Test successful quiz generation."""
        # Arrange
        mock_groq_client.chat.completions.create.return_value = mock_groq_response
        full_prompt = "Buat soal tentang Kalkulus tingkat sedang"

        # Act
        topic, difficulty, num_questions, questions = await mock_ai_service.generate_soal(full_prompt)

        # Assert
        assert difficulty == "sedang"

    async def test_generate_soal_error_handling(self, mock_ai_service, mock_groq_client):
        """Test quiz generation error handling."""
        # Arrange
        mock_groq_client.chat.completions.create.side_effect = Exception("API Error")

        # Act
        topic, difficulty, num_questions, questions = await mock_ai_service.generate_soal("Invalid prompt")

        # Assert
        assert topic == "Topik Umum"
        assert difficulty == "sedang"
        assert num_questions == 0
        assert questions == []

    async def test_match_topic_exact_match(self, mock_ai_service):
        """Test topic matching with exact match."""
        # Arrange
        new_topic = "python programming"
        existing_topics = ["python programming", "data structures"]
        current_difficulty = "sedang"

        # Act
        result = await mock_ai_service.match_topic(new_topic, current_difficulty, existing_topics)

        # Assert
        assert result == "python programming"

    async def test_match_topic_no_match(self, mock_ai_service, mock_groq_client):
        """Test topic matching with no match."""
        # Arrange
        mock_groq_client.chat.completions.create.side_effect = Exception("API Error")
        new_topic = "new topic"
        existing_topics = ["python programming", "data structures"]
        current_difficulty = "sedang"

        # Act
        result = await mock_ai_service.match_topic(new_topic, current_difficulty, existing_topics)

        # Assert
        assert result == "new topic"

    async def test_generate_performance_suggestion(self, mock_ai_service, mock_groq_client):
        """Test performance suggestion generation."""
        # Arrange
        performance_data = [
            {"topic": "Python", "difficulty": "sedang", "avg_score": 85.5, "total_questions": 10},
            {"topic": "Data Structures", "difficulty": "mudah", "avg_score": 75.0, "total_questions": 8}
        ]
        mock_groq_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="## 🎯 Ringkasan & Saran Belajar\nGreat progress!"))
        ]

        # Act
        result = await mock_ai_service.generate_performance_suggestion(performance_data)

    async def test_generate_study_plan_success(self, mock_ai_service, mock_groq_client):
        """Test successful study plan generation."""
        # Arrange
        mock_groq_client.chat.completions.create.return_value.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "topic": "Python Programming",
                        "total_duration_minutes": 120,
                        "sessions": [
                            {"duration": 45, "break": 10, "focus": "Basic Syntax"},
                            {"duration": 45, "break": 15, "focus": "Functions"}
                        ],
                        "description": "Comprehensive study plan"
                    })
                )
            )
        ]

        # Act
        result = await mock_ai_service.generate_study_plan("I want to learn Python for 2 hours")

    async def test_normalize_question(self, mock_ai_service):
        """Test question normalization."""
        # Arrange
        raw_question = {
            "pertanyaan": "What is Python?",
            "pilihan": ["A snake", "A language", "A game", "A book"],
            "jawaban": "B",
            "penjelasan": "Python is a programming language"
        }

        # Act
        normalized = AIService.normalize_question(raw_question)

        # Assert
        assert normalized["question"] == "What is Python?"
        assert len(normalized["options"]) == 4
        assert normalized["answer"] == "B"
        assert normalized["explanation"] == "Python is a programming language"

    async def test_normalize_question_missing_fields(self, mock_ai_service):
        """Test question normalization with missing fields."""
        # Arrange
        raw_question = {
            "pertanyaan": "What is Python?"
        }

        # Act
        normalized = AIService.normalize_question(raw_question)

        # Assert
        assert normalized["question"] == "What is Python?"
        assert len(normalized["options"]) == 4
        assert normalized["answer"] == "A"
        assert normalized["explanation"] == ""
