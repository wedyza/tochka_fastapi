#type: ignore
from fastapi import APIRouter, Request, Response, status, Depends, HTTPException
from sqlalchemy import and_, or_
from .. import schemas, models, utils
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings
router = APIRouter()
from ..oauth2 import create_access_token
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
async def register(payload: schemas.CreateUserSchema, response: Response, db: Session = Depends(get_db)):
    # Check if user already exist
    user = db.query(models.User).filter(
        and_(models.User.name == payload.name.lower(), models.User.deleted_at == None)
    ).first()
    if user:
        new_user = user
    else:
        new_user = models.User(**payload.model_dump())
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    access_token = create_access_token({"user_id": str(new_user.id)})
    
    return {
        'id': new_user.id,
        'name': new_user.name,
        'role': new_user.role,
        'api_key': access_token
    }

@router.get('/instrument')
async def list_instruments(db: Session = Depends(get_db))->list[schemas.InstrumentResponse]:
    list_of_instruments = db.query(models.Instrument).filter(models.Instrument.deleted_at == None).all()
    return list_of_instruments


@router.get('/orderbook/{ticker}')
async def get_orderbook(ticker:str, limit = 10, db: Session = Depends(get_db)):
    return f"{ticker} orderbook {limit}"


@router.get('/transactions/{ticker}')
async def get_transaction_history(ticker:str, limit = 10, db: Session = Depends(get_db)):
    return f"{ticker} transactions {limit}"


# @router.post('/login')
# def login(payload: schemas.LoginUserSchema, response: Response, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
#     # Check if the user exist
#     user = db.query(models.User).filter(
#         models.User.email == payload.email.lower()
#     ).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail='Incorrect Email or Password')

#     # Check if user verified his email
#     if not user.verified:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                             detail='Please verify your email address')

#     # Check if the password is valid
#     if not utils.verify_password(payload.password, user.password):
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail='Incorrect Email or Password')

#     # Create access token
#     access_token = Authorize.create_access_token(
#         subject=str(user.id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

#     # Create refresh token
#     refresh_token = Authorize.create_refresh_token(
#         subject=str(user.id), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

#     # Store refresh and access tokens in cookie
#     response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
#                         ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
#     response.set_cookie('refresh_token', refresh_token,
#                         REFRESH_TOKEN_EXPIRES_IN * 60, REFRESH_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
#     response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
#                         ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')

#     # Send both access
#     return {'status': 'success', 'access_token': access_token}


# @router.get('/refresh')
# def refresh_token(response: Response, request: Request, Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
#     try:
#         print(Authorize._refresh_cookie_key)
#         Authorize.jwt_refresh_token_required()

#         user_id = Authorize.get_jwt_subject()
#         if not user_id:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                                 detail='Could not refresh access token')
#         user = db.query(models.User).filter(models.User.id == user_id).first()
#         if not user:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
#                                 detail='The user belonging to this token no logger exist')
#         access_token = Authorize.create_access_token(
#             subject=str(user.id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
#     except Exception as e:
#         error = e.__class__.__name__
#         if error == 'MissingTokenError':
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail=error)

#     response.set_cookie('access_token', access_token, ACCESS_TOKEN_EXPIRES_IN * 60,
#                         ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, True, 'lax')
#     response.set_cookie('logged_in', 'True', ACCESS_TOKEN_EXPIRES_IN * 60,
#                         ACCESS_TOKEN_EXPIRES_IN * 60, '/', None, False, False, 'lax')
#     return {'access_token': access_token}


# @router.get('/logout', status_code=status.HTTP_200_OK)
# def logout(response: Response, Authorize: AuthJWT = Depends(), user_id: str = Depends(oauth2.require_user)):
#     Authorize.unset_jwt_cookies()
#     response.set_cookie('logged_in', '', -1)

#     return {'status': 'success'}

