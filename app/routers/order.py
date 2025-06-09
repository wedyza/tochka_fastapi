#type: ignore

from fastapi import APIRouter, Response, HTTPException, Depends, status
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2
from sqlalchemy import and_, func, text
from ..functions import check_custom_balance, making_a_deal, order_processing, unlock_custom_balance
from typing import List

router = APIRouter()


def fill_list(order:models.Order, ticker:str):
    return {
        "id": order.id,
        "user_id": order.user_id,
        "timestamp": order.created_at,
        "filled": order.filled,
        "body": {
            "direction": order.direction,
            "price": order.price,
            'qty': order. quantity,
            'ticker': ticker
        }
    }

@router.get('')
def list_orders(db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user))->List[schemas.OrdersResponse]:
    orders = db.query(models.Order).filter(models.Order.deleted_at == None).all()
    answer = []

    for order in orders:
        ticker = db.query(models.Instrument).filter(models.Instrument.id == order.instrument_id).first()
        answer.append(fill_list(order, ticker.ticker))
    return answer


@router.get('/{order_id}')
def get_order(order_id: str, db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user))->schemas.OrdersResponse:
    order = db.query(models.Order).filter(models.Order.deleted_at == None).filter(models.Order.id == order_id).first()
    if order is None:
        raise HTTPException(detail='Не найдено активного заказа с таким ID', status_code=status.HTTP_404_NOT_FOUND)
    ticker = db.query(models.Instrument).filter(models.Instrument.id == order.instrument_id).first()
    return fill_list(order, ticker.ticker)


@router.delete('/{order_id}')
def delete_order(order_id: str, db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user))->schemas.DeleteResponse:
    order = db.query(models.Order).filter(
        and_(models.Order.deleted_at == None, models.Order.id == order_id, models.Order.filled == False)
    ).first()

    if order is None:
        raise HTTPException(detail='Не найдено активного заказа с таким ID', status_code=status.HTTP_404_NOT_FOUND)
    
    order.deleted_at = text('now()')

    rub_instrument = db.query(models.Instrument).filter(and_(models.Instrument.deleted_at == None, models.Instrument.ticker == 'RUB')).first()
    if order.direction == models.DirectionsOrders.BUY:
        unlock_custom_balance(db, order.user_id, (order.quantity - order.filled_quantity)*order.price, rub_instrument.id)
    else:
        unlock_custom_balance(db, order.user_id, order.quantity - order.filled_quantity, order.instrument_id)

    db.commit()
    db.refresh(order)

    return {
        'success': True
    }

@router.post('')
def create_order(payload: schemas.OrderCreateInput,db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)):
    instrument = db.query(models.Instrument).filter(
        and_(models.Instrument.deleted_at == None, models.Instrument.ticker == payload.ticker)
    ).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено валюты с таким тикером!')
    
    order = models.Order()
    order.direction = payload.direction
    order.user_id = user_id
    order.instrument_id = instrument.id
    order.quantity = payload.qty

    if payload.price != 0:
        # user = db.query(models.User).filter(models.User.id==user_id).first()
        user_must_pay = payload.qty * payload.price

        order.price = payload.price
        
        if payload.direction == models.DirectionsOrders.BUY:
            user_rub_balance = check_custom_balance(db, user_id, 'RUB')
            if user_rub_balance < user_must_pay:
                raise HTTPException(status_code=422, detail=f'На счету пользователя {user_rub_balance} рублей. Необходимо еще {user_must_pay - user_rub_balance} для создания заказа с указанными хар-ками')
        else:
            user_custom_balance = check_custom_balance(db, user_id, instrument.ticker)
            if user_custom_balance < order.quantity:
                raise HTTPException(status_code=422, detail='На счету пользователя не хватает выбранной валюты')
        order_processing(db, order)
    else:
        need_quantity = payload.qty
        final_price = 0
        opposite_order_direction = models.DirectionsOrders.BUY if payload.direction == models.DirectionsOrders.SELL else payload.direction

        currency_orders_quantity = db.query(func.sum(models.Order.quantity - models.Order.filled_quantity)).filter(and_(models.Order.direction == opposite_order_direction, models.Order.filled == False, models.Order.deleted_at == None))
        if need_quantity > currency_orders_quantity:
            raise HTTPException(status_code=422, detail='В данный момент в стакане нет столько валюты, сколько вы хотите купить.')
        
        if payload.direction == models.DirectionsOrders.BUY:
            orders = db.query(models.Order).filter(and_(
                models.Order.direction == opposite_order_direction, models.Order.deleted_at == None, models.Order.filled == False
            )).order_by(models.Order.price.asc()).all()
        else:
            orders = db.query(models.Order).filter(and_(
                models.Order.direction == opposite_order_direction, models.Order.deleted_at == None, models.Order.filled == False
            )).order_by(models.Order.price.desc()).all()

        stocked_orders = list()
        for another_order in orders:
            local_need_quantity = another_order.quantity - another_order.filled_quantity
            if order.filled_quantity + local_need_quantity > order.quantity:
                order_count = order.quantity - order.filled_quantity
                another_order.filled_quantity += order_count
                order.filled_quantity += order_count

                # another_order_query = db.query(models.Order).filter(id == another_order.id).update(another_order.dict(exclude_unset=True), synchronize_session=False)
                db.commit()
                break

            need_quantity -= another_order.quantity
            stocked_orders.append(another_order)
            final_price = another_order.quantity * another_order.price
            if payload.direction == models.DirectionsOrders.BUY and final_price > user_rub_balance:
                raise HTTPException(status_code=422, detail='На счету пользователя недостаточно денег для закрытия заказа')
            
            if order.filled_quantity + local_need_quantity == order.quantity:
                break
        

        db.add(order)
        db.commit()
        db.refresh(order)

        for another_order in stocked_orders:
            if order.direction == models.DirectionsOrders.BUY:
                making_a_deal(order, another_order ,db)
            else:
                making_a_deal(another_order, order ,db)
    return {
        'success': True,
        'order_id': order.id
    }
