from fastapi import APIRouter, HTTPException, status

from app.dependencies.auth import CurrentUser, SessionDep
from app.schemas.promo_code import PromoCodeRedeemRequest, PromoCodeRedeemResponse
from app.services.promo_code import (
    PromoCodeAlreadyRedeemedError,
    PromoCodeExpiredError,
    PromoCodeNotFoundError,
    redeem_promo_code,
)

router = APIRouter(prefix="/promo-codes", tags=["promo-codes"])


@router.post("/redeem", response_model=PromoCodeRedeemResponse)
async def redeem(
    payload: PromoCodeRedeemRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> PromoCodeRedeemResponse:
    try:
        result = await redeem_promo_code(session, current_user, payload.code)
    except PromoCodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found",
        ) from exc
    except PromoCodeAlreadyRedeemedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Promo code already redeemed",
        ) from exc
    except PromoCodeExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Promo code expired",
        ) from exc
    return PromoCodeRedeemResponse(
        promo_code_id=result.promo_code_id,
        coin_reward=result.coin_reward,
        balance=result.balance,
    )
