import pytest
from unittest.mock import patch, AsyncMock
from quiz_bot.study_manager import StudySessionManager, StudySessionState
from quiz_bot.ai_service import AIService

pytestmark = pytest.mark.asyncio

class TestStudyWorkflow:
    """Test suite for study session workflows."""

    @pytest.fixture
    def mock_ai_responses(self):
        """Mock AI service responses."""
        return {
            "study_plan": {
                "topic": "Python Programming",
                "total_duration_minutes": 120,
                "sessions": [
                    {"duration": 45, "break": 10, "focus": "Basic Syntax"},
                    {"duration": 45, "break": 15, "focus": "Functions"}
                ],
                "description": "Comprehensive study plan"
            },
            "study_summary": "Great progress in understanding Python basics!",
            "answer_response": "Python is a high-level programming language."
        }

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service to avoid real API calls."""
        with patch.object(AIService, 'generate_study_plan', return_value=None) as mock_gen_plan, \
             patch.object(AIService, 'generate_study_summary', return_value=None) as mock_gen_summary, \
             patch.object(AIService, 'answer_study_question', return_value=None) as mock_answer:
            yield {
                'generate_study_plan': mock_gen_plan,
                'generate_study_summary': mock_gen_summary,
                'answer_study_question': mock_answer
            }

    async def test_complete_study_workflow(self, mock_discord_channel, mock_ai_service, mock_ai_responses):
        """Test a complete study session workflow."""
        # Arrange
        study_manager = StudySessionManager()
        user_id = "test_user"
        topic = "Python Programming"

        # Mock AI service responses
        mock_ai_service['generate_study_plan'].return_value = mock_ai_responses["study_plan"]
        mock_ai_service['generate_study_summary'].return_value = mock_ai_responses["study_summary"]
        mock_ai_service['answer_study_question'].return_value = mock_ai_responses["answer_response"]

        # Act - Create and start study session
        with patch('quiz_bot.study_manager.db'):
            session = study_manager.create_session(
                user_id=user_id,
                topic=topic,
                study_plan=mock_ai_responses["study_plan"],
                channel=mock_discord_channel
            )

            # Start first interval
            await session.start_study_interval()
            assert session.state == StudySessionState.ACTIVE
            assert session.current_interval == 0

            # Simulate asking a question during study
            assert session.can_ask_questions() is True
            session.add_question(
                "What is Python?",
                mock_ai_responses["answer_response"]
            )

            # Start break
            await session.start_break()
            assert session.state == StudySessionState.RESTING

            # Move to second interval
            await session.start_study_interval()
            assert session.state == StudySessionState.ACTIVE
            assert session.current_interval == 0

            # End session
            await session.end_session()
            assert session.state == StudySessionState.COMPLETED

            # Verify final state
            assert session.questions[0]["question"] == "What is Python?"
            assert session.questions[0]["answer"] == mock_ai_responses["answer_response"]
            mock_discord_channel.send.assert_called()

    async def test_concurrent_study_sessions(self, mock_discord_channel):
        """Test handling multiple concurrent study sessions."""
        # Arrange
        study_manager = StudySessionManager()
        study_plan = {
            "topic": "Python",
            "total_duration_minutes": 60,
            "sessions": [
                {"duration": 25, "break": 5, "focus": "Concurrency"}
            ],
            "description": "Test concurrent sessions"
        }

        # Act & Assert
        with patch('quiz_bot.study_manager.db'):
            # Create first session
            session1 = study_manager.create_session(
                user_id="user1",
                topic="Python",
                study_plan=study_plan,
                channel=mock_discord_channel
            )

            # Create second session
            session2 = study_manager.create_session(
                user_id="user2",
                topic="JavaScript",
                study_plan=study_plan,
                channel=mock_discord_channel
            )

            # Verify both sessions are independent
            assert study_manager.get_session("user1") == session1
            assert study_manager.get_session("user2") == session2
            assert session1.user_id != session2.user_id

            # Test session isolation
            session1.add_question("Python Q?", "Python A")
            session2.add_question("JS Q?", "JS A")

            assert len(session1.questions) == 1
            assert len(session2.questions) == 1
            assert session1.questions[0]["question"] == "Python Q?"
            assert session2.questions[0]["question"] == "JS Q?"

    async def test_study_session_state_transitions(self, mock_discord_channel):
        """Test study session state transitions."""
        # Arrange
        study_manager = StudySessionManager()
        study_plan = {
            "topic": "State Transitions",
            "total_duration_minutes": 60,
            "sessions": [
                {"duration": 25, "break": 5, "focus": "States"}
            ],
            "description": "Test state transitions"
        }

        with patch('quiz_bot.study_manager.db'):
            # Create session
            session = study_manager.create_session(
                user_id="user1",
                topic="States",
                study_plan=study_plan,
                channel=mock_discord_channel
            )

            # Test initial state
            assert session.state == StudySessionState.ACTIVE
            assert session.can_ask_questions() is True

            # Test transition to break
            await session.start_break()
            assert session.state == StudySessionState.RESTING
            assert session.can_ask_questions() is False

            # Test transition back to active
            await session.start_study_interval()
            assert session.state == StudySessionState.ACTIVE
            assert session.can_ask_questions() is True

            # Test transition to completed
            await session.end_session()
            assert session.state == StudySessionState.COMPLETED
            assert session.can_ask_questions() is False
