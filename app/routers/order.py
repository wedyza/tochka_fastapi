# type: ignore

from fastapi import APIRouter, Response, HTTPException, Depends, status
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2
from sqlalchemy import and_, func, text
from ..functions import (
    check_custom_balance,
    order_processing,
    unlock_custom_balance,
    market_order_processing
)
from typing import List
from uuid import UUID

router = APIRouter()


def fill_list(order: models.Order, ticker: str):
    data = {
        "id": order.id,
        "user_id": order.user_id,
        "timestamp": order.created_at,
        "filled": order.filled,
        "body": {"direction": order.direction, "qty": order.quantity, "ticker": ticker},
        "status": order.status,
    }
    if not order.price is None:
        data["body"]["price"] = order.price
    return data


@router.get("")
def list_orders(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
) -> List[schemas.OrdersResponse]:
    orders = (
        db.query(models.Order)
        .filter(models.Order.deleted_at == None)
        .filter(models.Order.user_id == user_id)
        .all()
    )
    answer = []

    for order in orders:
        ticker = (
            db.query(models.Instrument)
            .filter(models.Instrument.id == order.instrument_id)
            .first()
        )
        answer.append(fill_list(order, ticker.ticker))
    return answer


@router.get("/{order_id}")
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
) -> schemas.OrdersResponse:
    order = (
        db.query(models.Order)
        .filter(models.Order.deleted_at == None)
        .filter(models.Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(
            detail="Не найдено активного заказа с таким ID",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    ticker = (
        db.query(models.Instrument)
        .filter(models.Instrument.id == order.instrument_id)
        .first()
    )
    return fill_list(order, ticker.ticker)


@router.delete("/{order_id}")
def delete_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
) -> schemas.DeleteResponse:
    order = (
        db.query(models.Order)
        .filter(
            and_(
                models.Order.deleted_at == None,
                models.Order.id == order_id,
                models.Order.status != models.StatusOrders.EXECUTED,
                models.Order.status != models.StatusOrders.CANCELLED,
            )
        )
        .first()
    )

    if order is None:
        raise HTTPException(
            detail="Не найдено активного заказа с таким ID",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    order.deleted_at = text("now()")
    order.status = models.StatusOrders.CANCELLED

    rub_instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.deleted_at == None, models.Instrument.ticker == "RUB"
            )
        )
        .first()
    )
    if order.direction == models.DirectionsOrders.BUY:
        unlock_custom_balance(
            db,
            order.user_id,
            (order.quantity - order.filled) * order.price,
            rub_instrument.id,
        )
    else:
        unlock_custom_balance(
            db, order.user_id, order.quantity - order.filled, order.instrument_id
        )

    db.commit()
    db.refresh(order)

    return {"success": True}


@router.post("")
def create_order(
    payload: schemas.OrderCreateInput,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.deleted_at == None,
                models.Instrument.ticker == payload.ticker,
            )
        )
        .first()
    )
    if instrument is None:
        raise HTTPException(
            status_code=404, detail="Не найдено валюты с таким тикером!"
        )

    if payload.price < 0 or payload.qty < 0:
        raise HTTPException(
            status_code=422, detail='Не правильные цифры'
        )
    order = models.Order()
    order.direction = payload.direction
    order.user_id = user_id
    order.instrument_id = instrument.id
    order.quantity = payload.qty
    order.filled = 0

    user_rub_balance = check_custom_balance(db, user_id, "RUB")
    if payload.price != 0:
        user_must_pay = payload.qty * payload.price

        order.price = payload.price

        if payload.direction == models.DirectionsOrders.BUY:
            if user_rub_balance < user_must_pay:
                # raise HTTPException(status_code=400, detail=f'На счету пользователя {user_rub_balance} рублей. Необходимо еще {user_must_pay - user_rub_balance} для создания заказа с указанными хар-ками')
                return Response("first one", status_code=421)
        else:
            user_custom_balance = check_custom_balance(db, user_id, instrument.ticker)
            if user_custom_balance < order.quantity:
                # raise HTTPException(status_code=400, detail='На счету пользователя не хватает выбранной валюты')
                return Response("secnd one", status_code=422)
        order_processing(db, order)
    else:
        order = market_order_processing(db, order, user_rub_balance)
    return {"success": True, "order_id": order.id}
