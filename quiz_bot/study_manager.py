import asyncio
import discord
from typing import Dict, Optional
import datetime
import uuid
from enum import Enum
from .database import db, StudySessionState
from .ai_service import ai_service

from .utils import split_into_chunks

class StudySession:
    def __init__(self, user_id: str, session_id: str, topic: str, 
                 intervals: list, channel: discord.TextChannel, focus: str = None):
        self.user_id = user_id
        self.session_id = session_id
        self.topic = topic
        self.intervals = intervals  # List of {duration, break} dictionaries
        self.current_interval = 0  # This will track both current and completed intervals
        self.channel = channel
        self.state = StudySessionState.ACTIVE
        self.focus = focus
        self.study_timer = None
        self.break_timer = None
        self.questions = []
        self.start_time = datetime.datetime.now()

    @property
    def total_intervals(self) -> int:
        """Get total number of intervals in the session."""
        return len(self.intervals)

    async def start_study_interval(self):
        """Start a study interval."""
        if self.current_interval >= len(self.intervals):
            await self.end_session()
            return

        interval = self.intervals[self.current_interval]
        self.state = StudySessionState.ACTIVE
        db.update_study_session_state(self.session_id, self.state)
        
        await self.channel.send(
            f"📚 **Study Interval {self.current_interval + 1} Started**\n"
            f"Topic: **{self.topic}**\n"
            f"Fokus: **{interval.get('focus', 'General study')}**\n"
            f"Durasi: **{interval['duration']}** menit\n\n"
            f"Anda dapat mengajukan pertanyaan tentang topik ini selama sesi belajar!"
        )

        # Start the timer
        self.study_timer = asyncio.create_task(self._study_timer())

    async def _study_timer(self):
        """Internal timer for study interval."""
        try:
            interval = self.intervals[self.current_interval]
            await asyncio.sleep(interval['duration'] * 60)
            db.update_study_session_state(self.session_id, self.state, self.current_interval)
            
            # Start break if not the last interval
            if self.current_interval < len(self.intervals):
                await self.start_break()
        except asyncio.CancelledError:
            pass

    async def start_break(self):
        """Start a break interval."""
        interval = self.intervals[self.current_interval]
        self.state = StudySessionState.RESTING
        db.update_study_session_state(self.session_id, self.state)
        
        await self.channel.send(
            f"☕ **Break Time!**\n"
            f"Istirahat selama **{interval['break']}** menit.\n"
            f"Pertanyaan akan dijeda selama istirahat."
        )

        # Start the break timer
        self.break_timer = asyncio.create_task(self._break_timer())

    async def _break_timer(self):
        """Internal timer for break interval."""
        try:
            interval = self.intervals[self.current_interval]
            await asyncio.sleep(interval['break'] * 60)
            
            # Move to next interval
            self.current_interval += 1
            
            # Start next study interval or end session if done
            if self.current_interval < len(self.intervals):
                await self.start_study_interval()
            else:
                await self.end_session()
        except asyncio.CancelledError:
            pass

    async def end_session(self):
        """End the study session."""
        if self.study_timer:
            self.study_timer.cancel()
        if self.break_timer:
            self.break_timer.cancel()

        self.state = StudySessionState.COMPLETED
        db.update_study_session_state(self.session_id, self.state)

        # Generate and save summary
        duration = (datetime.datetime.now() - self.start_time).total_seconds() / 60
        summary = await ai_service.generate_study_summary(
            self.topic, 
            duration, 
            self.current_interval,  # Use current_interval instead of completed_intervals
            self.questions
        )
        db.save_study_summary(self.session_id, summary)

        content = (
            f"🎉 **Study Session Completed!**\n"
            f"Topic: **{self.topic}**\n"
            f"Completed Intervals: **{self.current_interval}**\n"
            f"Total Duration: **{int(duration)}** minutes\n\n"
            f"**Session Summary:**\n{summary}"
        )
        
        # Split and send long messages
        if len(content) > 2000:
            chunks = self.utils.split_into_chunks(content)
            for chunk in chunks:
                await self.channel.send(chunk)

    def can_ask_questions(self) -> bool:
        """Check if questions can be asked in current state."""
        return self.state == StudySessionState.ACTIVE

    def add_question(self, question: str, answer: str):
        """Add a question to the session history."""
        self.questions.append({"question": question, "answer": answer, "timestamp": datetime.datetime.now().isoformat()})

class StudySessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, StudySession] = {}

    def create_session(self, user_id: str, topic: str, study_plan: dict, 
                      channel: discord.TextChannel) -> StudySession:
        """Create a new study session with multiple intervals."""
        if user_id in self.active_sessions:
            raise ValueError("User already has an active study session")

        session_id = str(uuid.uuid4())
        
        # Create intervals list from study plan
        intervals = [
            {
                "duration": session["duration"],
                "break": session["break"],
                "focus": session["focus"]
            }
            for session in study_plan["sessions"]
        ]
        
        session = StudySession(user_id, session_id, topic, intervals, channel)
        self.active_sessions[user_id] = session
        
        # Save to database
        db.create_study_session(session_id, user_id, topic, study_plan)
        
        return session

    def get_session(self, user_id: str) -> Optional[StudySession]:
        """Get an active study session for a user."""
        return self.active_sessions.get(user_id)

    def end_session(self, user_id: str) -> None:
        """End a study session."""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

study_manager = StudySessionManager()