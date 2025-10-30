import pytest
from unittest.mock import patch, AsyncMock
from quiz_bot.quiz_manager import QuizManager
from quiz_bot.ai_service import AIService

pytestmark = pytest.mark.asyncio

class TestQuizWorkflow:
    """Test suite for quiz workflows."""

    @pytest.fixture
    def mock_quiz_response(self):
        """Mock quiz generation response."""
        return {
            "topic": "Python Basics",
            "difficulty": "sedang",
            "jumlah_soal": 3,
            "questions": [
                {
                    "question": "What is Python?",
                    "options": ["A snake", "A programming language", "A game", "A book"],
                    "answer": "B",
                    "explanation": "Python is a programming language."
                },
                {
                    "question": "Who created Python?",
                    "options": ["Guido van Rossum", "Bill Gates", "Steve Jobs", "Mark Zuckerberg"],
                    "answer": "A",
                    "explanation": "Python was created by Guido van Rossum."
                },
                {
                    "question": "Which is valid Python syntax?",
                    "options": ["print 'Hello'", "print('Hello')", "printf('Hello')", "cout << 'Hello'"],
                    "answer": "B",
                    "explanation": "print() is the correct syntax in Python 3."
                }
            ]
        }

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service to avoid real API calls."""
        with patch.object(AIService, 'generate_soal', return_value=(
            "Python Basics", "sedang", 3, [
                {"question": "What is Python?", "options": ["A snake", "A programming language", "A game", "A book"], "answer": "B", "explanation": "Python is a programming language."},
                {"question": "Who created Python?", "options": ["Guido van Rossum", "Bill Gates", "Steve Jobs", "Mark Zuckerberg"], "answer": "A", "explanation": "Python was created by Guido van Rossum."},
                {"question": "Which is valid Python syntax?", "options": ["print 'Hello'", "print('Hello')", "printf('Hello')", "cout << 'Hello'"], "answer": "B", "explanation": "print() is the correct syntax in Python 3."}
            ])):
            yield AIService()

    async def test_complete_quiz_workflow(self, mock_ai_service, mock_quiz_response):
        """Test a complete quiz workflow."""
        # Arrange
        quiz_manager = QuizManager()
        user_id = "test_user"
        topic = "Python Programming"
        difficulty = "sedang"

        # Act - Create quiz session
        session = quiz_manager.create_session(
            user_id=user_id,
            questions=mock_quiz_response["questions"],
            topic=topic,
            difficulty=difficulty,
            quiz_question_ids=["q1", "q2", "q3"]
        )

        # Simulate taking the quiz
        assert session.get_current_question()["question"] == "What is Python?"
        assert session.check_answer("B") is True
        session.score += 1
        session.move_to_next_question()

        assert session.get_current_question()["question"] == "Who created Python?"
        assert session.check_answer("A") is True
        session.score += 1
        session.move_to_next_question()

        assert session.get_current_question()["question"] == "Which is valid Python syntax?"
        assert session.check_answer("B") is True
        session.score += 1
        session.move_to_next_question()

        # Get final stats
        stats = session.get_final_stats()
        assert stats["score"] == 3
        assert stats["total_questions"] == 3
        assert stats["percentage"] == 100.0

        # End quiz
        quiz_manager.end_session(user_id)
        assert quiz_manager.get_session(user_id) is None

    async def test_quiz_workflow_with_wrong_answers(self, mock_ai_service, mock_quiz_response):
        """Test quiz workflow with incorrect answers."""
        # Arrange
        quiz_manager = QuizManager()
        user_id = "test_user"

        # Act - Create quiz session
        session = quiz_manager.create_session(
            user_id=user_id,
            questions=mock_quiz_response["questions"],
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1", "q2", "q3"]
        )

        # Simulate taking the quiz with wrong answers
        assert session.check_answer("A") is False  # Wrong answer
        session.move_to_next_question()

        assert session.check_answer("B") is False  # Wrong answer
        session.move_to_next_question()

        assert session.check_answer("A") is False  # Wrong answer
        session.move_to_next_question()

        # Get final stats
        stats = session.get_final_stats()
        assert stats["score"] == 0
        assert stats["total_questions"] == 3
        assert stats["percentage"] == 0.0

    async def test_quiz_workflow_with_mixed_results(self, mock_ai_service, mock_quiz_response):
        """Test quiz workflow with mixed correct and incorrect answers."""
        # Arrange
        quiz_manager = QuizManager()
        user_id = "test_user"

        # Act - Create quiz session
        session = quiz_manager.create_session(
            user_id=user_id,
            questions=mock_quiz_response["questions"],
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1", "q2", "q3"]
        )

        # First question - correct
        assert session.check_answer("B") is True
        session.score += 1
        session.move_to_next_question()

        # Second question - wrong
        assert session.check_answer("B") is False
        session.move_to_next_question()

        # Third question - correct
        assert session.check_answer("B") is True
        session.score += 1
        session.move_to_next_question()

        # Get final stats
        stats = session.get_final_stats()
        assert stats["score"] == 2
        assert stats["total_questions"] == 3
        assert stats["percentage"] == (2 / 3) * 100

    async def test_quiz_workflow_edge_cases(self, mock_ai_service):
        """Test quiz workflow edge cases."""
        # Arrange
        quiz_manager = QuizManager()
        user_id = "test_user"

        # Test with empty questions
        session = quiz_manager.create_session(
            user_id=user_id,
            questions=[],
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=[]
        )

        # Verify behavior with empty questions
        assert session.get_current_question() is None
        assert session.is_finished() is True
        
        stats = session.get_final_stats()
        assert stats["score"] == 0
        assert stats["total_questions"] == 0
        assert stats["percentage"] == 0  # Handle division by zero edge case

    async def test_concurrent_quiz_sessions(self, mock_quiz_response):
        """Test handling multiple concurrent quiz sessions."""
        # Arrange
        quiz_manager = QuizManager()

        # Create multiple sessions
        session1 = quiz_manager.create_session(
            user_id="user1",
            questions=mock_quiz_response["questions"],
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1", "q2", "q3"]
        )

        session2 = quiz_manager.create_session(
            user_id="user2",
            questions=mock_quiz_response["questions"],
            topic="Python",
            difficulty="mudah",
            quiz_question_ids=["q1", "q2", "q3"]
        )

        # Verify session isolation
        assert quiz_manager.get_session("user1") == session1
        assert quiz_manager.get_session("user2") == session2

        # Test independent progress tracking
        session1.check_answer("B")
        session1.score += 1
        session1.move_to_next_question()

        session2.check_answer("A")  # Wrong answer
        session2.move_to_next_question()

        # Verify independent scores
        assert session1.score == 1
        assert session2.score == 0

        # End sessions independently
        quiz_manager.end_session("user1")
        assert quiz_manager.get_session("user1") is None
        assert quiz_manager.get_session("user2") is session2

        quiz_manager.end_session("user2")
        assert quiz_manager.get_session("user2") is None
