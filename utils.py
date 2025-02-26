async def is_slot_available(day, time, user_id=None):
    """
    Проверяет доступность слота для записи.
    
    Args:
        day: День слота
        time: Время слота
        user_id: ID пользователя (для проверки повторной записи)
        
    Returns:
        bool: True если слот доступен, False если занят
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT id, giver_id, receiver_id FROM slots WHERE day = ? AND time = ? AND status = 'active'",
                (day, time)
            )
            existing_slot = await cursor.fetchone()
            
            if existing_slot is None:
                return True
                
            if user_id is None:
                return existing_slot[2] is None
            
            
            slot_id, giver_id, receiver_id = existing_slot
            
            if giver_id == user_id:
                logger.info(f"Пользователь {user_id} является дарителем в слоте {slot_id}")
                return False
            
            if receiver_id is not None:
                logger.info(f"Слот {slot_id} уже занят получателем {receiver_id}")
                return False
            
            cursor = await db.execute(
                """
                SELECT id FROM slots 
                WHERE day = ? AND time = ? AND status = 'active' 
                AND (giver_id = ? OR receiver_id = ?)
                """,
                (day, time, user_id, user_id)
            )
            conflicting_slot = await cursor.fetchone()
            if conflicting_slot:
                logger.info(f"Пользователь {user_id} уже записан на другой слот в это время")
                return False
            
            logger.info(f"Слот {slot_id} доступен для записи пользователем {user_id}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности слота: {e}")
        return False