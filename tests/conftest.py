"""Common test fixtures and configurations for all tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from quiz_bot.ai_service import AIService
from quiz_bot.study_manager import StudySessionManager
from quiz_bot.quiz_manager import QuizManager

@pytest.fixture
def mock_groq_client():
    """Mock the Groq client."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client

@pytest.fixture
def mock_ai_service(mock_groq_client):
    """Create a mocked AI service."""
    ai_service = AIService()
    ai_service.groq_client = mock_groq_client
    return ai_service

@pytest.fixture
def mock_discord_channel():
    """Create a mocked Discord channel."""
    channel = AsyncMock()
    channel.send = AsyncMock()
    return channel

@pytest.fixture
def sample_quiz_questions():
    """Return sample quiz questions for testing."""
    return [
        {
            "question": "What is the capital of France?",
            "options": ["London", "Berlin", "Paris", "Madrid"],
            "answer": "C",
            "explanation": "Paris is the capital of France."
        },
        {
            "question": "Which planet is closest to the Sun?",
            "options": ["Venus", "Mercury", "Mars", "Earth"],
            "answer": "B",
            "explanation": "Mercury is the closest planet to the Sun."
        }
    ]

@pytest.fixture
def sample_study_plan():
    """Return a sample study plan for testing."""
    return {
        "topic": "Python Programming",
        "total_duration_minutes": 120,
        "sessions": [
            {
                "duration": 45,
                "break": 10,
                "focus": "Basic Syntax"
            },
            {
                "duration": 45,
                "break": 15,
                "focus": "Functions and Classes"
            }
        ],
        "description": "Comprehensive Python programming study session"
    }

@pytest.fixture
def sample_learning_history():
    """Return sample learning history data for testing."""
    return {
        "topics_data": {
            "Python Programming": {
                "avg_score": 85.5,
                "quiz_attempts": 5,
                "study_sessions": 3,
                "total_study_time": 180,
                "difficulty_levels": ["mudah", "sedang"]
            },
            "Data Structures": {
                "avg_score": 75.0,
                "quiz_attempts": 3,
                "study_sessions": 2,
                "total_study_time": 120,
                "difficulty_levels": ["sedang"]
            }
        },
        "recent_study_sessions": [
            {"topic": "Python Programming"},
            {"topic": "Data Structures"}
        ],
        "recent_performance": [
            {"topic": "Python Programming", "avg_score": 85.5},
            {"topic": "Data Structures", "avg_score": 75.0}
        ]
    }