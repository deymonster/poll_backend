from db.base_class import Base
from enum import Enum
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON, event, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy import func


class TypeQuestion(str, Enum):
    SINGLE = "SINGLE ANSWER"
    PLURAL = "PLURAL ANSWER"
    FREE = "FREE ANSWER"  # multiple text fields for answer
    FREE_TEXT = "FREE TEXT ANSWER"  # one text field for answer


class PollStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    # CLOSED = "CLOSED"
    ENDED = "ENDED"
    ARCHIVED = "ARCHIVED"


class Poll(Base):
    """Model poll"""

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=func.now(), comment="Дата создания")
    title = Column(String, index=True)
    description = Column(String, index=True)
    poll_cover = Column(String, nullable=True)
    poll_status = Column(ENUM(PollStatus), default=PollStatus.DRAFT)
    poll_url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="polls")
    question = relationship("Question", back_populates="poll", cascade="all, delete-orphan")
    response = relationship("Response", back_populates="poll", cascade="all, delete-orphan")

    active_from = Column(DateTime, nullable=True)
    active_duration = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)

    def is_published(self):
        if self.poll_status == PollStatus.PUBLISHED:
            return True
        else:
            return None

    def is_ended(self):
        if self.poll_status == PollStatus.ENDED:
            return True
        else:
            return None

#
# @event.listens_for(Poll, "before_update")
# def before_update(mapper, connection, target):
#     if target.poll_status == PollStatus.PUBLISHED and not target.active_from:
#         now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
#         target.active_from = now_utc + timedelta(hours=5)


class Question(Base):
    """Model question"""

    id = Column(Integer, primary_key=True, index=True)
    type = Column(ENUM(TypeQuestion), nullable=False, index=True)
    text = Column(String, index=True)
    question_cover = Column(String, nullable=True)
    option_pass = Column(Boolean, default=False)
    option_other_answer = Column(Boolean, default=False)
    poll_id = Column(Integer, ForeignKey("poll.id"))
    order = Column(Integer, default=10, index=True)
    poll = relationship("Poll", back_populates="question")
    choice = relationship("Choice", back_populates="question", cascade="all, delete-orphan")
    response = relationship("Response", back_populates="question", cascade="all, delete-orphan")


# Model choice
class Choice(Base):
    """Model choice"""

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    choice_cover = Column(String, nullable=True)
    text_fields_count = Column(Integer, nullable=True)
    question_id = Column(Integer, ForeignKey("question.id", ondelete="CASCADE"))
    question = relationship("Question", back_populates="choice")


# Model Response
class Response(Base):
    """Model response"""

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    poll_id = Column(Integer, ForeignKey("poll.id", ondelete="CASCADE"))
    poll = relationship("Poll", back_populates="response")
    question_id = Column(Integer, ForeignKey("question.id", ondelete="CASCADE"))
    question = relationship("Question", back_populates="response")

    answer_text = Column(JSON, nullable=True)
    answer_choice = Column(JSON, nullable=True)

    user_token = Column(String, nullable=False, index=True)



