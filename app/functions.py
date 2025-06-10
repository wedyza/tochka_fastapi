#type: ignore
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from sqlalchemy import and_

def deposit_balance(db:Session, user_id:str, instrument_id:str, amount:float):
    balance_instance = db.query(models.Balance).filter(and_(models.Balance.user_id == user_id, models.Balance.instrument_id == instrument_id)).first()
    # print(f"trying to deposit - {balance_instance}")
    # print(f"user_id = {user_id}, instrument_id - {instrument_id}")
    if not balance_instance is None:
        # print("successful += ")
        balance_instance.amount += amount
        db.commit()
        db.refresh(balance_instance)
    else:
        # print("successful created new one")
        new_balance_instance = models.Balance(user_id=user_id, instrument_id=instrument_id, amount=amount)
        db.add(new_balance_instance)
        db.commit()
        db.refresh(new_balance_instance)


def withdraw_balance(db:Session, user_id:str, instrument_id:str, amount:float):
    balance_instance = db.query(models.Balance).filter(and_(models.Balance.user_id == user_id, models.Balance.instrument_id == instrument_id)).first()
    # print(f"trying to withdraw - {balance_instance}")
    # print(f"user_id = {user_id}, instrument_id - {instrument_id}")
    if not balance_instance is None:
        # print("successful")
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
    # print("error")
    raise HTTPException(status_code=400, detail='Невозможно снять того, чего нету!')


def unlock_custom_balance(db:Session, user_id:str, amount:int, instrument_id: str):
    rub_instrument = db.query(models.Instrument).filter(and_(models.Instrument.id==instrument_id, models.Instrument.deleted_at == None)).first()
    
    if not rub_instrument:
        raise HTTPException(status_code=404, detail='В системе отсутствует нужная валюта!')

    user = db.query(models.User).filter(models.User.id==user_id).first()
    for balance in user.balance:
        if balance.instrument_id == rub_instrument.id:
            balance.locked -= amount
            break
    
    db.commit()
    db.refresh(balance)



def lock_custom_balance(db:Session, user_id:str, amount:int, instrument_id: str):
    rub_instrument = db.query(models.Instrument).filter(and_(models.Instrument.id==instrument_id, models.Instrument.deleted_at == None)).first()
    
    if not rub_instrument:
        raise HTTPException(status_code=404, detail='В системе отсутствует нужная валюта!')

    user = db.query(models.User).filter(models.User.id==user_id).first()
    for balance in user.balance:
        if balance.instrument_id == rub_instrument.id:
            balance.locked = amount
            break
    
    db.commit()
    db.refresh(balance)


def check_custom_balance(db:Session, user_id:str, ticker: str):
    custom_instrument = db.query(models.Instrument).filter(models.Instrument.ticker==ticker).filter(models.Instrument.deleted_at == None).first()

    if not custom_instrument:
        raise HTTPException(status_code=404, detail='В системе отсутствуют данный инструмент!')
    
    user = db.query(models.User).filter(models.User.id==user_id).first()
    try:
        for balance in user.balance:
            if balance.instrument_id == custom_instrument.id:
                return balance.amount - balance.locked
        return 0
    except:
        return 0


def order_processing(db:Session, order:models.Order):
    db.add(order)
    db.commit()
    db.refresh(order)

    rub_instrument = db.query(models.Instrument).filter(and_(models.Instrument.deleted_at == None, models.Instrument.ticker == 'RUB')).first()
    if order.direction == models.DirectionsOrders.SELL:
        lock_custom_balance(db, order.user_id, order.quantity, order.instrument.id)
        opposite_orders = db.query(models.Order).filter(and_(
            models.Order.direction == models.DirectionsOrders.BUY, models.Order.filled == False
        )).filter(models.Order.price >= order.price).all() 
    else:
        lock_custom_balance(db, order.user_id, order.quantity * order.price, rub_instrument.id)
        opposite_orders = db.query(models.Order).filter(and_(
            models.Order.direction == models.DirectionsOrders.SELL, models.Order.filled == False
        )).filter(models.Order.price <= order.price).all()
    
    for another_order in opposite_orders:
        order = db.query(models.Order).filter(models.Order.id == order.id).first()
        if order.filled:
            # print("FILLED ON FULL")
            return
        if order.direction == models.DirectionsOrders.BUY:
            making_a_deal(order, another_order, db)
        else:
            making_a_deal(another_order, order, db)
    


def making_a_deal(buy_order:models.Order, sell_order:models.Order, db:Session):
    buyer_query = db.query(models.User).filter(models.User.id==buy_order.user_id)
    seller_query = db.query(models.User).filter(models.User.id==sell_order.user_id)

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
    
    buy_instrument = db.query(models.Instrument).filter(and_(models.Instrument.deleted_at == None, models.Instrument.ticker == 'RUB')).first()

    if sell_order.price is None:
        final_price = buy_order.price * final_quantity
    else:
        final_price = sell_order.price * final_quantity
    
    withdraw_balance(db, buyer.id, buy_instrument.id, final_price)
    deposit_balance(db, seller.id, buy_instrument.id, final_price)
    unlock_custom_balance(db, buyer.id, final_price, buy_instrument.id)

    buy_order.filled_quantity += final_quantity
    sell_order.filled_quantity += final_quantity

    deposit_balance(db, buyer.id, buy_order.instrument.id, final_quantity)
    withdraw_balance(db, seller.id, buy_order.instrument.id, final_quantity)
    unlock_custom_balance(db, seller.id, final_quantity, sell_order.instrument_id)

    db.commit()
    db.refresh(buy_order)
    db.refresh(sell_order)
