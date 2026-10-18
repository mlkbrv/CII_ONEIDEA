/*
 * Russian — the reference table.
 *
 * Every key the app uses must exist here: the other languages fall back to
 * this one, so a key missing here shows up as the raw key on screen.
 *
 * Keys are namespaced by screen. `common.*` is anything that appears on more
 * than one, which is also the test of whether a string belongs there.
 */
export default {
  // --- common --------------------------------------------------------------
  "common.coins": "монет",
  "common.open": "Открыть",
  "common.cancel": "Отмена",
  "common.retry": "Попробовать снова",
  "common.loading": "Загружаем…",
  "common.error_title": "Не удалось загрузить",
  "common.error_hint": "Проверь соединение",
  "common.follow": "Подписаться",
  "common.unfollow": "Отписаться",
  "common.streak": "Серия побед",
  "common.wardrobe": "Гардероб",
  "common.shop": "Магазин",
  "common.finished": "завершён",
  "common.minutes_short": "мин",
  "common.hours_short": "ч",
  "common.days_short": "д",

  // --- navigation ----------------------------------------------------------
  "nav.home": "Главная",
  "nav.shop": "Магазин",
  "nav.battles": "Баттлы",
  "nav.friends": "Друзья",
  "nav.profile": "Профиль",
  "nav.notifications": "Уведомления",

  // --- home ----------------------------------------------------------------
  "home.scan_cta": "📷 Ввести код с крышки",
  "home.battle_running": "Идёт баттл",
  "home.no_battles": "Баттлов нет",
  "home.no_battles_hint":
    "Вызови друга на баттл образов — победитель забирает весь призовой фонд.",
  "home.find_opponent": "Найти соперника",
  "home.time_left": "осталось {time}",
  "home.leaders": "Лидеры",

  // --- scan ----------------------------------------------------------------
  "scan.title": "Код с крышки",
  "scan.hint": "Каждая крышка — это монеты. Отсканируй код или введи его руками.",
  "scan.scan_button": "📷 Сканировать",
  "scan.submit": "Активировать",
  "scan.checking": "Проверяем…",
  "scan.placeholder": "XXXX-XXXX",
  "scan.label": "Код с крышки",
  "scan.success": "Готово! +{coins} монет. Баланс:",
  "scan.err_404": "Код не найден. Проверь, что ввёл его правильно.",
  "scan.err_409": "Этот код уже использован.",
  "scan.err_410": "Срок действия кода истёк.",
  "scan.err_401": "Открой приложение из Telegram.",
  "scan.err_503": "Бот ещё не настроен на сервере.",
  "scan.err_generic": "Не удалось активировать код",

  // --- shop ----------------------------------------------------------------
  "shop.all": "Все",
  "shop.pick_hint": "Выбери вещь — примерим её на твоём медведе, прежде чем покупать.",
  "shop.buy": "Купить",
  "shop.buying": "Покупаем…",
  "shop.owned": "Уже в гардеробе",
  "shop.owned_short": "✓ есть",
  "shop.not_enough": "Не хватает монет",
  "shop.bought": "{item} — куплено! Осталось {balance} монет",
  "shop.err_funds": "Не хватает монет — активируй ещё одну крышку",
  "shop.err_owned": "Эта вещь уже у тебя в гардеробе",
  "shop.err_generic": "Не удалось купить",

  // --- wardrobe ------------------------------------------------------------
  "wardrobe.all": "Всё",
  "wardrobe.empty": "Гардероб пуст",
  "wardrobe.empty_hint":
    "Активируй код с крышки, чтобы получить монеты, и загляни в магазин.",
  "wardrobe.to_shop": "В магазин",
  "wardrobe.equip": "Надеть",
  "wardrobe.unequip": "Снять",
  "wardrobe.of": "Гардероб {username}",
  "wardrobe.hidden": "Гардероб скрыт",
  "wardrobe.hidden_hint": "Этот игрок не открывает свой гардероб.",
  "wardrobe.empty_other": "Тут пока пусто",
  "slot.hair": "Причёски",
  "slot.hat": "Головные уборы",
  "slot.top": "Верх",
  "slot.bottom": "Низ",
  "slot.shoes": "Обувь",
  "slot.accessory": "Аксессуары",

  // --- profile -------------------------------------------------------------
  "profile.followers": "подписчиков",
  "profile.following": "подписок",
  "profile.streak_short": "серия",
  "profile.watch_battle": "⚔️ Смотреть баттл",
  "profile.challenge": "⚔️ Вызвать",
  "profile.duration_question": "Сколько длится баттл?",
  "profile.challenge_sent": "Вызов отправлен. Ждём ответа соперника.",
  "profile.err_busy": "Один из вас уже участвует в баттле",
  "profile.err_challenge": "Не удалось отправить вызов",
  "profile.view_wardrobe": "👀 Посмотреть гардероб",
  "profile.wardrobe_private": "Этот игрок закрыл свой гардероб.",
  "profile.language": "Язык",
  "duration.30": "30 минут",
  "duration.60": "1 час",
  "duration.360": "6 часов",
  "duration.1440": "24 часа",

  // --- friends and search --------------------------------------------------
  "friends.search_placeholder": "Найти игрока по имени",
  "friends.nobody_found": "Никого не нашли",
  "friends.nobody_found_hint": "Попробуй другое имя.",
  "friends.no_following": "Ты пока ни на кого не подписан",
  "friends.no_following_hint":
    "Найди игроков через поиск — их баттлы появятся в ленте, а их самих можно будет вызвать.",
  "follows.followers": "Подписчики",
  "follows.following": "Подписки",
  "follows.no_followers": "Пока нет подписчиков",
  "follows.no_following": "Пока нет подписок",

  // --- battles -------------------------------------------------------------
  "battles.mine": "Мои",
  "battles.others": "Другие",
  "battles.my_subscriptions": "Мои подписки",
  "battles.all": "Все",
  "battles.empty": "Пока пусто",
  "battles.empty_hint":
    "Вызови кого-нибудь на баттл образов — победитель забирает весь призовой фонд.",
  "battles.to_friends": "К друзьям",
  "battles.challenges_you": "{username} вызывает тебя на баттл",
  "battles.accept": "Принять",
  "battles.decline": "Отклонить",
  "battles.you_challenged": "Ты вызвал {username} — ждём ответа",
  "battles.cancel_challenge": "Отменить вызов",
  "battles.err_conflict": "Кто-то из вас уже в баттле — этот вызов больше не действителен",
  "battles.err_generic": "Не удалось ответить на вызов",
  "battles.none_following": "У твоих подписок нет баттлов",
  "battles.none_following_hint": "Подпишись на больше игроков или посмотри все баттлы.",
  "battles.none_at_all": "Сейчас никто не сражается",
  "battles.none_at_all_hint": "Загляни позже — или начни свой.",
  "battles.card_meta": "Приз: {prize} 🪙 · осталось {time}",
  "battles.mine_prefix": "Твой баттл · ",

  // --- one battle ----------------------------------------------------------
  "battle.running": "🔥 Идёт баттл",
  "battle.finished": "Баттл завершён",
  "battle.prize_pool": "Призовой фонд: {prize} 🪙",
  "battle.prize_and_time": "Призовой фонд: {prize} 🪙 · осталось {time}",
  "battle.votes_share": "{votes} голосов · {share}%",
  "battle.winner": "🏆 Победил {username} и забрал {prize} 🪙",
  "battle.draw": "🤝 Ничья — призовой фонд поделён поровну",
  "battle.yours":
    "Это твой баттл. Зови подписчиков голосовать — каждый голос добавляет монету в призовой фонд.",
  "battle.already_voted": "Ты уже отдал свой голос в этом баттле.",
  "battle.vote_for": "За {username} · 1 🪙",
  "battle.need_coin": "Нужна хотя бы одна монета.",
  "battle.get_coins": "Активируй код с крышки",
  "battle.err_funds": "Не хватает монет — один голос стоит 1 монету",
  "battle.err_participant": "Участники не голосуют в своём баттле",
  "battle.err_voted": "Ты уже голосовал в этом баттле",
  "battle.err_generic": "Не удалось проголосовать",

  // --- leaderboard ---------------------------------------------------------
  "leaderboard.streak": "🔥 Серия",
  "leaderboard.wins": "🏆 Победы",
  "leaderboard.empty": "Таблица пуста",
  "leaderboard.empty_hint": "Пока никто не сражался.",
  "leaderboard.you_are_here": "Ты сейчас здесь",

  // --- notifications -------------------------------------------------------
  "notifications.title": "Уведомления",
  "notifications.empty": "Пока тихо",
  "notifications.empty_hint":
    "Здесь появятся вызовы на баттлы, результаты и новые подписчики.",
  "time.just_now": "только что",
  "time.minutes_ago": "{count} мин назад",
  "time.hours_ago": "{count} ч назад",

  // --- sign in -------------------------------------------------------------
  "signin.tagline":
    "Собирай монеты с крышек, одевай своего медведя и вызывай друзей на баттл образов.",
  "signin.prompt": "Войди через Telegram, чтобы начать:",
  "signin.not_configured": "Вход через браузер не настроен. Открой приложение из Telegram.",
  "signin.open_in_telegram": "Открыть в Telegram",
  "signin.failed": "Не удалось войти",

  // --- demographics ----------------------------------------------------------
  "demographics.title": "Расскажи о себе",
  "demographics.subtitle": "Это по желанию. Ответь и получи 100 монет в подарок.",
  "demographics.gender": "Пол",
  "demographics.gender_male": "Мужской",
  "demographics.gender_female": "Женский",
  "demographics.gender_undisclosed": "Не хочу говорить",
  "demographics.year": "Год рождения",
  "demographics.year_placeholder": "Не указывать",
  "demographics.privacy": "Эти данные нужны только для общей статистики и не видны другим игрокам.",
  "demographics.save": "Сохранить",
  "demographics.skip": "Позже",
  "demographics.error": "Не удалось сохранить. Попробуй ещё раз.",
  "demographics.thanks": "Спасибо!",
  "demographics.bonus_received": "Твой подарок:",
  "demographics.close": "Отлично",
  "demographics.profile_cta": "📝 Ответь на пару вопросов и получи 100 монет",
};
