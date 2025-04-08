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