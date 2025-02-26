@router.callback_query(ReceiveMassage.confirmation, F.data == "confirm_receive_rules")
async def show_available_slots_after_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    slots = await get_available_slots()
    if not slots:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, сейчас нет доступных слотов для записи.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return

    user_id = callback_query.from_user.id
    
    now = get_current_moscow_time()
    logger.info(f"Текущее московское время: {now}")
    
    logger.info(f"Доступные слоты: {len(slots)}")
    for i, slot in enumerate(slots):
        logger.info(f"Слот {i+1}: день={slot.get('day', 'Н/Д')}, время={slot.get('time', 'Н/Д')}")
    
    filtered_slots = []
    for slot in slots:
        try:
            if 'day' not in slot or 'time' not in slot:
                logger.error(f"Слот не содержит необходимых полей day или time: {slot}")
                continue
                
            day_str = slot['day']
            if not day_str or len(day_str.split()) < 2:
                logger.error(f"Некорректный формат дня: {day_str}")
                continue
            
            day_parts = day_str.split()
            if day_parts[0] == 'День':
                logger.error(f"Некорректный формат дня (начинается с 'День'): {day_str}")
                continue
            
            normalized_time = normalize_time_format(slot['time'])
            logger.info(f"Нормализованное время слота: {normalized_time} (исходное: {slot['time']})")
              
            slot_datetime = parse_slot_datetime(slot['day'], slot['time'])
            
            is_future = slot_datetime and slot_datetime > now
            logger.info(f"Слот в будущем: {is_future}, datetime={slot_datetime}")
            
            if not is_future:
                logger.info(f"Пропущен прошедший слот: {slot['day']} {slot['time']}")
                continue
                
            is_not_self = slot['giver_id'] != user_id
            logger.info(f"Слот не создан текущим пользователем: {is_not_self}, giver_id={slot['giver_id']}, user_id={user_id}")
            
            if not is_not_self:
                logger.info(f"Пропущен собственный слот: {slot['day']} {slot['time']}")
                continue
                
            receiver_id = slot['receiver_id']
            if receiver_id is not None:
                logger.info(f"Пропущен занятый слот: {slot['day']} {slot['time']}, receiver_id={receiver_id}")
                continue
                
            has_conflicts = not await is_slot_available(slot['day'], slot['time'], user_id)
            logger.info(f"Слот имеет конфликты: {has_conflicts}")
            
            if has_conflicts:
                logger.info(f"Пропущен конфликтующий слот: {slot['day']} {slot['time']}")
                continue
            
            filtered_slots.append(slot)
            logger.info(f"Добавлен доступный слот: {slot['day']} {slot['time']}")
        except Exception as e:
            logger.error(f"Ошибка при фильтрации слота: {e}")
    
    if not filtered_slots:
        inline_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            "К сожалению, все доступные слоты уже прошли или заняты.", 
            reply_markup=inline_markup
        )
        await state.clear()
        return

    markup = types.InlineKeyboardMarkup(inline_keyboard=[])
    days = sorted(list(set([slot['day'] for slot in filtered_slots])))

    for day in days:
        button = types.InlineKeyboardButton(text=day, callback_data=f"receive_day:{day}")
        markup.inline_keyboard.append([button])

    await callback_query.message.edit_text("Выберите день:", reply_markup=markup)
    await state.set_state(ReceiveMassage.day)