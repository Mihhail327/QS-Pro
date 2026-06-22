import asyncio
from datetime import datetime
import structlog
from sqlmodel import select
from app.database.config import async_session_factory
from app.models.snippet import Snippet

logger = structlog.get_logger(__name__)

async def start_reminder_daemon():
    """Background task runner to periodically check and trigger scheduled reminders."""
    logger.info("🔔 Background reminder daemon starting up...")
    while True:
        try:
            # Poll every 10 seconds for due alerts
            await asyncio.sleep(10)
            
            async with async_session_factory() as session:
                now = datetime.utcnow()
                statement = select(Snippet).where(
                    Snippet.reminder_at != None,
                    Snippet.reminder_at <= now,
                    Snippet.is_notified == False
                )
                result = await session.execute(statement)
                pending_reminders = result.scalars().all()
                
                if pending_reminders:
                    for s in pending_reminders:
                        logger.warn(
                            "🔔 [ALERT] Scheduled vault reminder fired!",
                            snippet_id=s.id,
                            title=s.title,
                            category=s.category,
                            sub_category=s.sub_category,
                            reminder_time=s.reminder_at.isoformat()
                        )
                        s.is_notified = True
                        session.add(s)
                    await session.commit()
                    
        except asyncio.CancelledError:
            logger.info("🔔 Background reminder daemon cancelled.")
            break
        except Exception as e:
            logger.error("⚠️ Exception in background reminder daemon", error=str(e))
