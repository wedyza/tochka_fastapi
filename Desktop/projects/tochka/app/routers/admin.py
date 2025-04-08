from fastapi import APIRouter, Depends, status, HTTPException
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, functions
from sqlalchemy import or_, and_

router = APIRouter()


@router.delete('/user/{user_id}')
def delete_user(user_id: str, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')
    db.delete(user)
    db.commit()
    return 'Done.'


@router.post('/instrument', response_model=schemas.InstrumentResponse, status_code=status.HTTP_201_CREATED)
def add_instrument(payload: schemas.InstrumentCreateSchema, db: Session = Depends(get_db)):
    instrument = db.query(models.Instrument).filter(or_(
        models.Instrument.name == payload.name.lower(), models.Instrument.ticker == payload.ticker
    )).first()
    if instrument:
        raise HTTPException(status_code=400, detail='Инструмент с одним из этих показателей уже существует!')
    new_instrument = models.Instrument(**payload.model_dump())
    db.add(new_instrument)
    db.commit()
    db.refresh(new_instrument)
    return new_instrument

@router.delete('/instrument/{ticker}')
def delete_instrument(ticker: str, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == ticker).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')
    
    db.delete(instrument)
    db.commit()
    
    return 'Done.'


@router.post('/balance/deposit', response_model=schemas.BalanceResponse)
def deposit(payload:schemas.BalanceInput, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')

    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == payload.ticker).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')

    functions.deposit_balance(db, user_id=user.id, instrument_id=instrument.id, amount=payload.amount)

    return {
        'success': True
    }


@router.post('/balance/withdraw')
def withdraw(payload:schemas.BalanceInput, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')

    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == payload.ticker).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')

    functions.withdraw_balance(db, user_id=user.id, instrument_id=instrument.id, amount=payload.amount)

    return {
        'success': True
    }