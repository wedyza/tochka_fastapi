#type: ignore

from fastapi import APIRouter, Depends, status, HTTPException
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, functions
from sqlalchemy import or_, and_, text
from uuid import UUID
router = APIRouter()


@router.delete('/user/{user_id}')
def delete_user(user_id: UUID, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin))->schemas.DeleteResponse:
    user = db.query(models.User).filter(models.User.id == user_id).filter(models.User.deleted_at == None).first()
    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')
    user.deleted_at = text('now()')
    db.commit()
    db.refresh(user)

    db.query(models.Balance).filter(models.Balance.user_id == user_id).delete()
    db.query(models.Order).filter(models.Order.user_id == user_id).update(
        {models.Order.deleted_at: text('now()')}
    )
    return {
        'success': True
    }


@router.post('/instrument', response_model=schemas.InstrumentResponse, status_code=status.HTTP_201_CREATED)
def add_instrument(payload: schemas.InstrumentCreateSchema, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin))->schemas.InstrumentCreateSchema:
    instrument = db.query(models.Instrument).filter(and_(or_(
        models.Instrument.name == payload.name, models.Instrument.ticker == payload.ticker), models.Instrument.deleted_at == None
    )).first()
    if instrument:
        raise HTTPException(status_code=422, detail='Инструмент с одним из этих показателей уже существует!')
    new_instrument = models.Instrument(**payload.model_dump())
    print(f"Создан инструмент - {new_instrument.ticker}")
    db.add(new_instrument)
    db.commit()
    db.refresh(new_instrument)
    return new_instrument

@router.delete('/instrument/{ticker}')
def delete_instrument(ticker: str, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin))->schemas.DeleteResponse:
    instrument = db.query(models.Instrument).filter(
        and_(models.Instrument.ticker == ticker, models.Instrument.deleted_at == None)
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')
    
    instrument.deleted_at = text('now()')

    db.query(models.Balance).filter(models.Balance.instrument_id == instrument.id).delete()
    db.query(models.Order).filter(models.Order.instrument_id == instrument.id).update(
        {models.Order.deleted_at: text('now()')}
    )
    db.commit()
    db.refresh(instrument)

    
    return {
        'success': True
    }



@router.post('/balance/deposit', response_model=schemas.BalanceResponse)
def deposit(payload:schemas.BalanceInput, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).filter(models.User.deleted_at == None).first()
    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')
    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == payload.ticker).filter(models.Instrument.deleted_at == None).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')
    functions.deposit_balance(db, user_id=user.id, instrument_id=instrument.id, amount=payload.amount)

    return {
        'success': True
    }


@router.post('/balance/withdraw', response_model=schemas.BalanceResponse)
def withdraw(payload:schemas.BalanceInput, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).filter(models.User.deleted_at == None).first()
    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')

    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == payload.ticker).first()

    if not instrument:
        raise HTTPException(status_code=404, detail='Не найдено инструмента с таким тикером!')

    functions.withdraw_balance(db, user_id=user.id, instrument_id=instrument.id, amount=payload.amount)

    return {
        'success': True
    }