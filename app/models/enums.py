from enum import Enum

from sqlalchemy import Enum as SAEnum


class AuthProviderType(str, Enum):
    TELEGRAM = "telegram"


class DevicePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"


class TransactionType(str, Enum):
    PROMO_REDEEM = "promo_redeem"
    PRODUCT_CODE_REDEEM = "product_code_redeem"
    SHOP_PURCHASE = "shop_purchase"
    VOTE = "vote"
    PRIZE = "prize"


class ClothingSlot(str, Enum):
    HAIR = "hair"
    TOP = "top"
    BOTTOM = "bottom"
    SHOES = "shoes"
    ACCESSORIES = "accessories"


class CompetitionRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class CompetitionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class NotificationType(str, Enum):
    CHALLENGE = "challenge"
    COMPETITION_ACCEPTED = "competition_accepted"
    COMPETITION_ENDING = "competition_ending"
    COMPETITION_RESULT = "competition_result"


def str_enum(enum_cls: type[Enum], *, length: int = 32) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        values_callable=lambda x: [e.value for e in x],
        length=length,
    )
