from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, EmailStr, constr, field_validator
import re
from typing import Dict
import pydantic
from .models import DirectionsOrders


class UserBaseSchema(BaseModel):
    name: str
    role: str

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    role: str = "USER"


class UserResponse(UserBaseSchema):
    id: uuid.UUID
    name: str
    role: str
    api_key: str


# class UserBalance(BaseModel):
#     "Ticker1": 123
#     "Ticker2": 123123

class InstrumentBase(BaseModel):
    name: str
    ticker: str

    class Config:
        orm_mode = True

    @field_validator('ticker')
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError('Invalid ticker format!')
        return v

class InstrumentResponse(InstrumentBase):
    pass


class InstrumentCreateSchema(InstrumentBase):
    pass


class BalanceInput(BaseModel):
    user_id: str
    ticker: str
    amount: float


class BalanceResponse(BaseModel):
    success: bool


class DeleteResponse(BaseModel):
    success: bool

class BalancePrintResponse(pydantic.RootModel):
    root: Dict[str, float]

    def __getitem__(self, key: str) -> float:
        return self.__root__[key]
    

class LimitOrderCreateInput(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int
    price: int


    @field_validator('ticker')
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError('Invalid ticker format!')
        return v


class MarketOrderCreateInput(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int


    @field_validator('ticker')
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError('Invalid ticker format!')
        return v


class OrderCreateOutput(BaseModel):
    ticker: str
    success: bool