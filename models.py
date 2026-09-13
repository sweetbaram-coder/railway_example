from typing import Optional
from sqlmodel import SQLModel, Field

class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reserver_name: str = Field(index=True)
    room_name: str = Field(index=True)
    start_time: int = Field(description="예약 시작 시간 (9 ~ 17시)")
    end_time: int = Field(description="예약 종료 시간 (start_time + 1)")
