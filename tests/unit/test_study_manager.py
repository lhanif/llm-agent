"""Unit tests for the study session management module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from quiz_bot.study_manager import StudySession, StudySessionManager, StudySessionState

pytestmark = pytest.mark.asyncio

class TestStudySession:
    """Test suite for StudySession class."""

    @pytest.fixture
    def study_session(self, mock_discord_channel):
        """Create a study session for testing."""
        intervals = [
            {"duration": 25, "break": 5, "focus": "Basic Concepts"},
            {"duration": 25, "break": 5, "focus": "Advanced Topics"}
        ]
        return StudySession(
            user_id="123",
            session_id="session_123",
            topic="Python",
            intervals=intervals,
            channel=mock_discord_channel
        )

    async def test_study_session_initialization(self, study_session):
        """Test study session initialization."""
        # Assert
        assert study_session.user_id == "123"
        assert study_session.session_id == "session_123"
        assert study_session.topic == "Python"
        assert len(study_session.intervals) == 2
        assert study_session.current_interval == 0
        assert study_session.state == StudySessionState.ACTIVE
        assert study_session.questions == []

    async def test_total_intervals(self, study_session):
        """Test total intervals calculation."""
        assert study_session.total_intervals == 2

    @patch('quiz_bot.study_manager.db')
    async def test_start_study_interval(self, mock_db, study_session, mock_discord_channel):
        """Test starting a study interval."""
        # Act
        await study_session.start_study_interval()

        # Assert
        mock_discord_channel.send.assert_called_once()
        assert "Study Interval 1 Started" in mock_discord_channel.send.call_args[0][0]
        assert study_session.state == StudySessionState.ACTIVE
        mock_db.update_study_session_state.assert_called_once_with(
            study_session.session_id, 
            StudySessionState.ACTIVE
        )

    @patch('quiz_bot.study_manager.db')
    async def test_start_break(self, mock_db, study_session, mock_discord_channel):
        """Test starting a break interval."""
        # Act
        await study_session.start_break()

        # Assert
        mock_discord_channel.send.assert_called_once()
        assert "Break Time!" in mock_discord_channel.send.call_args[0][0]
        assert study_session.state == StudySessionState.RESTING
        mock_db.update_study_session_state.assert_called_once_with(
            study_session.session_id, 
            StudySessionState.RESTING
        )

    def test_can_ask_questions(self, study_session):
        """Test checking if questions can be asked."""
        # Test when active
        assert study_session.can_ask_questions() is True

        # Test when resting
        study_session.state = StudySessionState.RESTING
        assert study_session.can_ask_questions() is False

    def test_add_question(self, study_session):
        """Test adding a question to session history."""
        # Act
        study_session.add_question("What is Python?", "A programming language")

        # Assert
        assert len(study_session.questions) == 1
        assert study_session.questions[0]["question"] == "What is Python?"
        assert study_session.questions[0]["answer"] == "A programming language"


class TestStudySessionManager:
    """Test suite for StudySessionManager class."""

    @pytest.fixture
    def study_manager(self):
        """Create a study session manager for testing."""
        return StudySessionManager()

    @pytest.fixture
    def study_plan(self):
        """Create a sample study plan for testing."""
        return {
            "topic": "Python Programming",
            "total_duration_minutes": 120,
            "sessions": [
                {"duration": 45, "break": 10, "focus": "Basic Syntax"},
                {"duration": 45, "break": 15, "focus": "Functions"}
            ],
            "description": "Comprehensive study plan"
        }

    @patch('quiz_bot.study_manager.db')
    def test_create_session(self, mock_db, study_manager, study_plan, mock_discord_channel):
        """Test creating a new study session."""
        # Act
        session = study_manager.create_session(
            user_id="123",
            topic="Python",
            study_plan=study_plan,
            channel=mock_discord_channel
        )

        # Assert
        assert session.user_id == "123"
        assert session.topic == "Python"
        assert len(session.intervals) == 2
        assert "123" in study_manager.active_sessions
        mock_db.create_study_session.assert_called_once()

    @patch('quiz_bot.study_manager.db')
    def test_create_session_existing_user(self, mock_db, study_manager, study_plan, mock_discord_channel):
        """Test creating a session for user with existing session."""
        # Arrange
        study_manager.active_sessions["123"] = "existing_session"

        # Act & Assert
        with pytest.raises(ValueError, match="User already has an active study session"):
            study_manager.create_session(
                user_id="123",
                topic="Python",
                study_plan=study_plan,
                channel=mock_discord_channel
            )

    def test_get_session(self, study_manager, study_plan, mock_discord_channel):
        """Test getting an active session."""
        # Arrange
        session = study_manager.create_session(
            user_id="123",
            topic="Python",
            study_plan=study_plan,
            channel=mock_discord_channel
        )

        # Act & Assert
        assert study_manager.get_session("123") == session
        assert study_manager.get_session("456") is None