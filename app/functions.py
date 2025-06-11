# type: ignore
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from sqlalchemy import and_


def deposit_balance(db: Session, user_id: str, instrument_id: str, amount: float):
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
        db.commit()
        db.refresh(balance_instance)
    else:
        new_balance_instance = models.Balance(
            user_id=user_id, instrument_id=instrument_id, amount=amount
        )
        db.add(new_balance_instance)
        db.commit()
        db.refresh(new_balance_instance)


def withdraw_balance(db: Session, user_id: str, instrument_id: str, amount: float):
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
            db.commit()
        elif balance_instance.amount < 0:
            raise HTTPException(
                status_code=410, detail="Баланс не может опустится ниже 0!"
            )
        else:
            db.commit()
            db.refresh(balance_instance)
        return {"success": True}
    # print("error")
    instrument = (
        db.query(models.Instrument)
        .filter(models.Instrument.id == instrument_id)
        .first()
    )
    raise HTTPException(status_code=411, detail="Невозможно снять того, чего нету!")


def unlock_custom_balance(db: Session, user_id: str, amount: int, instrument_id: str):
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
        db.commit()
        db.refresh(balance)
    else:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        print(f"user_id - {user.id}")
        print(f"finding instrument_id - {instrument_id}")
        try:
            for balance in user.balance:
                print(
                    f"user balance - {balance.instrument_id}, amount - {balance.amount}, locked - {balance.locked}"
                )
        except:
            print(user.balance)
        print("balance not found")


def lock_custom_balance(db: Session, user_id: str, amount: int, instrument_id: str):
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
        db.commit()
        db.refresh(balance)
    else:
        print("balance not found")


def check_custom_balance(db: Session, user_id: str, ticker: str):
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
        lock_custom_balance(db, order.user_id, order.quantity, order.instrument.id)
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
            .all()
        )
    else:
        lock_custom_balance(
            db, order.user_id, order.quantity * order.price, rub_instrument.id
        )
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
            .all()
        )

    for another_order in opposite_orders:
        order = db.query(models.Order).filter(models.Order.id == order.id).first()
        if order.status == models.StatusOrders.EXECUTED or order.status == models.StatusOrders.CANCELLED:
            return
        if order.direction == models.DirectionsOrders.BUY:
            making_a_deal(order, another_order, db)
        else:
            making_a_deal(another_order, order, db)


def making_a_deal(buy_order: models.Order, sell_order: models.Order, db: Session):
    buyer = db.query(models.User).filter(models.User.id == buy_order.user_id).first()
    seller = db.query(models.User).filter(models.User.id == sell_order.user_id).first()

    buy_quantity = buy_order.quantity - buy_order.filled
    sell_quantity = sell_order.quantity - sell_order.filled
    if buy_quantity <= 0 or sell_quantity <= 0:
        print(f"{buy_order.quantity} - {buy_order.filled} = {buy_quantity} => buy quantity")
        print(f"{sell_order.quantity} - {sell_order.filled} = {sell_quantity} => sell quantity")
    final_quantity = buy_quantity if buy_quantity <= sell_quantity else sell_quantity
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
    else:
        final_price = sell_order.price * final_quantity

    try:
        if not buy_order.price is None:
            unlock_custom_balance(db, buyer.id, final_price, buy_instrument.id)
        withdraw_balance(db, buyer.id, buy_instrument.id, final_price)
        deposit_balance(db, seller.id, buy_instrument.id, final_price)

        buy_order.filled += final_quantity
        sell_order.filled += final_quantity

        if not sell_order.price is None:
            unlock_custom_balance(db, seller.id, final_quantity, sell_order.instrument_id)
        deposit_balance(db, buyer.id, buy_order.instrument.id, final_quantity)
        withdraw_balance(db, seller.id, buy_order.instrument.id, final_quantity)
        if buy_order.filled == buy_order.quantity:
            buy_order.status = models.StatusOrders.EXECUTED
        else:
            buy_order.status = models.StatusOrders.PARTIALLY_EXECUTED

        if sell_order.filled == sell_order.quantity:
            sell_order.status = models.StatusOrders.EXECUTED
        else:
            sell_order.status = models.StatusOrders.PARTIALLY_EXECUTED

        db.commit()
        db.refresh(buy_order)
        db.refresh(sell_order)
    except Exception as e:
        try:
            print("buyer balance:")
            for b in buyer.balance:
                print(f"{b.instrument_id} - {b.amount}")
        except:
            print('Ничего нет')
        finally:
            print(f"buyer_id - {buyer.id}")
            print(f"seller_id - {seller.id}")
            raise e
