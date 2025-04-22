#type: ignore
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from sqlalchemy import and_

def deposit_balance(db:Session, user_id:str, instrument_id:str, amount:float):
    balance_instance = db.query(models.Balance).filter(and_(models.Balance.user_id == user_id, models.Balance.instrument_id == instrument_id)).first()
    if balance_instance:
        balance_instance.amount += amount
        db.commit()
        db.refresh(balance_instance)
    else:
        new_balance_instance = models.Balance(user_id=user_id, instrument_id=instrument_id, amount=amount)
        db.add(new_balance_instance)
        db.commit()
        db.refresh(new_balance_instance)


def withdraw_balance(db:Session, user_id:str, instrument_id:str, amount:float):
    balance_instance = db.query(models.Balance).filter(and_(models.Balance.user_id == user_id, models.Balance.instrument_id == instrument_id)).first()
    if balance_instance:
        balance_instance.amount -= amount

        if balance_instance.amount == 0:
            db.delete(balance_instance)
            db.commit()
        elif balance_instance.amount < 0:
            raise HTTPException(status_code=400, detail='Баланс не может опустится ниже 0!')
        else:
            db.commit()
            db.refresh(balance_instance)
        return {
            'success': True
        }
    raise HTTPException(status_code=400, detail='Невозможно снять того, чего нету!')


def check_rub_balance(db:Session, user_id:str):
    rub_instrument = db.query(models.Instrument).filter(models.Instrument.ticker=="RUB").first()

    if not rub_instrument:
        raise HTTPException(status_code=404, detail='В системе отсутствуют рубли!')
    
    user = db.query(models.User).filter(models.User.id==user_id).first()
    try:
        for balance in user.balance:
            if balance.instrument_id == rub_instrument.id:
                return balance.amount
    except:
        return 0


def order_processing(db:Session, order:models.Order):
    if order.direction == models.DirectionsOrders.SELL:
        opposite_orders = db.query(models.Order).filter(
            models.Order.direction == models.DirectionsOrders.BUY
        ).filter(models.Order.price >= order.price).all() 
    else:
        opposite_orders = db.query(models.Order).filter(
            models.Order.direction == models.DirectionsOrders.SELL
        ).filter(models.Order.price <= order.price).all()
    
    for another_order in opposite_orders:
        order = db.refresh(order)
        if order.filled:
            print("FILLED ON FULL")
            break
        if order.direction == models.DirectionsOrders.BUY:
            making_a_deal(order, another_order, db)
        else:
            making_a_deal(another_order, order, db)


def making_a_deal(buy_order:models.Order, sell_order:models.Order, db:Session):
    buyer_query = db.query(models.User).filter(id==buy_order.user_id)
    seller_query = db.query(models.User).filter(id==sell_order.user_id)

    buyer = buyer_query.first()
    seller = seller_query.first()

    buy_quantity = buy_order.quantity - buy_order.filled_quantity
    sell_quantity = sell_order.quantity - sell_order.filled_quantity

    if buy_quantity > sell_quantity:
        final_quantity = sell_quantity
        sell_order.filled = True
    elif buy_quantity < sell_quantity:
        final_quantity = buy_quantity
        buy_order.filled = True
    else:
        buy_order.filled = True
        sell_order.filled = True
        final_quantity = buy_quantity  
    
    withdraw_balance(db, buyer.id, 'RUB', sell_order.price * final_quantity)
    deposit_balance(db, seller.id, 'RUB', sell_order.price * final_quantity)

    buy_order.filled_quantity += final_quantity
    sell_order.filled_quantity += final_quantity

    deposit_balance(db, buyer.id, buy_order.instrument.ticker, final_quantity)
    withdraw_balance(db, seller.id, buy_order.instrument.ticker, final_quantity)

    db.commit()
    db.refresh()
    pass