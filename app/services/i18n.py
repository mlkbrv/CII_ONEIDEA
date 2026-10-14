"""
Server-side wording, in the three languages Cola Fest ships in.

The Mini App carries its own translations — it can, everything it says is a
reaction to something the user just did. The server needs its own set because
it composes text at moments when nobody is asking: the bot writes "your battle
ends in 10 minutes" from a sweeper thread, long after any request context is
gone. The only thing available then is the recipient's row in `users`, which
is why the language is stored there.

Русский is the default: Cola Fest is an Azerbaijani event where Russian is the
common working language, and a wrong guess in Russian is understood by more of
the audience than a wrong guess in either of the others.

Adding a language means adding one dict below. A key missing from it falls
back to Russian rather than showing the key, because a message in the wrong
language is still a message, and `competition_won` is not.
"""
import logging

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "ru"
SUPPORTED_LANGUAGES = ("ru", "en", "az")


def normalise_language(value: str | None) -> str:
    """Reduce whatever Telegram (or a client) sent to a language we have.

    Telegram sends IETF tags — "en", "ru", "az-AZ", sometimes "en-GB". Only
    the primary subtag matters here: we do not distinguish regional variants,
    and treating "az-AZ" as unsupported would send an Azerbaijani user
    Russian for no reason.
    """
    if not value:
        return DEFAULT_LANGUAGE
    primary = value.strip().lower().replace("_", "-").split("-")[0]
    return primary if primary in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, language: str | None = None, **params) -> str:
    """Look up `key` in `language`, formatting it with `params`."""
    lang = normalise_language(language)
    table = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])

    template = table.get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
        if template is None:
            logger.warning("No translation for %r in any language", key)
            return key
        logger.info("Key %r is missing in %r, falling back to %s", key, lang, DEFAULT_LANGUAGE)

    try:
        return template.format(**params)
    except KeyError:
        # A template expecting a parameter the caller did not pass. Returning
        # the raw template beats raising in the middle of sending a batch of
        # notifications to real people.
        logger.exception("Missing parameter while formatting %r", key)
        return template


def human_duration(minutes: int | None, language: str | None = None) -> str:
    """"30 минут" / "1 hour" / "6 saat" — the presets from TZ section 10.

    Kept out of the tables because Russian needs three plural forms and the
    other two need one; a lookup table would have to carry every number.
    """
    if not minutes:
        return ""
    lang = normalise_language(language)

    if minutes < 60:
        return {"ru": f"{minutes} минут", "en": f"{minutes} minutes", "az": f"{minutes} dəqiqə"}[lang]

    hours = minutes // 60
    if lang == "en":
        return "1 hour" if hours == 1 else f"{hours} hours"
    if lang == "az":
        return f"{hours} saat"
    # Russian: 1 час / 2-4 часа / 5+ часов.
    if hours == 1:
        return "1 час"
    if hours < 5:
        return f"{hours} часа"
    return f"{hours} часов"


# --- Tables ----------------------------------------------------------------
# Keys are grouped: notification.* is what a player reads in the feed and in
# Telegram, bot.* is what the bot says in a chat.

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "notification.new_follower": "👋 {actor} подписался на тебя",
        "notification.competition_request": "⚔️ {actor} вызывает тебя на баттл{duration}!",
        "notification.competition_request.duration": " на {duration}",
        "notification.competition_accepted": "✅ {actor} принял твой вызов. Баттл начался!",
        "notification.competition_declined": "🚫 {actor} отклонил твой вызов",
        "notification.competition_ending_soon": "⏰ Твой баттл заканчивается через {minutes} мин. Зови болельщиков!",
        "notification.competition_won": "🏆 Ты выиграл баттл!\nПризовой фонд: {prize} монет{streak}",
        "notification.competition_won.streak": "\nСерия побед: {streak}",
        "notification.competition_lost": "😔 Ты проиграл баттл. Смени образ и попробуй снова!",
        "notification.competition_draw": "🤝 Ничья! Призовой фонд {prize} монет поделён поровну",
        "notification.unknown": "У тебя новое уведомление в Cola Fest",
        "notification.someone": "Кто-то",

        "bot.start": (
            "🐻‍❄️ <b>Cola Fest</b>\n\n"
            "Покупай Coca-Cola, вводи код с крышки и получай монеты.\n"
            "Одевай своего медведя, вызывай друзей на баттл образов "
            "и забирай призовой фонд.\n\n"
            "Открой приложение или отправь код прямо сюда:\n"
            "<code>/redeem КОД</code>"
        ),
        "bot.open_app": "Открыть Cola Fest",
        "bot.spend_coins": "Потратить монеты",
        "bot.redeem_usage": "Использование: <code>/redeem КОД</code>",
        "bot.no_user": "Не удалось определить пользователя.",
        "bot.code_not_found": "Код не найден. Проверь, что ввёл его правильно.",
        "bot.code_used": "Этот код уже использован.",
        "bot.code_expired": "Срок действия кода истёк.",
        "bot.code_failed": "Не удалось активировать код. Попробуй позже.",
        "bot.error": "Что-то пошло не так. Попробуй ещё раз через минуту.",
        "bot.redeemed": "✅ Код активирован!\n+{coins} монет\nБаланс: <b>{balance}</b>",
        "bot.profile": "👤 <b>{username}</b>\n💰 Монет: {coins}\n🔥 Серия побед: {streak}",
        "bot.fallback": "Открой приложение, чтобы играть, или отправь код с крышки.",
    },
    "en": {
        "notification.new_follower": "👋 {actor} started following you",
        "notification.competition_request": "⚔️ {actor} challenged you to a battle{duration}!",
        "notification.competition_request.duration": " for {duration}",
        "notification.competition_accepted": "✅ {actor} accepted your challenge. The battle is on!",
        "notification.competition_declined": "🚫 {actor} declined your challenge",
        "notification.competition_ending_soon": "⏰ Your battle ends in {minutes} min. Rally your followers!",
        "notification.competition_won": "🏆 You won the battle!\nPrize pool: {prize} coins{streak}",
        "notification.competition_won.streak": "\nWinning streak: {streak}",
        "notification.competition_lost": "😔 You lost the battle. Change your outfit and try again!",
        "notification.competition_draw": "🤝 A draw! The {prize}-coin prize pool is split evenly",
        "notification.unknown": "You have a new Cola Fest notification",
        "notification.someone": "Someone",

        "bot.start": (
            "🐻‍❄️ <b>Cola Fest</b>\n\n"
            "Buy Coca-Cola, enter the code from the cap and earn coins.\n"
            "Dress up your bear, challenge your friends to outfit battles "
            "and take the prize pool.\n\n"
            "Open the app, or send a code right here:\n"
            "<code>/redeem CODE</code>"
        ),
        "bot.open_app": "Open Cola Fest",
        "bot.spend_coins": "Spend coins",
        "bot.redeem_usage": "Usage: <code>/redeem CODE</code>",
        "bot.no_user": "Could not identify you.",
        "bot.code_not_found": "Code not found. Check that you typed it correctly.",
        "bot.code_used": "This code has already been used.",
        "bot.code_expired": "This code has expired.",
        "bot.code_failed": "Could not redeem the code. Try again later.",
        "bot.error": "Something went wrong. Try again in a minute.",
        "bot.redeemed": "✅ Code redeemed!\n+{coins} coins\nBalance: <b>{balance}</b>",
        "bot.profile": "👤 <b>{username}</b>\n💰 Coins: {coins}\n🔥 Winning streak: {streak}",
        "bot.fallback": "Open the app to play, or send a code from a cap.",
    },
    "az": {
        "notification.new_follower": "👋 {actor} səni izləməyə başladı",
        "notification.competition_request": "⚔️ {actor} səni döyüşə çağırır{duration}!",
        "notification.competition_request.duration": " — {duration}",
        "notification.competition_accepted": "✅ {actor} çağırışını qəbul etdi. Döyüş başladı!",
        "notification.competition_declined": "🚫 {actor} çağırışını rədd etdi",
        "notification.competition_ending_soon": "⏰ Döyüşün {minutes} dəqiqəyə bitir. Azarkeşlərini çağır!",
        "notification.competition_won": "🏆 Döyüşü uddun!\nMükafat fondu: {prize} sikkə{streak}",
        "notification.competition_won.streak": "\nQalibiyyət seriyası: {streak}",
        "notification.competition_lost": "😔 Döyüşü uduzdun. Geyimini dəyiş və yenidən cəhd et!",
        "notification.competition_draw": "🤝 Heç-heçə! {prize} sikkəlik fond bərabər bölündü",
        "notification.unknown": "Cola Fest-də yeni bildirişin var",
        "notification.someone": "Kimsə",

        "bot.start": (
            "🐻‍❄️ <b>Cola Fest</b>\n\n"
            "Coca-Cola al, qapaqdakı kodu daxil et və sikkə qazan.\n"
            "Ayını geyindir, dostlarını geyim döyüşünə çağır "
            "və mükafat fondunu qazan.\n\n"
            "Tətbiqi aç və ya kodu birbaşa bura göndər:\n"
            "<code>/redeem KOD</code>"
        ),
        "bot.open_app": "Cola Fest-i aç",
        "bot.spend_coins": "Sikkələri xərclə",
        "bot.redeem_usage": "İstifadə: <code>/redeem KOD</code>",
        "bot.no_user": "Səni müəyyən etmək alınmadı.",
        "bot.code_not_found": "Kod tapılmadı. Düzgün yazdığını yoxla.",
        "bot.code_used": "Bu kod artıq istifadə olunub.",
        "bot.code_expired": "Kodun müddəti bitib.",
        "bot.code_failed": "Kodu aktivləşdirmək alınmadı. Sonra yenidən cəhd et.",
        "bot.error": "Nəsə səhv getdi. Bir dəqiqədən sonra yenidən cəhd et.",
        "bot.redeemed": "✅ Kod aktivləşdirildi!\n+{coins} sikkə\nBalans: <b>{balance}</b>",
        "bot.profile": "👤 <b>{username}</b>\n💰 Sikkə: {coins}\n🔥 Qalibiyyət seriyası: {streak}",
        "bot.fallback": "Oynamaq üçün tətbiqi aç və ya qapaqdakı kodu göndər.",
    },
}
