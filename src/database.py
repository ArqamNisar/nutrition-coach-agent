from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional, List
from datetime import datetime
from src.config import DATABASE_URL
from src.models import UserProfile, FoodLog, ChatMessage

# Create database engine
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    SQLModel.metadata.create_all(engine)

def get_user_profile(user_id: int = 1) -> Optional[UserProfile]:
    """Retrieves the user profile from the database."""
    with Session(engine) as session:
        statement = select(UserProfile).where(UserProfile.id == user_id)
        results = session.exec(statement)
        return results.first()

def save_user_profile(profile: UserProfile) -> UserProfile:
    """Saves or updates the user profile."""
    with Session(engine) as session:
        db_profile = session.get(UserProfile, profile.id)
        if db_profile:
            # Update fields
            for key, value in profile.model_dump().items():
                if key != "id":
                    setattr(db_profile, key, value)
            db_profile.updated_at = datetime.now()
            session.add(db_profile)
            session.commit()
            session.refresh(db_profile)
            return db_profile
        else:
            # Insert new
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile

def log_food(food_item: FoodLog) -> FoodLog:
    """Logs a food item to the database."""
    with Session(engine) as session:
        session.add(food_item)
        session.commit()
        session.refresh(food_item)
        return food_item

def get_food_logs(limit: int = 100) -> List[FoodLog]:
    """Retrieves list of food logs sorted by timestamp descending."""
    with Session(engine) as session:
        statement = select(FoodLog).order_by(FoodLog.timestamp.desc()).limit(limit)
        return list(session.exec(statement).all())

def get_todays_food_logs() -> List[FoodLog]:
    """Retrieves food logs for today (from midnight onwards)."""
    with Session(engine) as session:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        statement = select(FoodLog).where(FoodLog.timestamp >= today_start).order_by(FoodLog.timestamp.desc())
        return list(session.exec(statement).all())

def delete_food_log(log_id: int) -> bool:
    """Deletes a food log entry."""
    with Session(engine) as session:
        log = session.get(FoodLog, log_id)
        if log:
            session.delete(log)
            session.commit()
            return True
        return False

def save_chat_message(message: ChatMessage) -> ChatMessage:
    """Saves a chatbot message to history."""
    with Session(engine) as session:
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

def get_chat_history(limit: int = 50) -> List[ChatMessage]:
    """Retrieves chat message history."""
    with Session(engine) as session:
        statement = select(ChatMessage).order_by(ChatMessage.timestamp.asc()).limit(limit)
        return list(session.exec(statement).all())

def clear_chat_history():
    """Deletes all messages in chat history."""
    with Session(engine) as session:
        session.query(ChatMessage).delete()
        session.commit()
