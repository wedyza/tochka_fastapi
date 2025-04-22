#type: ignore

from fastapi import APIRouter, HTTPException, Depends
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2
from sqlalchemy import and_, func
from ..functions import check_rub_balance, making_a_deal


router = APIRouter()


@router.get('/')
def list_orders(db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)):
    pass


@router.post('/')
def create_order(payload: schemas.LimitOrderCreateInput | schemas.MarketOrderCreateInput,db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user))->schemas.OrderCreateOutput:
    print(type(payload))
    
    instrument = db.query(models.Instrument).filter(
        and_(models.Instrument.deleted_at != None, models.Instrument.ticker == payload.ticker)
    ).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено валюты с таким тикером!')
    
    order = models.Order()
    order.direction = payload.direction
    order.user_id = user_id
    order.instrument_id = instrument.id
    order.quantity = payload.qty

    user_rub_balance = check_rub_balance(db, user_id)
    if type(payload) == schemas.LimitOrderCreateInput:
        pass
        # user = db.query(models.User).filter(models.User.id==user_id).first()
        user_must_pay = payload.qty * payload.price

        order.price = payload.price
        
        if payload.direction == models.DirectionsOrders.BUY:
            if user_rub_balance == 0:
                raise HTTPException(status_code=400, detail='На счету пользователя нет рублей, невозможно сделать заказ')
            elif user_rub_balance < user_must_pay:
                raise HTTPException(status_code=400, detail=f'На счету пользователя {user_rub_balance} рублей. Необходимо еще {user_must_pay - user_rub_balance} для создания заказа с указанными хар-ками')

        # order_processing(db, order)
    else:
        need_quantity = payload.qty
        final_price = 0
        opposite_order_direction = models.DirectionsOrders.BUY if payload.direction == models.DirectionsOrders.SELL else payload.direction

        currency_orders_quantity = db.query(func.sum(models.Order.quantity - models.Order.filled_quantity)).filter(models.Order.direction == opposite_order_direction)
        if need_quantity > currency_orders_quantity:
            raise HTTPException(status_code=400, detail='В данный момент в стакане нет столько валюты, сколько вы хотите купить.')
        
        if payload.direction == models.DirectionsOrders.BUY:
            orders = db.query(models.Order).filter(
                models.Order.direction == opposite_order_direction
            ).order_by(models.Order.price.asc()).all()
        else:
            orders = db.query(models.Order).filter(
                models.Order.direction == opposite_order_direction
            ).order_by(models.Order.price.desc()).all()

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
                raise HTTPException(status_code=400, detail='На счету пользователя недостаточно денег для закрытия заказа')
            
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
        'ticker': 'Sosal mne?'
    }