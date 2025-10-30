from typing import Dict, List, Optional
import datetime
import uuid

class QuizSession:
    def __init__(self, user_id: str, session_id: str, questions: List[Dict], 
                 quiz_question_ids: List[str], topic: str, difficulty: str):
        self.user_id = user_id
        self.session_id = session_id
        self.questions = questions
        self.quiz_question_ids = quiz_question_ids
        self.topic = topic
        self.difficulty = difficulty
        self.current = 0
        self.score = 0
        self.start_time = datetime.datetime.now()
        self.question_start_time = datetime.datetime.now()

    def get_current_question(self) -> Optional[Dict]:
        """Get the current question."""
        if self.current < len(self.questions):
            return self.questions[self.current]
        return None

    def get_current_question_id(self) -> Optional[str]:
        """Get the current question ID."""
        if self.current < len(self.quiz_question_ids):
            return self.quiz_question_ids[self.current]
        return None

    def check_answer(self, answer: str) -> bool:
        """Check if the answer is correct."""
        current_q = self.get_current_question()
        if current_q:
            return answer.upper() == current_q["answer"].upper()
        return False

    def get_answer_duration(self) -> float:
        """Get the duration taken to answer the current question."""
        return (datetime.datetime.now() - self.question_start_time).total_seconds()

    def move_to_next_question(self) -> None:
        """Move to the next question."""
        self.current += 1
        self.question_start_time = datetime.datetime.now()

    def is_finished(self) -> bool:
        """Check if the quiz is finished."""
        return self.current >= len(self.questions)

    def get_final_stats(self) -> Dict:
        """Get final quiz statistics."""
        end_time = datetime.datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        if len(self.questions) == 0:
            percentage_score = 0
            avg_duration_per_q = 0
        else:
            percentage_score = (self.score / len(self.questions)) * 100
            avg_duration_per_q = total_duration / len(self.questions)
        
        return {
            "score": self.score,
            "total_questions": len(self.questions),
            "percentage": percentage_score,
            "total_duration": str(datetime.timedelta(seconds=round(total_duration))),
            "avg_duration_per_q": avg_duration_per_q
        }

class QuizManager:
    def __init__(self):
        self.active_sessions: Dict[str, QuizSession] = {}

    def create_session(self, user_id: str, questions: List[Dict], topic: str, 
                      difficulty: str, quiz_question_ids: List[str]) -> QuizSession:
        """Create a new quiz session."""
        session_id = str(uuid.uuid4())
        session = QuizSession(user_id, session_id, questions, quiz_question_ids, topic, difficulty)
        self.active_sessions[user_id] = session
        return session

    def get_session(self, user_id: str) -> Optional[QuizSession]:
        """Get an active quiz session for a user."""
        return self.active_sessions.get(user_id)

    def end_session(self, user_id: str) -> None:
        """End a quiz session."""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

quiz_manager = QuizManager()