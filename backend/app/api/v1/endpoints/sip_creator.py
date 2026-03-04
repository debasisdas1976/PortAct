from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset
from app.schemas.sip import SIPPreviewRequest, SIPPreviewResponse, SIPCreateRequest
from app.services.sip_transaction_service import SIPTransactionService, MF_ASSET_TYPES

router = APIRouter()


def _validate_sip_request(asset_id: int, periods, current_user: User, db: Session) -> tuple:
    """Common validation for preview and create endpoints."""
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")

    asset_type_val = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
    if asset_type_val not in MF_ASSET_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"SIP creator only supports mutual fund assets. Got: {asset_type_val}",
        )

    if not asset.isin:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Asset must have an ISIN to look up historical NAV",
        )

    if len(periods) > 1:
        error = SIPTransactionService.validate_non_overlapping(periods)
        if error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, error)

    scheme_code = SIPTransactionService.get_scheme_code(asset)
    if not scheme_code:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Could not resolve AMFI scheme code for ISIN: {asset.isin}. "
            "Please verify the ISIN is correct.",
        )

    return asset, scheme_code


@router.post("/preview", response_model=SIPPreviewResponse)
async def preview_sip_transactions(
    request: SIPPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Preview SIP transactions without creating them."""
    asset, scheme_code = _validate_sip_request(
        request.asset_id, request.periods, current_user, db
    )
    try:
        return SIPTransactionService.preview_sip_transactions(
            asset, request.periods, scheme_code
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/create", response_model=SIPPreviewResponse, status_code=status.HTTP_201_CREATED)
async def create_sip_transactions(
    request: SIPCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create SIP transactions in bulk after preview confirmation."""
    asset, scheme_code = _validate_sip_request(
        request.asset_id, request.periods, current_user, db
    )
    try:
        return SIPTransactionService.create_sip_transactions(
            db, asset, request.periods, scheme_code,
            update_asset_metrics=request.update_asset_metrics,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
