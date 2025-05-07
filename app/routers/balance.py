from fastapi import APIRouter, Depends
from ..database import get_db
from sqlalchemy.orm import Session
from .. import models, schemas, oauth2

router = APIRouter()


@router.get('/')
def get_me(db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user))->schemas.BalancePrintResponse:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    answer = {}
    for coin in user.balance:
        instrument = db.query(models.Instrument).filter(models.Instrument.id == coin.instrument_id).first()
        answer[instrument.ticker] = coin.amount - coin.locked
    return answer
