from supabase import create_client, Client
from typing import Dict, List, Optional
import datetime
from .config import config

from enum import Enum

class StudySessionState(Enum):
    ACTIVE = "active"
    RESTING = "resting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DatabaseManager:
    def __init__(self):
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    def upsert_user(self, user_id: str, username: str) -> None:
        """Create or update user in database."""
        self.supabase.table("users").upsert({"id": user_id, "username": username}).execute()

    def create_quiz_session(self, session_id: str, user_id: str, topic: str, difficulty: str, total_questions: int) -> None:
        """Create a new quiz session."""
        self.supabase.table("quiz_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "topic": topic,
            "difficulty": difficulty,
            "total_questions": total_questions
        }).execute()

    def save_question(self, qid: str, topic: str, difficulty: str, question_text: str, 
                     correct_answer: str, explanation: str) -> None:
        """Save a question to the database."""
        self.supabase.table("questions").insert({
            "id": qid,
            "topic": topic,
            "difficulty": difficulty,
            "question_text": question_text,
            "correct_answer": correct_answer,
            "explanation": explanation
        }).execute()

    def save_quiz_question(self, session_id: str, question_id: str, sequence: int) -> Optional[str]:
        """Save quiz question and return its ID."""
        result = self.supabase.table("quiz_questions").insert({
            "session_id": session_id,
            "question_id": question_id,
            "sequence": sequence
        }).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return None

    def save_answer(self, quiz_question_id: str, user_id: str, user_answer: str, 
                   is_correct: bool, duration_seconds: float) -> None:
        """Save user's answer."""
        self.supabase.table("quiz_answers").insert({
            "quiz_question_id": quiz_question_id,
            "user_id": user_id,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "duration_seconds": duration_seconds
        }).execute()

    def update_performance(self, user_id: str, topic: str, difficulty: str, is_correct: bool) -> None:
        """Update user's performance summary."""
        perf = self.supabase.table("performance_summary").select("*").eq("user_id", user_id).eq("topic", topic).execute()
        
        if perf.data:
            data = perf.data[0]
            total_correct = data["total_correct"] + (1 if is_correct else 0)
            total_questions = data["total_questions"] + 1
            avg_score = total_correct / total_questions * 100
            
            self.supabase.table("performance_summary").update({
                "total_questions": total_questions,
                "total_correct": total_correct,
                "avg_score": avg_score,
                "last_updated": datetime.datetime.now().isoformat()
            }).eq("id", data["id"]).execute()
        else:
            self.supabase.table("performance_summary").insert({
                "user_id": user_id,
                "topic": topic,
                "difficulty": difficulty,
                "total_sessions": 1,
                "total_questions": 1,
                "total_correct": (1 if is_correct else 0),
                "avg_score": (100 if is_correct else 0)
            }).execute()

    def get_performance_summary(self, user_id: str) -> List[Dict]:
        """Get user's performance summary."""
        result = self.supabase.table("performance_summary").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
        
    def get_study_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's recent study sessions with summaries and intervals."""
        query = self.supabase.table("study_sessions")\
            .select(
                """
                *,
                study_summaries(summary),
                study_intervals(
                    id,
                    sequence,
                    duration_minutes,
                    break_duration,
                    focus
                )
                """
            )\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)
        
        result = query.execute()
        
        # Process and structure the data
        if result.data:
            for session in result.data:
                # Convert intervals to sorted list if present
                if "study_intervals" in session:
                    intervals = session["study_intervals"]
                    session["study_intervals"] = sorted(
                        intervals,
                        key=lambda x: x["sequence"]
                    ) if intervals else []
                    
                    # Calculate actual study time from intervals
                    session["actual_duration"] = sum(
                        interval["duration_minutes"]
                        for interval in session["study_intervals"]
                    )
                else:
                    session["study_intervals"] = []
                    session["actual_duration"] = 0
                    
        return result.data if result.data else []

    def get_user_learning_history(self, user_id: str) -> Dict:
        """Get comprehensive user learning history including both quiz performance and study sessions."""
        performance = self.get_performance_summary(user_id)
        study_sessions = self.get_study_history(user_id)
        
        # Aggregate topics and their stats
        topics_data = {}
        
        # Process quiz performance
        for perf in performance:
            topic = perf["topic"]
            if topic not in topics_data:
                topics_data[topic] = {
                    "quiz_attempts": 0,
                    "avg_score": 0,
                    "total_questions": 0,
                    "study_sessions": 0,
                    "total_study_time": 0,
                    "difficulty_levels": set()
                }
            
            data = topics_data[topic]
            data["quiz_attempts"] += 1
            data["avg_score"] = perf["avg_score"]
            data["total_questions"] += perf["total_questions"]
            data["difficulty_levels"].add(perf["difficulty"])
        
            # Process study sessions
            for session in study_sessions:
                topic = session["topic"]
                if topic not in topics_data:
                    topics_data[topic] = {
                        "quiz_attempts": 0,
                        "avg_score": 0,
                        "total_questions": 0,
                        "study_sessions": 0,
                        "total_study_time": 0,
                        "difficulty_levels": set()
                    }
                
                data = topics_data[topic]
                data["study_sessions"] += 1
                data["total_study_time"] += session.get("total_duration", 0)  # Use new total_duration field        # Convert sets to lists for JSON serialization
        for topic_data in topics_data.values():
            topic_data["difficulty_levels"] = list(topic_data["difficulty_levels"])
        
        return {
            "topics_data": topics_data,
            "recent_study_sessions": study_sessions[:5],
            "recent_performance": performance[:5]
        }

    def get_existing_topics(self, difficulty: str) -> List[str]:
        """Get existing topics for a given difficulty level."""
        res = self.supabase.table("performance_summary").select("topic").eq("difficulty", difficulty).execute()
        return list(set([row['topic'] for row in res.data]))

    def create_study_session(self, session_id: str, user_id: str, topic: str, 
                           study_plan: dict) -> None:
        """Create a new study session with intervals."""
        # Create main session
        self.supabase.table("study_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "topic": topic,
            "total_duration": sum(s["duration"] for s in study_plan["sessions"]),
            "state": StudySessionState.ACTIVE.value,
            "start_time": datetime.datetime.now().isoformat(),
            "completed_intervals": 0,
            "current_interval": 0,
            "description": study_plan.get("description", "")
        }).execute()
        
        # Create study intervals
        for i, interval in enumerate(study_plan["sessions"]):
            self.supabase.table("study_intervals").insert({
                "session_id": session_id,
                "sequence": i + 1,
                "duration_minutes": interval["duration"],
                "break_duration": interval["break"],
                "focus": interval["focus"]
            }).execute()

    def update_study_session_state(self, session_id: str, state: StudySessionState, 
                                 completed_intervals: int = None) -> None:
        """Update study session state."""
        data = {"state": state.value}
        if completed_intervals is not None:
            data["completed_intervals"] = completed_intervals
        
        self.supabase.table("study_sessions").update(data).eq("id", session_id).execute()

    def save_study_summary(self, session_id: str, summary: str) -> None:
        """Save study session summary."""
        self.supabase.table("study_summaries").insert({
            "session_id": session_id,
            "summary": summary,
            "created_at": datetime.datetime.now().isoformat()
        }).execute()

    def get_active_study_session(self, user_id: str) -> Optional[Dict]:
        """Get user's active study session if any."""
        res = self.supabase.table("study_sessions").select("*")\
            .eq("user_id", user_id)\
            .in_("state", [StudySessionState.ACTIVE.value, StudySessionState.RESTING.value])\
            .execute()
        return res.data[0] if res.data else None

db = DatabaseManager()