# type: ignore
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from sqlalchemy import and_, func, text
from .database import get_db


def market_order_processing(db:Session, order:models.Order, user_rub_balance:float):
    # need_quantity = order.quantity
    final_price = 0
    opposite_order_direction = (
        models.DirectionsOrders.BUY
        if order.direction == models.DirectionsOrders.SELL
        else models.DirectionsOrders.SELL
    )

    if order.direction == models.DirectionsOrders.BUY:
        orders = (
            db.query(models.Order)
            .filter(
                and_(
                    models.Order.direction == models.DirectionsOrders.SELL,
                    models.Order.deleted_at == None,
                    models.Order.status != models.StatusOrders.EXECUTED,
                    models.Order.status != models.StatusOrders.CANCELLED,
                    models.Order.instrument_id == order.instrument_id,
                )
            )
            .order_by(models.Order.price.asc(), models.Order.created_at.asc())
            .with_for_update(of=models.Order)
            .all()
        )
    else:
        orders = (
            db.query(models.Order)
            .filter(
                and_(
                    models.Order.direction == models.DirectionsOrders.BUY,
                    models.Order.deleted_at == None,
                    models.Order.status != models.StatusOrders.EXECUTED,
                    models.Order.status != models.StatusOrders.CANCELLED,
                    models.Order.instrument_id == order.instrument_id,
                )
            )
            .order_by(models.Order.price.desc(), models.Order.created_at.asc())
            .with_for_update(of=models.Order)
            .all()
        )
    # print(orders[0].filled)
    stocked_orders = list()
    order_local_filled = 0

    for another_order in orders:
        local_need_quantity = another_order.quantity - another_order.filled
        if order_local_filled + local_need_quantity > order.quantity:
            if order.direction == models.DirectionsOrders.BUY and (final_price + (order.quantity - order_local_filled) * another_order.price) > user_rub_balance:
                raise HTTPException(status_code=424, detail='На счету пользователя недостаточно денег для закрытия заказа')
            order_local_filled = order.quantity
            stocked_orders.append(another_order)
            break

        final_price += local_need_quantity * another_order.price
        stocked_orders.append(another_order)

        if (
            order.direction == models.DirectionsOrders.BUY
            and final_price > user_rub_balance
        ):
            raise HTTPException(status_code=424, detail='На счету пользователя недостаточно денег для закрытия заказа')
        
        order_local_filled += local_need_quantity
        if order_local_filled == order.quantity:
            break
    
    # print(order_local_filled)
    # print(orders)
    if order_local_filled < order.quantity:
        raise HTTPException(status_code=423, detail='В данный момент в стакане нет столько валюты, сколько вы хотите обменять.') # Надо переделать так, чтобы коммиты срабатывали в нужных местах, а не повсюду, либо протестить поведение при наличии коммитов повсюду (можно еще попробовать создавать новые сессии, хз)
    # db.add(order)
    # db.commit()
    # db.refresh(order)

    for another_order in stocked_orders:
        if another_order.status == models.StatusOrders.CANCELLED or another_order.status == models.StatusOrders.EXECUTED:
            market_order_processing()
        if order.direction == models.DirectionsOrders.BUY:
            making_a_deal(order, another_order, db)
        else:
            making_a_deal(another_order, order, db)
    
    return order


def deposit_balance(db: Session, user_id: str, instrument_id: str, amount: float):
    db = next(get_db())
    balance_instance = (
        db.query(models.Balance)
        .filter(
            and_(
                models.Balance.user_id == user_id,
                models.Balance.instrument_id == instrument_id,
            )
        )
        .first()
    )
    if not balance_instance is None:
        balance_instance.amount += amount
        # db.commit()
        # db.refresh(balance_instance)
    else:
        new_balance_instance = models.Balance(
            user_id=user_id, instrument_id=instrument_id, amount=amount
        )
        db.add(new_balance_instance)
        # db.commit()
        # db.refresh(new_balance_instance)


def withdraw_balance(db: Session, user_id: str, instrument_id: str, amount: float):
    db = next(get_db())
    balance_instance = (
        db.query(models.Balance)
        .filter(
            and_(
                models.Balance.user_id == user_id,
                models.Balance.instrument_id == instrument_id,
            )
        )
        .first()
    )
    if not balance_instance is None:
        balance_instance.amount -= amount
        if balance_instance.amount == 0:
            db.delete(balance_instance)
            # db.commit()
        elif balance_instance.amount < 0:
            raise HTTPException(
                status_code=410, detail="Баланс не может опустится ниже 0!"
            )
        # else:
            # db.commit()
            # db.refresh(balance_instance)
        return {"success": True}
    raise HTTPException(status_code=411, detail="Невозможно снять того, чего нету!")


def unlock_custom_balance(db: Session, user_id: str, amount: int, instrument_id: str):
    db = next(get_db())
    rub_instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.id == instrument_id,
                models.Instrument.deleted_at == None,
            )
        )
        .first()
    )

    if rub_instrument is None:
        raise HTTPException(
            status_code=412, detail="В системе отсутствует нужная валюта!"
        )

    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id)
        .filter(models.Balance.instrument_id == instrument_id)
        .first()
    )
    if balance is not None:
        balance.locked -= amount


def lock_custom_balance(db: Session, user_id: str, amount: int, instrument_id: str):
    db = next(get_db())
    rub_instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.id == instrument_id,
                models.Instrument.deleted_at == None,
            )
        )
        .first()
    )

    if rub_instrument is None:
        raise HTTPException(
            status_code=413, detail="В системе отсутствует нужная валюта!"
        )

    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id)
        .filter(models.Balance.instrument_id == instrument_id)
        .first()
    )

    if balance is not None:
        balance.locked += amount


def check_custom_balance(db: Session, user_id: str, ticker: str):
    db = next(get_db())
    custom_instrument = (
        db.query(models.Instrument)
        .filter(models.Instrument.ticker == ticker)
        .filter(models.Instrument.deleted_at == None)
        .first()
    )

    if custom_instrument is None:
        raise HTTPException(
            status_code=404, detail="В системе отсутствуют данный инструмент!"
        )

    balance = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id)
        .filter(models.Balance.instrument_id == custom_instrument.id)
        .first()
    )
    if balance is None:
        return 0
    return balance.amount - balance.locked


def order_processing(db: Session, order: models.Order):
    db.add(order)
    db.commit()
    db.refresh(order)

    rub_instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.deleted_at == None, models.Instrument.ticker == "RUB"
            )
        )
        .first()
    )
    if order.direction == models.DirectionsOrders.SELL:
        lock_custom_balance(db, order.user_id, order.quantity, order.instrument_id)
        db.commit()
        opposite_orders = (
            db.query(models.Order)
            .filter(
                and_(
                    models.Order.direction == models.DirectionsOrders.BUY,
                    models.Order.status != models.StatusOrders.EXECUTED,
                    models.Order.status != models.StatusOrders.CANCELLED,
                )
            )
            .filter(models.Order.price >= order.price)
            .filter(models.Order.instrument_id == order.instrument_id)
            .with_for_update(of=models.Order)
            .order_by(models.Order.created_at.asc())
            .all()
        )
    else:
        lock_custom_balance(
            db, order.user_id, order.quantity * order.price, rub_instrument.id
        )
        db.commit()
        opposite_orders = (
            db.query(models.Order)
            .filter(
                and_(
                    models.Order.direction == models.DirectionsOrders.SELL,
                    models.Order.status != models.StatusOrders.EXECUTED,
                    models.Order.status != models.StatusOrders.CANCELLED,
                )
            )
            .filter(models.Order.price <= order.price)
            .filter(models.Order.instrument_id == order.instrument_id)
            .with_for_update(of=models.Order)
            .order_by(models.Order.created_at.asc())
            .all()
        )

    for another_order in opposite_orders:
        if order.direction == models.DirectionsOrders.BUY:
            making_a_deal(order, another_order, db)
        else:
            making_a_deal(another_order, order, db)


def making_a_deal(buy_order: models.Order, sell_order: models.Order, db: Session):
    buyer = db.query(models.User).filter(models.User.id == buy_order.user_id).first()
    seller = db.query(models.User).filter(models.User.id == sell_order.user_id).first()


    buy_quantity = buy_order.quantity - buy_order.filled
    sell_quantity = sell_order.quantity - sell_order.filled
    
    final_quantity = min(buy_quantity, sell_quantity)

    buy_instrument = (
        db.query(models.Instrument)
        .filter(
            and_(
                models.Instrument.deleted_at == None, models.Instrument.ticker == "RUB"
            )
        )
        .first()
    )

    if sell_order.price is None:
        final_price = buy_order.price * final_quantity
        transaction_price = buy_order.price
    else:
        final_price = sell_order.price * final_quantity
        transaction_price = sell_order.price

    if not buy_order.price is None:
        unlock_custom_balance(db, buyer.id, final_price, buy_instrument.id)
    withdraw_balance(db, buyer.id, buy_instrument.id, final_price)
    deposit_balance(db, seller.id, buy_instrument.id, final_price)

    if buy_order.filled + final_quantity > buy_order.quantity or sell_order.filled + final_quantity > sell_order.quantity:
        print("failed on filled > quantity | END")
        print(f"{buy_order.id} | {buy_order.quantity} - {buy_order.filled} => buy quantity")
        print(f"{sell_order.id} | {sell_order.quantity} - {sell_order.filled} => sell quantity")
        print(f"final quantity - {final_quantity}")

    buy_order.filled += final_quantity
    sell_order.filled += final_quantity

    if not sell_order.price is None:
        unlock_custom_balance(db, seller.id, final_quantity, sell_order.instrument_id)
    deposit_balance(db, buyer.id, buy_order.instrument_id, final_quantity)
    withdraw_balance(db, seller.id, buy_order.instrument_id, final_quantity)


    if buy_order.filled == buy_order.quantity:
        buy_order.status = models.StatusOrders.EXECUTED
    else:
        buy_order.status = models.StatusOrders.PARTIALLY_EXECUTED

    if sell_order.filled == sell_order.quantity:
        sell_order.status = models.StatusOrders.EXECUTED
    else:
        sell_order.status = models.StatusOrders.PARTIALLY_EXECUTED

    transaction = models.Transaction(instrument_id = sell_order.instrument_id, amount=final_quantity, price=transaction_price)

    if sell_order.id is None:
        db.add(sell_order)
    if buy_order.id is None:
        db.add(buy_order)
    db.add(transaction)
    db.commit()
    db.refresh(buy_order)
    db.refresh(sell_order)
    db.refresh(transaction)