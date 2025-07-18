#type: ignore

from fastapi import APIRouter, Depends, status, HTTPException
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2, functions
from sqlalchemy import or_, and_, text

router = APIRouter()


@router.delete('/user/{user_id}')
def delete_user(user_id: str, db: Session = Depends(get_db), admin_id: str = Depends(oauth2.require_admin))->schemas.DeleteResponse:
    user = db.query(models.User).filter(
        and_(models.User.id == user_id, models.User.deleted_at == None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail='Пользователь с таким ID не найден!')
    user.deleted_at = text('now()')
    db.commit()
    db.refresh(user)
    return {
        'success': True
    }


@router.post('/instrument', response_model=schemas.InstrumentResponse, status_code=status.HTTP_201_CREATED)
def add_instrument(payload: schemas.InstrumentCreateSchema, db: Session = Depends(get_db)):
    instrument = db.query(models.Instrument).filter(or_(
        models.Instrument.name == payload.name.lower(), models.Instrument.ticker == payload.ticker, models.Instrument.deleted_at == None
    )).first()
    if instrument:
        raise HTTPException(status_code=400, detail='Инструмент с одним из этих показателей уже существует!')
    new_instrument = models.Instrument(**payload.model_dump())
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
    db.commit()
    db.refresh(instrument)

    
    return {
        'success': True
    }



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


@router.post('/balance/withdraw', response_model=schemas.BalanceResponse)
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