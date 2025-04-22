import base64
from typing import List
from fastapi import Depends, HTTPException, status, Header
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from . import models
from .database import get_db
from sqlalchemy.orm import Session
from .config import settings
import traceback
from jose import JWTError, jwt
import uuid

SECRET_KEY = "somereallyhard123456password"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# class Settings(BaseModel):
#     authjwt_algorithm: str = settings.JWT_ALGORITHM
#     authjwt_decode_algorithms: List[str] = [settings.JWT_ALGORITHM]
#     authjwt_token_location: set = {'cookies', 'headers'}
#     authjwt_access_cookie_key: str = 'access_token'
#     authjwt_refresh_cookie_key: str = 'refresh_token'
#     authjwt_public_key: str = base64.b64decode(
#         settings.JWT_PUBLIC_KEY).decode('utf-8')
#     authjwt_private_key: str = base64.b64decode(
#         settings.JWT_PRIVATE_KEY).decode('utf-8')


# @AuthJWT.load_config
# def get_config():
#     return Settings()

def create_access_token(data):
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class NotVerified(Exception):
    pass


class UserNotFound(Exception):
    pass

class UserNotAdmin(Exception):
    pass

def require_user(db: Session = Depends(get_db), Authorization: str = Header()): #authorization es che
    try:
        token = Authorization.split(' ')[1]
        user_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = uuid.UUID(user_id['user_id'])
        user = db.query(models.User).filter(models.User.id == user_id).first()
        
        if not user:
            raise UserNotFound('User no longer exist')

    except Exception as e:
        error = e.__class__.__name__
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='You are not logged in')
        if error == 'UserNotFound':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='User no longer exist')
        if error == 'NotVerified':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Please verify your account')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is invalid or has expired')
    return user_id


def require_admin(db: Session = Depends(get_db), Authorization: str = Header()):
    try:
        token = Authorization.split(' ')[1]
        user_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = uuid.UUID(user_id['user_id'])
        user = db.query(models.User).filter(models.User.id == user_id).first()

        if not user:
            raise UserNotFound('User no longer exist')
        
        if user.role != models.UserRole.ADMIN:
            raise UserNotAdmin('User is not admin')

    except Exception as e:
        error = e.__class__.__name__
        print(traceback.format_exc())
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='You are not logged in')
        if error == 'UserNotFound':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='User no longer exist')
        if error == 'NotVerified':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Please verify your account')
        if error == 'UserNotAdmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to do this'
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is invalid or has expired')
    return user_id