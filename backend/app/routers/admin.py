from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import RpaJob, RpaLog, User
from ..schemas import RoleIn, RpaJobOut, RpaJobUpdateIn, RpaLogOut, UserOut
from ..security import TEST_ADMIN, require_admin, require_admin_read
from ..services import rpa_jobs
from ..services.realtime import manager

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_read)])


@router.get("/users", response_model=list[UserOut])
def list_users(q: str | None = None, db: Session = Depends(get_db)):
    query = select(User).order_by(User.created_at.desc())
    if q:
        query = query.where(User.email.like(f"%{q}%") | User.name.like(f"%{q}%"))
    return db.scalars(query).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_role(user_id: int, data: RoleIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "회원을 찾을 수 없습니다.")
    if user.id == admin.id and data.role != "admin":
        raise HTTPException(400, "자기 자신의 관리자 권한은 해제할 수 없습니다.")
    if user.role == TEST_ADMIN or user.email == settings.test_admin_email:
        raise HTTPException(400, "테스트 관리자 계정의 권한은 변경할 수 없습니다.")
    user.role = data.role
    db.commit()
    manager.update_role(user.id, user.role)
    manager.publish("user.role", {"id": user.id, "role": user.role}, user_id=user.id)
    manager.publish("admin.user_role", {"id": user.id, "name": user.name, "role": user.role}, admin_only=True)
    return user


@router.get("/rpa/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return [{**RpaJobOut.model_validate(j).model_dump(mode="json"), "running": rpa_jobs.is_running(j.name)}
            for j in db.scalars(select(RpaJob).order_by(RpaJob.id)).all()]


@router.patch("/rpa/jobs/{name}", response_model=RpaJobOut)
def update_job(name: str, data: RpaJobUpdateIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    job = db.scalar(select(RpaJob).where(RpaJob.name == name))
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(job, k, v)
    db.commit()
    return job


@router.post("/rpa/jobs/{name}/run", status_code=202)
async def run_job(name: str, _: User = Depends(require_admin)):
    if name not in rpa_jobs.RUNNERS:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    if rpa_jobs.is_running(name):
        raise HTTPException(409, "이미 실행 중인 작업입니다.")
    rpa_jobs.spawn(name, "manual")
    return {"accepted": True, "job": name}


@router.get("/rpa/logs", response_model=list[RpaLogOut])
def list_logs(job: str | None = None, status: str | None = None, limit: int = Query(50, le=500),
              db: Session = Depends(get_db)):
    query = select(RpaLog).order_by(RpaLog.started_at.desc(), RpaLog.id.desc()).limit(limit)
    if job:
        query = query.where(RpaLog.job_name == job)
    if status:
        query = query.where(RpaLog.status == status)
    return db.scalars(query).all()


@router.get("/rpa/stats")
def rpa_stats(db: Session = Depends(get_db)):
    rows = db.execute(select(RpaLog.job_name, RpaLog.status, func.count(RpaLog.id), func.sum(RpaLog.items_count))
                      .group_by(RpaLog.job_name, RpaLog.status)).all()
    stats: dict[str, dict] = {}
    for job, status, count, items in rows:
        s = stats.setdefault(job, {"job": job, "success": 0, "failed": 0, "running": 0, "items": 0})
        s[status] = s.get(status, 0) + count
        s["items"] += int(items or 0)
    for s in stats.values():
        done = s["success"] + s["failed"]
        s["success_rate"] = round(s["success"] / done, 4) if done else 0
    return list(stats.values())


@router.get("/system")
def system_info():
    return {"rpa_mode": settings.rpa_mode, "scheduler_enabled": settings.scheduler_enabled,
            "database": "sqlite" if settings.is_sqlite else "tidb/mysql", "ws_clients": manager.online,
            "auto_purchase_order": settings.auto_purchase_order, "auto_send_purchase_order": settings.auto_send_purchase_order,
            "smtp_configured": bool(settings.smtp["host"]), "naver_datalab_configured": bool(settings.naver_datalab_client_id),
            "trend_targets": len(settings.trend_scrape_targets), "wholesale_targets": len(settings.wholesale_targets)}
