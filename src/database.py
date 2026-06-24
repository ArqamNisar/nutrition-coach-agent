from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional, List
from datetime import datetime
from src.config import DATABASE_URL
from src.models import UserProfile, FoodLog, ChatMessage
from src.logger import get_logger

logger = get_logger(__name__)

# Create database engine
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    logger.info("Initializing database and creating tables if they do not exist.")
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables initialized.")

def get_user_profile(user_id: int = 1) -> Optional[UserProfile]:
    """Retrieves the user profile from the database."""
    logger.info(f"Retrieving user profile for user_id={user_id}")
    with Session(engine) as session:
        statement = select(UserProfile).where(UserProfile.id == user_id)
        results = session.exec(statement)
        profile = results.first()
        if profile:
            logger.info(f"Found user profile for user_id={user_id}: goal={profile.goal}, diet={profile.diet_type}")
        else:
            logger.info(f"No user profile found for user_id={user_id}")
        return profile

def save_user_profile(profile: UserProfile) -> UserProfile:
    """Saves or updates the user profile."""
    logger.info(f"Saving/updating user profile for user_id={profile.id}")
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
            logger.info(f"Updated user profile: {db_profile.model_dump()}")
            return db_profile
        else:
            # Insert new
            session.add(profile)
            session.commit()
            session.refresh(profile)
            logger.info(f"Created new user profile: {profile.model_dump()}")
            return profile

def log_food(food_item: FoodLog) -> FoodLog:
    """Logs a food item to the database."""
    logger.info(f"Logging food item: {food_item.food_name}, calories={food_item.calories} kcal, P/C/F={food_item.protein}g/{food_item.carbs}g/{food_item.fat}g")
    with Session(engine) as session:
        session.add(food_item)
        session.commit()
        session.refresh(food_item)
        logger.info(f"Food item logged successfully with ID: {food_item.id}")
        return food_item

def get_food_logs(limit: int = 100) -> List[FoodLog]:
    """Retrieves list of food logs sorted by timestamp descending."""
    logger.info(f"Retrieving food logs with limit={limit}")
    with Session(engine) as session:
        statement = select(FoodLog).order_by(FoodLog.timestamp.desc()).limit(limit)
        logs = list(session.exec(statement).all())
        logger.info(f"Retrieved {len(logs)} food log entries.")
        return logs

def get_todays_food_logs() -> List[FoodLog]:
    """Retrieves food logs for today (from midnight onwards)."""
    logger.info("Retrieving today's food logs")
    with Session(engine) as session:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        statement = select(FoodLog).where(FoodLog.timestamp >= today_start).order_by(FoodLog.timestamp.desc())
        logs = list(session.exec(statement).all())
        logger.info(f"Retrieved {len(logs)} food log entries for today.")
        return logs

def delete_food_log(log_id: int) -> bool:
    """Deletes a food log entry."""
    logger.info(f"Attempting to delete food log with ID={log_id}")
    with Session(engine) as session:
        log = session.get(FoodLog, log_id)
        if log:
            session.delete(log)
            session.commit()
            logger.info(f"Deleted food log ID={log_id} successfully.")
            return True
        logger.warning(f"Failed to delete food log ID={log_id}: log not found.")
        return False

def save_chat_message(message: ChatMessage) -> ChatMessage:
    """Saves a chatbot message to history."""
    logger.info(f"Saving chat message: role={message.role}, agent={message.agent_name}")
    with Session(engine) as session:
        session.add(message)
        session.commit()
        session.refresh(message)
        logger.info(f"Saved chat message ID={message.id}")
        return message

def get_chat_history(limit: int = 50) -> List[ChatMessage]:
    """Retrieves chat message history."""
    logger.info(f"Retrieving chat history (limit={limit})")
    with Session(engine) as session:
        statement = select(ChatMessage).order_by(ChatMessage.timestamp.asc()).limit(limit)
        history = list(session.exec(statement).all())
        logger.info(f"Retrieved {len(history)} messages from chat history.")
        return history

def clear_chat_history():
    """Deletes all messages in chat history."""
    logger.info("Clearing chat history from database.")
    with Session(engine) as session:
        session.query(ChatMessage).delete()
        session.commit()
        logger.info("Chat history cleared successfully.")

