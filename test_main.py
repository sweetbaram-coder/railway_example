import pytest
from fastapi.testclient import TestClient
from main import app, ROOMS, HOURS
from database import init_db

from sqlmodel import SQLModel
from database import engine

@pytest.fixture(autouse=True)
def setup_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

def test_meeting_room_reservation_flow():
    client = TestClient(app, follow_redirects=False)

    # 1. 메인 현황판 GET 요청
    response = client.get("/")
    assert response.status_code == 200
    assert "사내 회의실 예약 시스템" in response.text
    for room in ROOMS:
        assert room in response.text

    # 2. 신규 예약 등록 (홍길동, 대회의실, 10시)
    reserve_data = {
        "reserver_name": "홍길동",
        "room_name": "대회의실",
        "start_time": 10
    }
    res = client.post("/reserve", data=reserve_data)
    assert res.status_code == 303
    assert "success" in res.headers["location"]

    # 3. 메인 현황판 조회 시 '홍길동' 포함 확인
    res_main = client.get("/")
    assert res_main.status_code == 200
    assert "홍길동" in res_main.text

    # 4. 중복 예약 시도 (김철수, 대회의실, 10시) -> 실패 검증
    dup_data = {
        "reserver_name": "김철수",
        "room_name": "대회의실",
        "start_time": 10
    }
    res_dup = client.post("/reserve", data=dup_data)
    assert res_dup.status_code == 303
    assert "error" in res_dup.headers["location"]

    # 5. 다른 시간/다른 회의실 정상 예약 (이순신, 미팅룸A, 14시)
    other_data = {
        "reserver_name": "이순신",
        "room_name": "미팅룸A",
        "start_time": 14
    }
    res_other = client.post("/reserve", data=other_data)
    assert res_other.status_code == 303
    assert "success" in res_other.headers["location"]

    # 6. 예약 취소 테스트
    # DB에서 reservation id 확인 후 취소
    from sqlmodel import Session, select
    from database import engine
    from models import Reservation

    with Session(engine) as session:
        hgd_res = session.exec(select(Reservation).where(Reservation.reserver_name == "홍길동")).first()
        assert hgd_res is not None
        hgd_id = hgd_res.id

    cancel_res = client.post(f"/cancel/{hgd_id}")
    assert cancel_res.status_code == 303
    assert "success" in cancel_res.headers["location"]

    # 7. 예약 취소 후 메시지 및 현황판 갱신 확인
    res_after_cancel = client.get(cancel_res.headers["location"])
    assert "예약이 취소되었습니다" in res_after_cancel.text

    # DB에서 홍길동 예약이 완전히 제거되었는지 검증
    with Session(engine) as session:
        cancelled_hgd = session.exec(select(Reservation).where(Reservation.reserver_name == "홍길동")).first()
        assert cancelled_hgd is None

    print("\n✅ 모든 비즈니스 로직 및 통합 테스트 통과!")
