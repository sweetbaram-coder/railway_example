from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional
from urllib.parse import quote

from database import init_db, get_session
from models import Reservation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 테이블 초기화
    init_db()
    yield

app = FastAPI(title="사내 회의실 예약 시스템", lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

# 회의실 목록 및 운영 시간대 설정 (09:00 ~ 18:00 서비스 운영)
ROOMS = ["대회의실", "미팅룸A", "미팅룸B", "포커스룸"]
HOURS = list(range(9, 18))  # [9, 10, 11, 12, 13, 14, 15, 16, 17]

@app.get("/", response_class=HTMLResponse)
def read_root(
    request: Request,
    error: Optional[str] = None,
    success: Optional[str] = None,
    session: Session = Depends(get_session)
):
    # 전체 예약 조회
    reservations = session.exec(select(Reservation)).all()
    
    # 시간표 그리드용 구조화: timetable[room_name][hour] = reservation 객체 또는 None
    timetable = {room: {hour: None for hour in HOURS} for room in ROOMS}
    for res in reservations:
        if res.room_name in timetable and res.start_time in timetable[res.room_name]:
            timetable[res.room_name][res.start_time] = res

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "rooms": ROOMS,
            "hours": HOURS,
            "timetable": timetable,
            "error": error,
            "success": success,
        }
    )

@app.post("/reserve")
def create_reservation(
    reserver_name: str = Form(...),
    room_name: str = Form(...),
    start_time: int = Form(...),
    session: Session = Depends(get_session)
):
    name_clean = reserver_name.strip()
    if not name_clean:
        return RedirectResponse(url=f"/?error={quote('예약자 이름을 입력해주세요.')}", status_code=status.HTTP_303_SEE_OTHER)
    
    if room_name not in ROOMS:
        return RedirectResponse(url=f"/?error={quote('유효하지 않은 회의실입니다.')}", status_code=status.HTTP_303_SEE_OTHER)

    if start_time < 9 or start_time >= 18:
        return RedirectResponse(url=f"/?error={quote('예약 가능한 시간은 09:00 ~ 18:00 사이입니다.')}", status_code=status.HTTP_303_SEE_OTHER)

    # 중복 예약 검증
    existing = session.exec(
        select(Reservation).where(
            Reservation.room_name == room_name,
            Reservation.start_time == start_time
        )
    ).first()

    if existing:
        msg = f"[{room_name}] {start_time}:00~{start_time+1}:00 시간대는 이미 '{existing.reserver_name}' 님이 예약하셨습니다."
        return RedirectResponse(url=f"/?error={quote(msg)}", status_code=status.HTTP_303_SEE_OTHER)

    end_time = start_time + 1
    new_res = Reservation(
        reserver_name=name_clean,
        room_name=room_name,
        start_time=start_time,
        end_time=end_time
    )
    session.add(new_res)
    session.commit()

    success_msg = f"{room_name} ({start_time:02d}:00~{end_time:02d}:00) 예약이 완료되었습니다."
    return RedirectResponse(url=f"/?success={quote(success_msg)}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/cancel/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    session: Session = Depends(get_session)
):
    res = session.get(Reservation, reservation_id)
    if res:
        info = f"{res.room_name} ({res.start_time:02d}:00~{res.end_time:02d}:00, {res.reserver_name}님) 예약이 취소되었습니다."
        session.delete(res)
        session.commit()
        return RedirectResponse(url=f"/?success={quote(info)}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=f"/?error={quote('해당 예약을 찾을 수 없습니다.')}", status_code=status.HTTP_303_SEE_OTHER)
