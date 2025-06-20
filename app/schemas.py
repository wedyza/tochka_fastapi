from datetime import datetime
from typing import List
import uuid
from pydantic import (
    BaseModel,
    field_validator,
    Field,
    computed_field,
)
import re
from typing import Dict, Optional
import pydantic
from .models import DirectionsOrders, StatusOrders


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


class InstrumentBase(BaseModel):
    name: str
    ticker: str

    class Config:
        orm_mode = True

    @field_validator("ticker")
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError("Invalid ticker format!")
        return v


class InstrumentResponse(InstrumentBase):
    pass


class InstrumentCreateSchema(InstrumentBase):
    pass


class BalanceInput(BaseModel):
    user_id: uuid.UUID
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


class OrderCreateInput(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int
    price: Optional[int] = 0

    @field_validator("ticker")
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError("Invalid ticker format!")
        return v


class MarketOrderCreateInput(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int

    @field_validator("ticker")
    def validate_ticker(cls, v):
        reg_exp = r"^[A-Z]{2,10}$"
        if re.match(reg_exp, v) is None:
            raise ValueError("Invalid ticker format!")
        return v


class OrderCreateOutput(BaseModel):
    ticker: str
    order_id: uuid.UUID


class OrderInOrderbook(BaseModel):
    price: int
    quantity: int = Field(..., exclude=True)
    filled: int = Field(..., exclude=True)

    @computed_field
    def qty(self) -> int:
        return self.quantity - self.filled


class OrderbookResponse(BaseModel):
    bid_levels: Optional[List[OrderInOrderbook]] = []
    ask_levels: Optional[List[OrderInOrderbook]] = []


class OrderBodyWithoutPrice(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int


class OrderBody(BaseModel):
    direction: DirectionsOrders
    ticker: str
    qty: int
    price: Optional[float]


class OrdersResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    timestamp: datetime
    body: OrderBody | OrderBodyWithoutPrice
    filled: int
    status: StatusOrders


class TransactionsResponse(BaseModel):
    ticker: str
    timestamp: datetime
    amount: int
    price: float