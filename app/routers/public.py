# type: ignore
from fastapi import APIRouter, Request, Response, status, Depends, HTTPException
from sqlalchemy import and_, or_
from .. import schemas, models, utils
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
from typing import List

router = APIRouter()
from ..oauth2 import create_access_token

ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserResponse,
)
async def register(
    payload: schemas.CreateUserSchema, response: Response, db: Session = Depends(get_db)
):
    # Check if user already exist
    user = (
        db.query(models.User)
        .filter(
            and_(
                models.User.name == payload.name.lower(), models.User.deleted_at == None
            )
        )
        .first()
    )
    if user:
        new_user = user
    else:
        new_user = models.User(**payload.model_dump())
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    access_token = create_access_token({"user_id": str(new_user.id)})

    return {
        "id": new_user.id,
        "name": new_user.name,
        "role": new_user.role,
        "api_key": access_token,
    }


@router.get("/instrument")
async def list_instruments(
    db: Session = Depends(get_db),
) -> list[schemas.InstrumentResponse]:
    list_of_instruments = (
        db.query(models.Instrument).filter(models.Instrument.deleted_at == None).all()
    )
    return list_of_instruments


@router.get("/orderbook/{ticker}")
async def get_orderbook(
    ticker: str, limit=10, db: Session = Depends(get_db)
) -> schemas.OrderbookResponse:
    ticker_entity = (
        db.query(models.Instrument)
        .filter(models.Instrument.ticker == ticker)
        .filter(models.Instrument.deleted_at == None)
        .first()
    )
    if ticker_entity is None:
        return Response("Not found", status_code=404)
    base_orders = (
        db.query(models.Order)
        .filter(models.Order.deleted_at == None)
        .filter(models.Order.instrument_id == ticker_entity.id)
        .filter(models.Order.status != models.StatusOrders.EXECUTED)
        .filter(models.Order.status != models.StatusOrders.CANCELLED)
    )
    return {
        "bid_levels": base_orders.filter(
            models.Order.direction == models.DirectionsOrders.BUY
        )
        .order_by(models.Order.price.desc())
        .limit(limit)
        .all(),
        "ask_levels": base_orders.filter(
            models.Order.direction == models.DirectionsOrders.SELL
        )
        .order_by(models.Order.price.asc())
        .limit(limit)
        .all(),
    }


@router.get("/transactions/{ticker}")
async def get_transaction_history(ticker: str, limit=10, db: Session = Depends(get_db))->List[schemas.TransactionsResponse]:
    ticker_entity = (
        db.query(models.Instrument)
        .filter(models.Instrument.ticker == ticker)
        .filter(models.Instrument.deleted_at == None)
        .first()
    )
    if ticker_entity is None:
        return Response("Not found", status_code=404)
    
    transactions = db.query(models.Transaction).filter(models.Transaction.instrument_id == ticker_entity.id).order_by(models.Transaction.created_at.desc()).all()
    result = []
    for transaction in transactions:
        result.append({
            'ticker': ticker,
            'amount': transaction.amount,
            'price': transaction.price,
            'timestamp': transaction.created_at
        })
    
    return result