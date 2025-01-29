from datetime import datetime, timedelta
from database import get_user_by_id

async def format_slot_info(slot):
    giver = await get_user_by_id(slot['giver_id'])
    giver_username = giver['username'] if giver else "Неизвестный пользователь"
    giver_comment = slot['giver_comment']
    if giver_comment:
        return f"{slot['day']} {slot['time']} - {giver_username} ({giver_comment})"
    else:
        return f"{slot['day']} {slot['time']} - {giver_username}"

async def is_slot_available(day, time):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM slots WHERE day = ? AND time = ? AND status = 'active'",
            (day, time)
        )
        existing_slot = await cursor.fetchone()
        return existing_slot is None
      
async def is_cancellation_allowed(slot):
    slot_time = datetime.strptime(f"{slot['day']} {slot['time']}", "%d %B %H:%M")
    return datetime.now() < slot_time - timedelta(minutes=30)