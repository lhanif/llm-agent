"""Unit tests for the quiz management module."""

import pytest
from datetime import datetime, timedelta
from quiz_bot.quiz_manager import QuizManager, QuizSession

class TestQuizSession:
    """Test suite for QuizSession class."""

    @pytest.fixture
    def quiz_questions(self):
        """Create sample quiz questions."""
        return [
            {
                "question": "What is Python?",
                "options": ["A snake", "A programming language", "A game", "A book"],
                "answer": "B",
                "explanation": "Python is a programming language"
            },
            {
                "question": "Which is valid Python syntax?",
                "options": ["print 'Hello'", "print('Hello')", "printf('Hello')", "cout << 'Hello'"],
                "answer": "B",
                "explanation": "print() is the correct syntax in Python 3"
            }
        ]

    @pytest.fixture
    def quiz_session(self, quiz_questions):
        """Create a quiz session for testing."""
        quiz_question_ids = ["q1", "q2"]
        return QuizSession(
            user_id="123",
            session_id="quiz_123",
            questions=quiz_questions,
            quiz_question_ids=quiz_question_ids,
            topic="Python Basics",
            difficulty="sedang"
        )

    def test_quiz_session_initialization(self, quiz_session):
        """Test quiz session initialization."""
        assert quiz_session.user_id == "123"
        assert quiz_session.session_id == "quiz_123"
        assert len(quiz_session.questions) == 2
        assert quiz_session.topic == "Python Basics"
        assert quiz_session.difficulty == "sedang"
        assert quiz_session.current == 0
        assert quiz_session.score == 0

    def test_get_current_question(self, quiz_session):
        """Test getting current question."""
        # Get first question
        question = quiz_session.get_current_question()
        assert question["question"] == "What is Python?"
        
        # Move to next question
        quiz_session.move_to_next_question()
        question = quiz_session.get_current_question()
        assert question["question"] == "Which is valid Python syntax?"
        
        # Move past last question
        quiz_session.move_to_next_question()
        assert quiz_session.get_current_question() is None

    def test_get_current_question_id(self, quiz_session):
        """Test getting current question ID."""
        assert quiz_session.get_current_question_id() == "q1"
        
        quiz_session.move_to_next_question()
        assert quiz_session.get_current_question_id() == "q2"
        
        quiz_session.move_to_next_question()
        assert quiz_session.get_current_question_id() is None

    def test_check_answer(self, quiz_session):
        """Test answer checking."""
        # Test correct answer
        assert quiz_session.check_answer("B") is True
        
        # Test wrong answer
        assert quiz_session.check_answer("A") is False
        
        # Test case insensitivity
        assert quiz_session.check_answer("b") is True


    def test_move_to_next_question(self, quiz_session):
        """Test moving to next question."""
        assert quiz_session.current == 0
        
        quiz_session.move_to_next_question()
        assert quiz_session.current == 1
        
        quiz_session.move_to_next_question()
        assert quiz_session.current == 2

    def test_is_finished(self, quiz_session):
        """Test quiz completion check."""
        assert quiz_session.is_finished() is False
        
        quiz_session.move_to_next_question()
        assert quiz_session.is_finished() is False
        
        quiz_session.move_to_next_question()
        assert quiz_session.is_finished() is True


class TestQuizManager:
    """Test suite for QuizManager class."""

    @pytest.fixture
    def quiz_manager(self):
        """Create a quiz manager for testing."""
        return QuizManager()

    @pytest.fixture
    def quiz_questions(self):
        """Create sample quiz questions."""
        return [
            {
                "question": "What is Python?",
                "options": ["A snake", "A programming language", "A game", "A book"],
                "answer": "B",
                "explanation": "Python is a programming language"
            }
        ]

    def test_create_session(self, quiz_manager, quiz_questions):
        """Test creating a new quiz session."""
        # Act
        session = quiz_manager.create_session(
            user_id="123",
            questions=quiz_questions,
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1"]
        )
        
        # Assert
        assert session.user_id == "123"
        assert session.questions == quiz_questions
        assert session.topic == "Python"
        assert session.difficulty == "sedang"
        assert "123" in quiz_manager.active_sessions

    def test_get_session(self, quiz_manager, quiz_questions):
        """Test getting an active quiz session."""
        # Arrange
        session = quiz_manager.create_session(
            user_id="123",
            questions=quiz_questions,
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1"]
        )
        
        # Act & Assert
        assert quiz_manager.get_session("123") == session
        assert quiz_manager.get_session("456") is None

    def test_end_session(self, quiz_manager, quiz_questions):
        """Test ending a quiz session."""
        # Arrange
        quiz_manager.create_session(
            user_id="123",
            questions=quiz_questions,
            topic="Python",
            difficulty="sedang",
            quiz_question_ids=["q1"]
        )
        
        # Act
        quiz_manager.end_session("123")
        
        # Assert
        assert "123" not in quiz_manager.active_sessions