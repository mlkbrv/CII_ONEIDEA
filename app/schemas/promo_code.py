from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PromoCodeRedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)

    @field_validator("code")
    @classmethod
    def strip_code(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("code is required")
        return stripped


class PromoCodeRedeemResponse(BaseModel):
    promo_code_id: UUID
    coin_reward: int
    balance: int
