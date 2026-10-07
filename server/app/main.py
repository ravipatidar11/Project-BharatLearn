from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import errors

from .db import ROOT, pool, query, transaction
from .security import password_hash, password_matches, require_admin, require_user, sign_token

app = FastAPI(title="BharatLearn API", version="1.0.0")
logger = logging.getLogger("bharatlearn.api")
_local_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
_deployed_origins = ["https://project-bharat-learn.vercel.app"]
configured_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CLIENT_ORIGIN", "").split(",")
    if origin.strip()
]
allowed_origins = list(dict.fromkeys(
    [*configured_origins, *_deployed_origins]
    if configured_origins
    else [*_local_origins, *_deployed_origins]
))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
_auth_requests: dict[str, list[float]] = {}

COURSE_SELECT = """SELECT c.id,c.title,c.subtitle,c.description,c.level,c.language,c.duration_hours,c.price_inr,c.original_price_inr,
 c.thumbnail_url,c.featured,c.is_published,c.created_at,c.accent,cat.name AS category,cat.slug AS category_slug,
 i.full_name AS instructor,i.title AS instructor_title,i.city AS instructor_city,
 COALESCE(round(avg(r.rating)::numeric,1),4.8) AS rating,count(DISTINCT e.user_id)::int AS student_count,
 count(DISTINCT l.id)::int AS lesson_count
 FROM courses c LEFT JOIN categories cat ON cat.id=c.category_id LEFT JOIN instructors i ON i.id=c.instructor_id
 LEFT JOIN reviews r ON r.course_id=c.id AND r.is_approved=true LEFT JOIN enrollments e ON e.course_id=c.id
 LEFT JOIN course_modules m ON m.course_id=c.id LEFT JOIN lessons l ON l.module_id=m.id"""
COURSE_GROUP = " GROUP BY c.id,cat.id,i.id"


def fail(status: int, message: str) -> None:
    raise HTTPException(status_code=status, detail=message)


def as_object(data: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        fail(400, "A JSON object is required.")
    return data


def text(data: dict[str, Any], key: str, minimum: int = 0, maximum: int = 10000, *, required: bool = True, default: Any = None, nullable: bool = False) -> Any:
    value = data.get(key, default)
    if value is None and nullable:
        return None
    if value is None and not required:
        return default
    if not isinstance(value, str):
        fail(400, f"{key} must be text.")
    value = value.strip()
    if len(value) < minimum or len(value) > maximum:
        fail(400, f"{key} must be between {minimum} and {maximum} characters.")
    return value


def number(data: dict[str, Any], key: str, *, required: bool = True, default: Any = None, integer: bool = False, minimum: float | None = None, maximum: float | None = None) -> Any:
    value = data.get(key, default)
    if value is None and not required:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and int(value) != value):
        fail(400, f"{key} must be a number{', without decimals' if integer else ''}.")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        fail(400, f"{key} is outside the allowed range.")
    return int(value) if integer else value


def boolean(data: dict[str, Any], key: str, default: bool | None = None) -> bool | None:
    value = data.get(key, default)
    if value is None:
        return None
    if not isinstance(value, bool):
        fail(400, f"{key} must be true or false.")
    return value


def string_list(data: dict[str, Any], key: str, max_items: int = 20, max_length: int = 240) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) > max_items or any(not isinstance(item, str) or len(item.strip()) > max_length for item in value):
        fail(400, f"{key} must be a list of up to {max_items} text values.")
    return [item.strip() for item in value]


def email_address(data: dict[str, Any], key: str = "email") -> str:
    value = text(data, key, 3, 180).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        fail(400, f"{key} must be a valid email address.")
    return value


def slug_value(data: dict[str, Any], key: str = "id") -> str:
    value = text(data, key, 1, 180)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        fail(400, f"{key} must be a lowercase URL slug.")
    return value


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "name": user["full_name"], "email": user["email"], "phone": user.get("phone"), "city": user.get("city"), "college": user.get("college"), "education": user.get("education"), "skills": user.get("skills", []), "role": user["role"]}


def rows_one(sql: str, params=(), conn=None):
    rows = query(sql, params, conn=conn)
    return rows[0] if rows else None


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/auth/"):
        now=time.monotonic()
        ip=request.client.host if request.client else "unknown"
        recent=[stamp for stamp in _auth_requests.get(ip,[]) if now-stamp < 900]
        if len(recent) >= 40:
            return JSONResponse(status_code=429,content={"error":"Too many authentication requests. Try again later."})
        recent.append(now)
        _auth_requests[ip]=recent
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "The request body or parameters are invalid."})


@app.exception_handler(errors.UniqueViolation)
async def duplicate_error(_request: Request, _exc: errors.UniqueViolation):
    return JSONResponse(status_code=409, content={"error": "This record already exists."})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, exc: Exception):
    logger.exception("Unhandled BharatLearn API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"error":"Something went wrong. Please try again."})


@app.on_event("startup")
def startup() -> None:
    if not os.getenv("DATABASE_URL") or not os.getenv("JWT_SECRET"):
        raise RuntimeError("Set DATABASE_URL and JWT_SECRET in bharatlearn/.env before starting the API.")
    pool.open(wait=True)


@app.on_event("shutdown")
def shutdown() -> None:
    if pool.closed is False:
        pool.close()


@app.get("/api/health")
def health():
    query("SELECT 1")
    return {"status": "ok", "service": "BharatLearn API", "database": "connected"}


@app.get("/api/stats")
def stats():
    row = rows_one("SELECT (SELECT count(*)::int FROM users WHERE role='student') AS learners,(SELECT count(*)::int FROM courses WHERE is_published) AS courses,(SELECT count(*)::int FROM instructors) AS instructors,(SELECT count(*)::int FROM certificates) AS certificates")
    return {"stats": {"learners": "10,000+" if row["learners"] >= 10000 else f"{row['learners']:,}+", "courses": "200+" if row["courses"] >= 200 else f"{row['courses']}+", "instructors": "50+" if row["instructors"] >= 50 else f"{row['instructors']}+", "certificates": "5,000+" if row["certificates"] >= 5000 else f"{row['certificates']:,}+"}}


# Authentication and student profile
@app.post("/api/auth/register", status_code=201)
def register(body: dict = Body(...)):
    data = as_object(body)
    name = text(data, "name", 2, 100)
    email = email_address(data)
    password = text(data, "password", 8, 100)
    phone = text(data, "phone", 0, 24, required=False, nullable=True)
    city = text(data, "city", 0, 80, required=False, nullable=True)
    college = text(data, "college", 0, 160, required=False, nullable=True)
    education = text(data, "education", 0, 100, required=False, nullable=True)
    try:
        user = rows_one("INSERT INTO users(full_name,email,phone,password_hash,city,college,education) VALUES($1,lower($2),$3,$4,$5,$6,$7) RETURNING id,full_name,email,phone,city,college,education,skills,role", [name,email,phone,password_hash(password),city,college,education])
    except errors.UniqueViolation:
        fail(409, "An account with that email already exists.")
    return {"token": sign_token(user["id"]), "user": public_user(user)}


@app.post("/api/auth/login")
def login(body: dict = Body(...)):
    data = as_object(body)
    email = email_address(data)
    password = text(data, "password", 1, 100)
    user = rows_one("SELECT * FROM users WHERE email=lower($1)", [email])
    if not user or not password_matches(password, user["password_hash"]):
        fail(401, "Email or password is incorrect.")
    return {"token": sign_token(user["id"]), "user": public_user(user)}


@app.get("/api/auth/me")
def auth_me(user=Depends(require_user)):
    profile = rows_one("SELECT id,full_name,email,phone,city,college,education,skills,role FROM users WHERE id=$1", [user["id"]])
    return {"user": public_user(profile)}


@app.put("/api/auth/profile")
def update_profile(body: dict = Body(...), user=Depends(require_user)):
    data = as_object(body)
    name = text(data, "name", 2, 100)
    values = [name]
    for key, limit in (("phone",24),("city",80),("college",160),("education",100)):
        values.append(text(data,key,0,limit,required=False,nullable=True) if key in data else None)
    skills = string_list(data,"skills",20,40) if "skills" in data else []
    profile = rows_one("UPDATE users SET full_name=$1,phone=$2,city=$3,college=$4,education=$5,skills=$6 WHERE id=$7 RETURNING id,full_name,email,phone,city,college,education,skills,role", [*values,skills,user["id"]])
    return {"user": public_user(profile)}


@app.post("/api/auth/forgot-password")
def forgot_password(body: dict = Body(...)):
    email = email_address(as_object(body))
    user = rows_one("SELECT id FROM users WHERE email=lower($1)", [email])
    result = {"message": "If an account exists, password reset instructions are ready."}
    if user:
        raw = secrets.token_hex(32)
        query("INSERT INTO password_reset_tokens(user_id,token_hash,expires_at) VALUES($1,$2,now()+interval '30 minutes')", [user["id"],hashlib.sha256(raw.encode()).hexdigest()])
        if os.getenv("NODE_ENV") in ("development", "test"):
            result["demoToken"] = raw
    return result


@app.post("/api/auth/reset-password")
def reset_password(body: dict = Body(...)):
    data = as_object(body)
    token = text(data,"token",20,200)
    password = text(data,"password",8,100)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with transaction() as conn:
        found = rows_one("SELECT id,user_id FROM password_reset_tokens WHERE token_hash=$1 AND used_at IS NULL AND expires_at>now() FOR UPDATE", [token_hash], conn)
        if not found:
            fail(400, "This reset link has expired or was already used.")
        query("UPDATE users SET password_hash=$1 WHERE id=$2", [password_hash(password),found["user_id"]], conn)
        query("UPDATE password_reset_tokens SET used_at=now() WHERE id=$1", [found["id"]], conn)
    return {"message": "Your password has been updated. You can now sign in."}


# Public discovery and catalogue
@app.get("/api/categories")
def categories():
    return {"categories": query("SELECT c.id,c.name,c.slug,c.icon,count(co.id)::int AS course_count FROM categories c LEFT JOIN courses co ON co.category_id=c.id AND co.is_published GROUP BY c.id ORDER BY c.name")}


@app.get("/api/courses")
def courses(search: str = "", category: str = "", level: str = "", maxPrice: float | None = None, maxDuration: int | None = None, sort: str = ""):
    params: list[Any] = []
    where = ["c.is_published=true"]
    if search.strip():
        params.append(f"%{search.strip()[:100]}%")
        where.append(f"(c.title ILIKE ${len(params)} OR c.subtitle ILIKE ${len(params)} OR cat.name ILIKE ${len(params)} OR i.full_name ILIKE ${len(params)})")
    if category.strip():
        params.append(category.strip())
        where.append(f"(cat.slug=${len(params)} OR cat.name=${len(params)})")
    if level.strip():
        params.append(level.strip())
        where.append(f"c.level=${len(params)}")
    if maxPrice is not None:
        params.append(maxPrice)
        where.append(f"c.price_inr<=${len(params)}")
    if maxDuration is not None:
        params.append(maxDuration)
        where.append(f"c.duration_hours<=${len(params)}")
    order = {"popular":"student_count DESC", "rating":"rating DESC", "newest":"c.created_at DESC", "price_asc":"c.price_inr ASC", "price_desc":"c.price_inr DESC"}.get(sort, "c.featured DESC,c.created_at DESC")
    return {"courses": query(f"{COURSE_SELECT} WHERE {' AND '.join(where)}{COURSE_GROUP} ORDER BY {order},c.title LIMIT 80", params)}


@app.get("/api/courses/{course_id}")
def course_detail(course_id: str):
    course = rows_one(f"{COURSE_SELECT} WHERE c.id=$1 AND c.is_published=true{COURSE_GROUP}", [course_id])
    if not course:
        fail(404, "Course not found.")
    modules = query("""SELECT m.id,m.title,m.position,
      json_agg(json_build_object('id',l.id,'title',l.title,'duration_minutes',l.duration_minutes,'type','lesson') ORDER BY l.position) FILTER(WHERE l.id IS NOT NULL) AS lessons,
      min(q.id) AS quiz_id,min(q.title) AS quiz_title FROM course_modules m LEFT JOIN lessons l ON l.module_id=m.id LEFT JOIN course_quizzes q ON q.module_id=m.id
      WHERE m.course_id=$1 GROUP BY m.id ORDER BY m.position""", [course_id])
    reviews = query("SELECT r.id,r.rating,r.body,r.created_at,u.full_name AS student FROM reviews r JOIN users u ON u.id=r.user_id WHERE r.course_id=$1 AND r.is_approved=true ORDER BY r.created_at DESC LIMIT 20", [course_id])
    instructor = rows_one("SELECT full_name,title,city,bio,rating FROM instructors WHERE id=(SELECT instructor_id FROM courses WHERE id=$1)", [course_id])
    return {"course":course,"modules":modules,"reviews":reviews,"instructor":instructor}


@app.get("/api/search")
def search(q: str = ""):
    term = q.strip()
    if len(term) < 2:
        return {"courses":[],"categories":[],"instructors":[]}
    like = f"%{term[:80]}%"
    return {"courses":query("SELECT id,title,subtitle FROM courses WHERE is_published AND (title ILIKE $1 OR subtitle ILIKE $1) LIMIT 6",[like]),"categories":query("SELECT name,slug FROM categories WHERE name ILIKE $1 LIMIT 5",[like]),"instructors":query("SELECT full_name,title FROM instructors WHERE full_name ILIKE $1 LIMIT 5",[like])}


@app.get("/api/me/wishlist")
def wishlist(user=Depends(require_user)):
    saved = query(f"{COURSE_SELECT} JOIN wishlists w ON w.course_id=c.id AND w.user_id=$1 WHERE c.is_published=true{COURSE_GROUP} ORDER BY max(w.created_at) DESC", [user["id"]])
    return {"courses":saved,"courseIds":[course["id"] for course in saved]}


@app.post("/api/me/wishlist", status_code=201)
def add_wishlist(body: dict = Body(...), user=Depends(require_user)):
    course_id = text(as_object(body),"courseId",2,180)
    saved = query("INSERT INTO wishlists(user_id,course_id) SELECT $1,id FROM courses WHERE id=$2 AND is_published ON CONFLICT DO NOTHING RETURNING course_id", [user["id"],course_id])
    if not saved and not rows_one("SELECT 1 FROM courses WHERE id=$1 AND is_published", [course_id]):
        fail(404,"Course not found.")
    return {"saved":True,"courseId":course_id}


@app.delete("/api/me/wishlist/{course_id}")
def remove_wishlist(course_id: str, user=Depends(require_user)):
    query("DELETE FROM wishlists WHERE user_id=$1 AND course_id=$2", [user["id"],course_id])
    return {"saved":False,"courseId":course_id}


@app.get("/api/instructors")
def instructors():
    return {"instructors":query("SELECT i.*,count(c.id)::int AS course_count FROM instructors i LEFT JOIN courses c ON c.instructor_id=i.id AND c.is_published GROUP BY i.id ORDER BY i.id LIMIT 20")}


# Enrolment, protected lessons, discussion and course quizzes
@app.post("/api/courses/{course_id}/enroll", status_code=201)
def enroll(course_id: str, body: dict = Body(default={}), user=Depends(require_user)):
    method = as_object(body).get("method", "demo_success")
    if method not in ("demo_success","demo_fail","free"):
        fail(400,"Choose a valid checkout method.")
    course = rows_one("SELECT id,title,price_inr FROM courses WHERE id=$1 AND is_published=true", [course_id])
    if not course:
        fail(404,"Course not found.")
    if method == "free" and course["price_inr"] > 0:
        fail(400,"Free checkout is only available for courses priced at ₹0.")
    reference = f"DEMO-{secrets.token_hex(16)}"
    if method == "demo_fail":
        query("INSERT INTO payments(user_id,course_id,amount_inr,method,status,reference) VALUES($1,$2,$3,$4,$5,$6)",[user["id"],course_id,course["price_inr"],method,"failed",reference])
        fail(402,"The demo payment was declined. You have not been charged.")
    with transaction() as conn:
        enrolled = query("INSERT INTO enrollments(user_id,course_id) VALUES($1,$2) ON CONFLICT(user_id,course_id) DO NOTHING RETURNING id",[user["id"],course_id],conn)
        if not enrolled:
            return {"message":"You are already enrolled in this course.","courseId":course_id}
        query("INSERT INTO payments(user_id,course_id,amount_inr,method,status,reference) VALUES($1,$2,$3,$4,$5,$6)",[user["id"],course_id,course["price_inr"],"free" if course["price_inr"] == 0 else method,"success",reference],conn)
        query("INSERT INTO notifications(user_id,title,body,href) VALUES($1,$2,$3,$4)",[user["id"],"You are enrolled",f"Your {course['title']} learning path is ready.",f"/learn/{course_id}"],conn)
    return {"message":"Demo checkout complete. You are enrolled.","courseId":course_id}


@app.get("/api/me/learning")
def learning(user=Depends(require_user)):
    return {"courses":query("""SELECT c.id,c.title,c.subtitle,c.thumbnail_url,c.duration_hours,e.progress_percent,e.enrolled_at,
      count(DISTINCT l.id)::int AS total_lessons,count(DISTINCT lp.lesson_id)::int AS completed_lessons FROM enrollments e JOIN courses c ON c.id=e.course_id
      LEFT JOIN course_modules m ON m.course_id=c.id LEFT JOIN lessons l ON l.module_id=m.id LEFT JOIN lesson_progress lp ON lp.lesson_id=l.id AND lp.user_id=e.user_id
      WHERE e.user_id=$1 GROUP BY c.id,e.id ORDER BY e.enrolled_at DESC""",[user["id"]])}


@app.get("/api/courses/{course_id}/lessons/{lesson_id}")
def get_lesson(course_id: str, lesson_id: int, user=Depends(require_user)):
    if not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],course_id]):
        fail(403,"Enroll in this course to open its lessons.")
    lesson = rows_one("SELECT l.*,m.course_id,m.title AS module_title FROM lessons l JOIN course_modules m ON m.id=l.module_id WHERE m.course_id=$1 AND l.id=$2",[course_id,lesson_id])
    if not lesson:
        fail(404,"Lesson not found.")
    lesson["completed"] = bool(rows_one("SELECT 1 FROM lesson_progress WHERE user_id=$1 AND lesson_id=$2",[user["id"],lesson_id]))
    return {"lesson":lesson}


@app.post("/api/courses/{course_id}/lessons/{lesson_id}/complete")
def complete_lesson(course_id: str, lesson_id: int, user=Depends(require_user)):
    if not rows_one("SELECT l.id FROM lessons l JOIN course_modules m ON m.id=l.module_id WHERE m.course_id=$1 AND l.id=$2",[course_id,lesson_id]):
        fail(404,"Lesson not found.")
    with transaction() as conn:
        enrolled = rows_one("SELECT id FROM enrollments WHERE user_id=$1 AND course_id=$2 FOR UPDATE",[user["id"],course_id],conn)
        if not enrolled:
            fail(403,"Enroll in this course to save lesson progress.")
        query("INSERT INTO lesson_progress(user_id,lesson_id) VALUES($1,$2) ON CONFLICT DO NOTHING",[user["id"],lesson_id],conn)
        counts = rows_one("SELECT count(l.id)::int AS total,count(lp.lesson_id)::int AS done FROM course_modules m JOIN lessons l ON l.module_id=m.id LEFT JOIN lesson_progress lp ON lp.lesson_id=l.id AND lp.user_id=$2 WHERE m.course_id=$1",[course_id,user["id"]],conn)
        progress = round(counts["done"] / counts["total"] * 100) if counts["total"] else 0
        query("UPDATE enrollments SET progress_percent=$1 WHERE id=$2",[progress,enrolled["id"]],conn)
        if progress == 100:
            query("INSERT INTO notifications(user_id,title,body,href) VALUES($1,$2,$3,$4)",[user["id"],"Course complete",f"You completed {course_id.replace('-', ' ')}. Open your dashboard to check certificate eligibility.","/dashboard"],conn)
    return {"progressPercent":progress,"completedLessons":counts["done"],"totalLessons":counts["total"]}


@app.get("/api/courses/{course_id}/discussions")
def get_discussions(course_id: str, user=Depends(require_user)):
    if not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],course_id]):
        fail(403,"Enroll in this course to join the discussion.")
    return {"posts":query("SELECT d.id,d.body,d.created_at,u.full_name AS author,u.role FROM discussion_posts d JOIN users u ON u.id=d.user_id WHERE d.course_id=$1 ORDER BY d.created_at DESC LIMIT 50",[course_id])}


@app.post("/api/courses/{course_id}/discussions", status_code=201)
def post_discussion(course_id: str, body: dict = Body(...), user=Depends(require_user)):
    data = as_object(body)
    message = text(data,"body",2,2000)
    lesson_id = data.get("lessonId")
    if lesson_id is not None and (isinstance(lesson_id,bool) or not isinstance(lesson_id,int)):
        fail(400,"lessonId must be an integer.")
    if not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],course_id]):
        fail(403,"Enroll in this course to join the discussion.")
    post = rows_one("INSERT INTO discussion_posts(course_id,lesson_id,user_id,body) VALUES($1,$2,$3,$4) RETURNING id,body,created_at",[course_id,lesson_id,user["id"],message])
    post.update({"author":user["full_name"],"role":user["role"]})
    return {"post":post}


@app.get("/api/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, user=Depends(require_user)):
    quiz = rows_one("SELECT q.id,q.title,m.course_id FROM course_quizzes q JOIN course_modules m ON m.id=q.module_id WHERE q.id=$1",[quiz_id])
    if not quiz:
        fail(404,"Quiz not found.")
    if not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],quiz["course_id"]]):
        fail(403,"Enroll in this course to take its quiz.")
    return {"quiz":quiz,"questions":query("SELECT id,prompt,options FROM quiz_questions WHERE quiz_id=$1",[quiz_id])}


@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz(quiz_id: int, body: dict = Body(...), user=Depends(require_user)):
    answers = as_object(body).get("answers")
    if not isinstance(answers,dict) or any(not isinstance(v,int) or isinstance(v,bool) or v<0 or v>10 for v in answers.values()):
        fail(400,"answers must map question ids to option indexes.")
    quiz = rows_one("SELECT q.id,m.course_id FROM course_quizzes q JOIN course_modules m ON m.id=q.module_id WHERE q.id=$1",[quiz_id])
    if not quiz or not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],quiz["course_id"]]):
        fail(404,"Quiz not found or course access is required.")
    questions = query("SELECT id,correct_index,explanation FROM quiz_questions WHERE quiz_id=$1",[quiz_id])
    results = [{"questionId":q["id"],"correct":answers.get(str(q["id"]))==q["correct_index"],"correctIndex":q["correct_index"],"explanation":q["explanation"]} for q in questions]
    score = sum(item["correct"] for item in results)
    query("INSERT INTO quiz_attempts(user_id,quiz_id,score,total) VALUES($1,$2,$3,$4)",[user["id"],quiz_id,score,len(questions)])
    return {"score":score,"total":len(questions),"percentage":round(score/len(questions)*100) if questions else 0,"results":results}


# Timed independent tests. Answers are only graded on the server.
@app.get("/api/tests")
def tests():
    return {"tests":query("""SELECT t.id,t.title,t.description,t.category,t.duration_minutes,t.total_marks,t.passing_percent,t.correct_marks,t.wrong_marks,t.max_attempts,t.question_count,t.starts_at,t.ends_at,t.leaderboard_enabled,count(q.id)::int AS available_questions
      FROM tests t LEFT JOIN test_questions q ON q.test_id=t.id AND q.is_active=true WHERE t.is_published=true GROUP BY t.id ORDER BY t.category,t.title""")}


@app.get("/api/tests/{test_id}")
def test_detail(test_id: str):
    test = rows_one("""SELECT t.id,t.title,t.description,t.category,t.duration_minutes,t.total_marks,t.passing_percent,t.correct_marks,t.wrong_marks,t.max_attempts,t.question_count,t.starts_at,t.ends_at,count(q.id)::int AS available_questions
      FROM tests t LEFT JOIN test_questions q ON q.test_id=t.id AND q.is_active=true WHERE t.id=$1 AND t.is_published=true GROUP BY t.id""",[test_id])
    if not test:
        fail(404,"Test not found.")
    return {"test":test}


def grade_attempt(test: dict[str, Any], question_rows: list[dict[str, Any]], question_ids: list[int], answers: dict[str, Any]):
    correct = wrong = unanswered = 0
    score = 0.0
    by_id = {question["id"]: question for question in question_rows}
    review = []
    for position, question_id in enumerate(question_ids, 1):
        question = by_id.get(question_id)
        if not question:
            continue
        given = answers.get(str(question_id))
        option_count=len(question.get("options", []))
        answered = isinstance(given,int) and not isinstance(given,bool) and 0 <= given < (option_count if option_count else 4)
        is_correct = bool(answered and given == question["correct_index"])
        if not answered:
            unanswered += 1
        elif is_correct:
            correct += 1
            score += float(test["correct_marks"])
        else:
            wrong += 1
            score -= float(test["wrong_marks"])
        review.append({"number":position,"questionId":question_id,"topic":question.get("topic"),"prompt":question.get("prompt"),"options":question.get("options"),"selectedIndex":given if answered else None,"correctIndex":question["correct_index"],"correct":is_correct,"explanation":question.get("explanation")})
    score = max(0,round(score,2))
    total_marks = float(test["total_marks"] or 0)
    percentage = max(0,round(score/total_marks*100,2)) if total_marks else 0
    return {"correct":correct,"wrong":wrong,"unanswered":unanswered,"score":score,"percentage":percentage,"review":review}


def test_questions_by_ids(question_ids: list[int], *, answers_hidden: bool = True):
    if not question_ids:
        return []
    columns = "id,topic,prompt,options" if answers_hidden else "id,topic,prompt,options,correct_index,explanation"
    found = query(f"SELECT {columns} FROM test_questions WHERE id=ANY($1::int[])",[question_ids])
    by_id = {question["id"]:question for question in found}
    return [by_id[question_id] for question_id in question_ids if question_id in by_id]


@app.post("/api/tests/{test_id}/start", status_code=201)
def start_test(test_id: str, user=Depends(require_user)):
    with transaction() as conn:
        test = rows_one("SELECT * FROM tests WHERE id=$1 AND is_published=true FOR UPDATE",[test_id],conn)
        if not test:
            fail(404,"Test not found.")
        now = datetime.now(timezone.utc)
        if test["starts_at"] and test["starts_at"] > now:
            fail(409,"This test has not opened yet.")
        if test["ends_at"] and test["ends_at"] < now:
            fail(409,"This test is closed.")
        expired = query("SELECT id,question_ids,answers FROM test_attempts WHERE user_id=$1 AND test_id=$2 AND status='in_progress' AND expires_at<=now() FOR UPDATE",[user["id"],test_id],conn)
        for old in expired:
            old_questions = query("SELECT id,correct_index FROM test_questions WHERE id=ANY($1::int[])",[old["question_ids"]],conn)
            counts = grade_attempt(test, old_questions, old["question_ids"], old["answers"] or {})
            query("UPDATE test_attempts SET status='timed_out',submitted_at=expires_at,score=$1,correct_count=$2,wrong_count=$3,unanswered_count=$4,percentage=$5,passed=$6,time_taken_seconds=$7 WHERE id=$8",[counts["score"],counts["correct"],counts["wrong"],counts["unanswered"],counts["percentage"],counts["percentage"]>=test["passing_percent"],test["duration_minutes"]*60,old["id"]],conn)
        used = rows_one("SELECT count(*)::int AS n FROM test_attempts WHERE user_id=$1 AND test_id=$2 AND status<>'in_progress'",[user["id"],test_id],conn)["n"]
        active = rows_one("SELECT id FROM test_attempts WHERE user_id=$1 AND test_id=$2 AND status='in_progress' AND expires_at>now()",[user["id"],test_id],conn)
        if active:
            attempt = rows_one("SELECT id,started_at,expires_at,answers,question_ids FROM test_attempts WHERE id=$1",[active["id"]],conn)
            questions = test_questions_by_ids(attempt["question_ids"])
            response = {"attempt":{**attempt,"answers":attempt["answers"] or {}},"test":{"id":test["id"],"title":test["title"],"durationMinutes":test["duration_minutes"],"totalMarks":test["total_marks"],"correctMarks":test["correct_marks"],"wrongMarks":test["wrong_marks"]},"questions":questions}
        else:
            if used >= test["max_attempts"]:
                fail(409,"You have used all available attempts.")
            selected = query("SELECT id FROM test_questions WHERE test_id=$1 AND is_active=true ORDER BY random() LIMIT $2",[test_id,test["question_count"]],conn)
            question_ids = [row["id"] for row in selected]
            if not question_ids:
                fail(409,"This test has no questions yet.")
            expires = now + timedelta(minutes=test["duration_minutes"])
            attempt = rows_one("INSERT INTO test_attempts(user_id,test_id,question_ids,expires_at) VALUES($1,$2,$3,$4) RETURNING id,started_at,expires_at",[user["id"],test_id,question_ids,expires],conn)
            response = {"attempt":{**attempt,"answers":{}},"test":{"id":test["id"],"title":test["title"],"durationMinutes":test["duration_minutes"],"totalMarks":test["total_marks"],"correctMarks":test["correct_marks"],"wrongMarks":test["wrong_marks"]},"questions":test_questions_by_ids(question_ids)}
    return response


@app.put("/api/tests/attempts/{attempt_id}/answers")
def save_test_answers(attempt_id: str, body: dict = Body(...), user=Depends(require_user)):
    answers = as_object(body).get("answers")
    if not isinstance(answers,dict) or any(not isinstance(value,int) or isinstance(value,bool) or value < 0 or value > 10 for value in answers.values()):
        fail(400,"answers must map question ids to option indexes.")
    attempt = rows_one("SELECT id,question_ids FROM test_attempts WHERE id=$1 AND user_id=$2 AND status='in_progress' AND expires_at>now()",[attempt_id,user["id"]])
    if not attempt:
        fail(409,"This attempt is no longer accepting answers.")
    allowed = {str(question_id) for question_id in attempt["question_ids"]}
    if any(key not in allowed or value > 3 for key,value in answers.items()):
        fail(400,"One or more answers do not belong to this test.")
    query("UPDATE test_attempts SET answers=answers || $1::jsonb WHERE id=$2 AND user_id=$3 AND status='in_progress' AND expires_at>now()",[json.dumps(answers),attempt_id,user["id"]])
    return {"saved":True,"savedAt":datetime.now(timezone.utc).isoformat()}


@app.post("/api/tests/{test_id}/submit")
def submit_test(test_id: str, body: dict = Body(...), user=Depends(require_user)):
    attempt_id = text(as_object(body),"attemptId",36,36)
    with transaction() as conn:
        attempt = rows_one("SELECT * FROM test_attempts WHERE id=$1 AND user_id=$2 AND test_id=$3 FOR UPDATE",[attempt_id,user["id"],test_id],conn)
        if not attempt:
            fail(404,"Test attempt not found.")
        if attempt["status"] != "in_progress":
            fail(409,"This test has already been submitted.")
        test = rows_one("SELECT * FROM tests WHERE id=$1",[test_id],conn)
        questions = query("SELECT id,topic,prompt,options,correct_index,explanation FROM test_questions WHERE id=ANY($1::int[])",[attempt["question_ids"]],conn)
        graded = grade_attempt(test,questions,attempt["question_ids"],attempt["answers"] or {})
        now = datetime.now(timezone.utc)
        elapsed = max(0,min(int((now-attempt["started_at"]).total_seconds()),test["duration_minutes"]*60))
        timed_out = now > attempt["expires_at"]
        status = "timed_out" if timed_out else "submitted"
        passed = graded["percentage"] >= test["passing_percent"]
        query("UPDATE test_attempts SET status=$1,submitted_at=$2,score=$3,correct_count=$4,wrong_count=$5,unanswered_count=$6,percentage=$7,passed=$8,time_taken_seconds=$9 WHERE id=$10",[status,now,graded["score"],graded["correct"],graded["wrong"],graded["unanswered"],graded["percentage"],passed,elapsed,attempt_id],conn)
        query("INSERT INTO notifications(user_id,title,body,href) VALUES($1,$2,$3,$4)",[user["id"],"Your test result is ready",f"{test['title']}: {graded['percentage']}%{' — passed' if passed else ' — keep practising'}.",f"/tests/result/{attempt_id}"],conn)
    return {"attemptId":attempt_id,"test":{"id":test["id"],"title":test["title"],"totalMarks":float(test["total_marks"]),"passingPercent":test["passing_percent"],"wrongMarks":float(test["wrong_marks"])},"summary":{"total":len(graded["review"]),"attempted":graded["correct"]+graded["wrong"],"correct":graded["correct"],"wrong":graded["wrong"],"unanswered":graded["unanswered"],"score":graded["score"],"percentage":graded["percentage"],"passed":passed,"timeTakenSeconds":elapsed,"timedOut":timed_out},"review":graded["review"]}


@app.get("/api/tests/attempts/{attempt_id}/result")
def test_result(attempt_id: str, user=Depends(require_user)):
    attempt = rows_one("SELECT a.*,t.title,t.total_marks,t.passing_percent FROM test_attempts a JOIN tests t ON t.id=a.test_id WHERE a.id=$1 AND a.user_id=$2 AND a.status<>'in_progress'",[attempt_id,user["id"]])
    if not attempt:
        fail(404,"Submitted test result not found.")
    questions = query("SELECT id,topic,prompt,options,correct_index,explanation FROM test_questions WHERE id=ANY($1::int[])",[attempt["question_ids"]])
    by_id = {q["id"]:q for q in questions}
    review=[]
    for index,question_id in enumerate(attempt["question_ids"],1):
        q=by_id[question_id]
        chosen=(attempt["answers"] or {}).get(str(question_id))
        review.append({"number":index,"questionId":q["id"],"topic":q["topic"],"prompt":q["prompt"],"options":q["options"],"selectedIndex":chosen if isinstance(chosen,int) else None,"correctIndex":q["correct_index"],"correct":chosen==q["correct_index"],"explanation":q["explanation"]})
    return {"attemptId":attempt_id,"test":{"id":attempt["test_id"],"title":attempt["title"],"totalMarks":float(attempt["total_marks"]),"passingPercent":attempt["passing_percent"]},"summary":{"total":len(attempt["question_ids"]),"attempted":attempt["correct_count"]+attempt["wrong_count"],"correct":attempt["correct_count"],"wrong":attempt["wrong_count"],"unanswered":attempt["unanswered_count"],"score":float(attempt["score"]),"percentage":float(attempt["percentage"]),"passed":attempt["passed"],"timeTakenSeconds":attempt["time_taken_seconds"],"timedOut":attempt["status"]=="timed_out"},"review":review}


@app.get("/api/me/test-history")
def test_history(user=Depends(require_user)):
    return {"attempts":query("""SELECT a.id,a.started_at,a.submitted_at,a.score,a.percentage,a.passed,a.time_taken_seconds,a.status,t.id AS test_id,t.title,t.category,
      row_number() OVER(PARTITION BY a.test_id ORDER BY a.started_at) AS attempt_number FROM test_attempts a JOIN tests t ON t.id=a.test_id WHERE a.user_id=$1 ORDER BY a.started_at DESC LIMIT 50""",[user["id"]])}


@app.get("/api/tests/{test_id}/leaderboard")
def leaderboard(test_id: str):
    test=rows_one("SELECT leaderboard_enabled FROM tests WHERE id=$1 AND is_published=true",[test_id])
    if not test or not test["leaderboard_enabled"]:
        return {"leaderboard":[]}
    return {"leaderboard":query("""SELECT u.full_name AS display_name,a.score,a.percentage,a.time_taken_seconds AS time_seconds,
      rank() OVER(ORDER BY a.score DESC,a.time_taken_seconds ASC) AS rank FROM test_attempts a JOIN users u ON u.id=a.user_id
      WHERE a.test_id=$1 AND a.status<>'in_progress' AND a.passed=true ORDER BY rank LIMIT 20""",[test_id])}


# Certificates, reviews and payment history
@app.get("/api/me/certificates")
def my_certificates(user=Depends(require_user)):
    return {"certificates":query("SELECT c.certificate_code,c.issued_at,co.id AS course_id,co.title AS course_title,u.full_name AS student_name FROM certificates c JOIN courses co ON co.id=c.course_id JOIN users u ON u.id=c.user_id WHERE c.user_id=$1 ORDER BY c.issued_at DESC",[user["id"]])}


@app.post("/api/certificates/issue", status_code=201)
def issue_certificate(body: dict = Body(...), user=Depends(require_user)):
    course_id=text(as_object(body),"courseId",2,180)
    enrollment=rows_one("SELECT progress_percent FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],course_id])
    if not enrollment or enrollment["progress_percent"] < 80:
        fail(409,"Complete at least 80% of the course to unlock your certificate.")
    passed=rows_one("SELECT 1 FROM test_attempts WHERE user_id=$1 AND passed=true AND status<>'in_progress' LIMIT 1",[user["id"]])
    if not passed:
        fail(409,"Pass an independent test to unlock your certificate.")
    code=f"BL-{secrets.token_hex(5).upper()}"
    cert=rows_one("INSERT INTO certificates(certificate_code,user_id,course_id) VALUES($1,$2,$3) ON CONFLICT(user_id,course_id) DO UPDATE SET user_id=EXCLUDED.user_id RETURNING certificate_code,issued_at",[code,user["id"],course_id])
    cert["course_id"]=course_id
    return {"certificate":cert,"message":"Certificate unlocked."}


@app.get("/api/certificates/verify/{code}")
def verify_certificate(code: str):
    cert=rows_one("SELECT c.certificate_code,c.issued_at,u.full_name AS student_name,co.title AS course_title FROM certificates c JOIN users u ON u.id=c.user_id JOIN courses co ON co.id=c.course_id WHERE c.certificate_code=$1",[code.upper()])
    if not cert:
        return JSONResponse(status_code=404,content={"valid":False,"error":"No certificate matches that verification code."})
    return {"valid":True,"certificate":cert}


@app.post("/api/courses/{course_id}/reviews", status_code=201)
def add_review(course_id: str, body: dict = Body(...), user=Depends(require_user)):
    data=as_object(body)
    rating=number(data,"rating",integer=True,minimum=1,maximum=5)
    message=text(data,"body",10,1200)
    if not rows_one("SELECT 1 FROM enrollments WHERE user_id=$1 AND course_id=$2",[user["id"],course_id]):
        fail(403,"Only enrolled learners can review a course.")
    review=rows_one("INSERT INTO reviews(user_id,course_id,rating,body) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,course_id) DO UPDATE SET rating=EXCLUDED.rating,body=EXCLUDED.body,is_approved=false RETURNING id,rating,body,is_approved",[user["id"],course_id,rating,message])
    return {"review":review,"message":"Thanks. Your review is waiting for moderation."}


@app.get("/api/me/payments")
def my_payments(user=Depends(require_user)):
    return {"payments":query("SELECT p.*,c.title AS course_title FROM payments p JOIN courses c ON c.id=p.course_id WHERE p.user_id=$1 ORDER BY p.created_at DESC LIMIT 50",[user["id"]])}


# Learner dashboard, notifications and contact form
@app.get("/api/me/dashboard")
def dashboard(user=Depends(require_user)):
    learning_rows=query("""SELECT c.id,c.title,c.thumbnail_url,c.duration_hours,e.progress_percent,count(DISTINCT l.id)::int AS total_lessons,count(DISTINCT lp.lesson_id)::int AS completed_lessons FROM enrollments e JOIN courses c ON c.id=e.course_id LEFT JOIN course_modules m ON m.course_id=c.id LEFT JOIN lessons l ON l.module_id=m.id LEFT JOIN lesson_progress lp ON lp.lesson_id=l.id AND lp.user_id=e.user_id WHERE e.user_id=$1 GROUP BY c.id,e.id ORDER BY e.enrolled_at DESC LIMIT 6""",[user["id"]])
    history=query("SELECT a.id,a.started_at,a.score,a.percentage,a.passed,a.time_taken_seconds,t.title,t.category FROM test_attempts a JOIN tests t ON t.id=a.test_id WHERE a.user_id=$1 AND a.status<>'in_progress' ORDER BY a.started_at DESC LIMIT 5",[user["id"]])
    certificate_count=rows_one("SELECT count(*)::int AS n FROM certificates WHERE user_id=$1",[user["id"]])["n"]
    notifications=query("SELECT id,title,body,href,read_at,created_at FROM notifications WHERE user_id=$1 ORDER BY created_at DESC LIMIT 8",[user["id"]])
    recent=query("SELECT id,course_id,progress_percent FROM enrollments WHERE user_id=$1",[user["id"]])
    activity=query("""SELECT to_char(days.day,'Dy') AS day,COALESCE(count(lp.lesson_id)*0.25,0)::numeric(5,2) AS hours FROM generate_series(current_date-interval '6 days',current_date,interval '1 day') days(day)
      LEFT JOIN lesson_progress lp ON lp.user_id=$1 AND date_trunc('day',lp.completed_at)=days.day GROUP BY days.day ORDER BY days.day""",[user["id"]])
    totals=rows_one("SELECT (SELECT count(*)::int FROM enrollments WHERE user_id=$1) AS enrolled,(SELECT count(*)::int FROM enrollments WHERE user_id=$1 AND progress_percent=100) AS completed,(SELECT count(*)::int FROM test_attempts WHERE user_id=$1 AND status<>'in_progress') AS tests,(SELECT COALESCE(sum(c.duration_hours*e.progress_percent/100.0),0)::int FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=$1) AS learning_hours",[user["id"]])
    recommendations=query(f"{COURSE_SELECT} WHERE c.is_published=true AND NOT EXISTS(SELECT 1 FROM enrollments e WHERE e.user_id=$1 AND e.course_id=c.id){COURSE_GROUP} ORDER BY c.featured DESC,rating DESC LIMIT 3",[user["id"]])
    return {"stats":{**totals,"certificates":certificate_count},"courses":learning_rows,"recentTests":history,"notifications":notifications,"recommendations":recommendations,"activity":recent,"learningActivity":activity}


@app.get("/api/me/notifications")
def my_notifications(user=Depends(require_user)):
    return {"notifications":query("SELECT id,title,body,href,read_at,created_at FROM notifications WHERE user_id=$1 ORDER BY created_at DESC LIMIT 50",[user["id"]])}


@app.post("/api/me/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user=Depends(require_user)):
    query("UPDATE notifications SET read_at=now() WHERE id=$1 AND user_id=$2",[notification_id,user["id"]])
    return {"read":True}


@app.post("/api/contact", status_code=201)
def contact(body: dict = Body(...)):
    data=as_object(body)
    name=text(data,"name",2,100)
    email=email_address(data)
    phone=text(data,"phone",0,24,required=False,nullable=True)
    subject=text(data,"subject",3,160)
    message=text(data,"message",10,3000)
    query("INSERT INTO contact_messages(name,email,phone,subject,message) VALUES($1,$2,$3,$4,$5)",[name,email,phone,subject,message])
    return {"message":"Thanks for reaching out. Your message has been saved."}


# Admin studio: learners, learning content, tests and moderation
@app.get("/api/admin/overview")
def admin_overview(_admin=Depends(require_admin)):
    stats_row=rows_one("SELECT (SELECT count(*)::int FROM users WHERE role='student') AS students,(SELECT count(*)::int FROM courses) AS courses,(SELECT count(*)::int FROM enrollments) AS enrollments,(SELECT count(*)::int FROM test_attempts WHERE status<>'in_progress') AS tests_taken,(SELECT count(*)::int FROM certificates) AS certificates,(SELECT COALESCE(sum(amount_inr),0)::int FROM payments WHERE status='success') AS demo_revenue_inr")
    monthly=query("""SELECT to_char(month,'Mon') AS month,count(e.id)::int AS enrollments FROM generate_series(date_trunc('month',now())-interval '5 months',date_trunc('month',now()),interval '1 month') month LEFT JOIN enrollments e ON date_trunc('month',e.enrolled_at)=month GROUP BY month ORDER BY month""")
    activity=query("SELECT u.full_name,c.title,e.enrolled_at FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id ORDER BY e.enrolled_at DESC LIMIT 8")
    return {"stats":stats_row,"monthly":monthly,"activity":activity}


@app.get("/api/admin/students")
def admin_students(search: str = "", _admin=Depends(require_admin)):
    term=search.strip()
    return {"students":query("""SELECT u.id,u.full_name,u.email,u.city,u.college,u.created_at,count(DISTINCT e.id)::int AS enrollments,count(DISTINCT a.id)::int AS tests_taken FROM users u LEFT JOIN enrollments e ON e.user_id=u.id LEFT JOIN test_attempts a ON a.user_id=u.id WHERE u.role='student' AND ($1='' OR u.full_name ILIKE $2 OR u.email ILIKE $2) GROUP BY u.id ORDER BY u.created_at DESC LIMIT 100""",[term,f"%{term}%"])}


@app.get("/api/admin/students/{student_id}")
def admin_student_detail(student_id: str, _admin=Depends(require_admin)):
    student=rows_one("SELECT id,full_name,email,phone,city,college,education,created_at FROM users WHERE id=$1 AND role='student'",[student_id])
    if not student:
        fail(404,"Student not found.")
    return {"student":student,"courses":query("SELECT c.id,c.title,e.progress_percent,e.enrolled_at FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=$1 ORDER BY e.enrolled_at DESC",[student["id"]]),"attempts":query("SELECT a.id,t.title,a.started_at,a.percentage,a.passed FROM test_attempts a JOIN tests t ON t.id=a.test_id WHERE a.user_id=$1 ORDER BY a.started_at DESC LIMIT 20",[student["id"]]),"certificates":query("SELECT certificate_code,c.title AS course_title,issued_at FROM certificates x JOIN courses c ON c.id=x.course_id WHERE x.user_id=$1",[student["id"]])}


@app.get("/api/admin/courses")
def admin_courses(_admin=Depends(require_admin)):
    return {"courses":query(f"{COURSE_SELECT}{COURSE_GROUP} ORDER BY c.created_at DESC LIMIT 200")}


@app.get("/api/admin/courses/{course_id}/curriculum")
def admin_curriculum(course_id: str, _admin=Depends(require_admin)):
    course=rows_one("SELECT id,title FROM courses WHERE id=$1",[course_id])
    if not course:
        fail(404,"Course not found.")
    modules=query("""SELECT m.id,m.title,m.position,min(q.id) AS quiz_id,min(q.title) AS quiz_title,
      COALESCE(json_agg(json_build_object('id',l.id,'title',l.title,'description',l.description,'video_url',l.video_url,'duration_minutes',l.duration_minutes,'position',l.position) ORDER BY l.position) FILTER(WHERE l.id IS NOT NULL),'[]'::json) AS lessons
      FROM course_modules m LEFT JOIN lessons l ON l.module_id=m.id LEFT JOIN course_quizzes q ON q.module_id=m.id WHERE m.course_id=$1 GROUP BY m.id ORDER BY m.position""",[course_id])
    return {"course":course,"modules":modules}


@app.post("/api/admin/courses/{course_id}/modules", status_code=201)
def admin_add_module(course_id: str, body: dict = Body(...), _admin=Depends(require_admin)):
    data=as_object(body)
    title=text(data,"title",2,160)
    position=number(data,"position",required=False,default=0,integer=True,minimum=0)
    module=rows_one("INSERT INTO course_modules(course_id,title,position) SELECT id,$2,$3 FROM courses WHERE id=$1 RETURNING id,title,position",[course_id,title,position])
    if not module:
        fail(404,"Course not found.")
    return {"module":module}


@app.put("/api/admin/modules/{module_id}")
def admin_update_module(module_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    data=as_object(body)
    title=text(data,"title",2,160,required=False) if "title" in data else None
    position=number(data,"position",required=False,integer=True,minimum=0) if "position" in data else None
    module=rows_one("UPDATE course_modules SET title=COALESCE($1,title),position=COALESCE($2,position) WHERE id=$3 RETURNING id,title,position",[title,position,module_id])
    if not module:
        fail(404,"Module not found.")
    return {"module":module}


@app.delete("/api/admin/modules/{module_id}")
def admin_delete_module(module_id: int, _admin=Depends(require_admin)):
    with transaction() as conn:
        rows=query("DELETE FROM course_modules WHERE id=$1 RETURNING id",[module_id],conn)
    if not rows:
        fail(404,"Module not found.")
    return {"deleted":True}


def optional_url(data: dict[str, Any], key: str):
    value=data.get(key)
    if value is None:
        return None
    value=text(data,key,1,2000)
    if not re.match(r"^https?://",value):
        fail(400,f"{key} must be a valid URL.")
    return value


@app.post("/api/admin/modules/{module_id}/lessons", status_code=201)
def admin_add_lesson(module_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    data=as_object(body)
    title=text(data,"title",2,180)
    description=text(data,"description",0,3000,required=False,default="")
    video_url=optional_url(data,"videoUrl")
    duration=number(data,"durationMinutes",required=False,default=10,integer=True,minimum=1,maximum=600)
    position=number(data,"position",required=False,default=0,integer=True,minimum=0)
    lesson=rows_one("INSERT INTO lessons(module_id,title,description,video_url,duration_minutes,position) SELECT id,$2,$3,$4,$5,$6 FROM course_modules WHERE id=$1 RETURNING id,title,description,video_url,duration_minutes,position",[module_id,title,description,video_url,duration,position])
    if not lesson:
        fail(404,"Module not found.")
    return {"lesson":lesson}


@app.put("/api/admin/lessons/{lesson_id}")
def admin_update_lesson(lesson_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    data=as_object(body)
    title=text(data,"title",2,180,required=False) if "title" in data else None
    description=text(data,"description",0,3000,required=False) if "description" in data else None
    video_url=optional_url(data,"videoUrl") if "videoUrl" in data else None
    duration=number(data,"durationMinutes",required=False,integer=True,minimum=1,maximum=600) if "durationMinutes" in data else None
    position=number(data,"position",required=False,integer=True,minimum=0) if "position" in data else None
    lesson=rows_one("UPDATE lessons SET title=COALESCE($1,title),description=COALESCE($2,description),video_url=COALESCE($3,video_url),duration_minutes=COALESCE($4,duration_minutes),position=COALESCE($5,position) WHERE id=$6 RETURNING id",[title,description,video_url,duration,position,lesson_id])
    if not lesson:
        fail(404,"Lesson not found.")
    return {"updated":True}


@app.delete("/api/admin/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int, _admin=Depends(require_admin)):
    deleted=query("DELETE FROM lessons WHERE id=$1 RETURNING id",[lesson_id])
    if not deleted:
        fail(404,"Lesson not found.")
    return {"deleted":True}


@app.post("/api/admin/modules/{module_id}/quizzes", status_code=201)
def admin_add_quiz(module_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    title=text(as_object(body),"title",2,160)
    quiz=rows_one("INSERT INTO course_quizzes(module_id,title) SELECT id,$2 FROM course_modules WHERE id=$1 RETURNING id,title",[module_id,title])
    if not quiz:
        fail(404,"Module not found.")
    return {"quiz":quiz}


def question_fields(data: dict[str, Any], *, test_question: bool = False, existing: bool = False):
    fields={}
    fields["topic"]=text(data,"topic",0,80,required=False,default="Core concepts") if test_question or "topic" in data else None
    fields["prompt"]=text(data,"prompt",8,1000,required=not existing) if "prompt" in data or not existing else None
    if "options" in data:
        options=string_list(data,"options",4,240)
        if len(options)!=4 or any(not option for option in options):
            fail(400,"Each question must have exactly four non-empty options.")
        fields["options"]=json.dumps(options)
    else:
        if not existing:
            fail(400,"options must contain exactly four answer choices.")
        fields["options"]=None
    fields["correct_index"]=number(data,"correctIndex",required=not existing,integer=True,minimum=0,maximum=3) if "correctIndex" in data or not existing else None
    fields["explanation"]=text(data,"explanation",0,1000,required=False,default="") if "explanation" in data or not existing else None
    if test_question:
        fields["position"]=number(data,"position",required=False,default=999,integer=True,minimum=0) if "position" in data or not existing else None
    return fields


@app.post("/api/admin/quizzes/{quiz_id}/questions", status_code=201)
def admin_add_quiz_question(quiz_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    d=question_fields(as_object(body))
    row=rows_one("INSERT INTO quiz_questions(quiz_id,prompt,options,correct_index,explanation) SELECT id,$2,$3,$4,$5 FROM course_quizzes WHERE id=$1 RETURNING id,prompt",[quiz_id,d["prompt"],d["options"],d["correct_index"],d["explanation"]])
    if not row:
        fail(404,"Quiz not found.")
    return {"question":row}


@app.post("/api/admin/courses", status_code=201)
def admin_create_course(body: dict = Body(...), _admin=Depends(require_admin)):
    d=as_object(body)
    course_id=slug_value(d)
    title=text(d,"title",3,160)
    subtitle=text(d,"subtitle",0,240,required=False,default="")
    description=text(d,"description",0,6000,required=False,default="")
    category_id=number(d,"categoryId",integer=True)
    instructor_id=number(d,"instructorId",integer=True)
    level=text(d,"level",1,30)
    if level not in ("Beginner","Intermediate","Advanced"):
        fail(400,"Choose a valid course level.")
    language=text(d,"language",0,60,required=False,default="English")
    duration=number(d,"durationHours",integer=True,minimum=1,maximum=1000)
    price=number(d,"priceInr",integer=True,minimum=0)
    original=number(d,"originalPriceInr",integer=True,minimum=0)
    published=boolean(d,"isPublished",False)
    featured=boolean(d,"featured",False)
    query("INSERT INTO courses(id,title,subtitle,description,category_id,instructor_id,level,language,duration_hours,price_inr,original_price_inr,is_published,featured) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",[course_id,title,subtitle,description,category_id,instructor_id,level,language,duration,price,original,published,featured])
    return {"course":{"id":course_id,"title":title}}


@app.put("/api/admin/courses/{course_id}")
def admin_update_course(course_id: str, body: dict = Body(...), _admin=Depends(require_admin)):
    d=as_object(body)
    title=text(d,"title",3,160,required=False) if "title" in d else None
    subtitle=text(d,"subtitle",0,240,required=False) if "subtitle" in d else None
    description=text(d,"description",0,6000,required=False) if "description" in d else None
    category_id=number(d,"categoryId",required=False,integer=True) if "categoryId" in d else None
    instructor_id=number(d,"instructorId",required=False,integer=True) if "instructorId" in d else None
    language=text(d,"language",0,60,required=False) if "language" in d else None
    duration=number(d,"durationHours",required=False,integer=True,minimum=1,maximum=1000) if "durationHours" in d else None
    price=number(d,"priceInr",required=False,integer=True,minimum=0) if "priceInr" in d else None
    original=number(d,"originalPriceInr",required=False,integer=True,minimum=0) if "originalPriceInr" in d else None
    level=text(d,"level",1,30,required=False) if "level" in d else None
    if level is not None and level not in ("Beginner","Intermediate","Advanced"):
        fail(400,"Choose a valid course level.")
    published=boolean(d,"isPublished") if "isPublished" in d else None
    featured=boolean(d,"featured") if "featured" in d else None
    row=rows_one("UPDATE courses SET title=COALESCE($1,title),subtitle=COALESCE($2,subtitle),description=COALESCE($3,description),category_id=COALESCE($4,category_id),instructor_id=COALESCE($5,instructor_id),language=COALESCE($6,language),duration_hours=COALESCE($7,duration_hours),price_inr=COALESCE($8,price_inr),original_price_inr=COALESCE($9,original_price_inr),level=COALESCE($10,level),is_published=COALESCE($11,is_published),featured=COALESCE($12,featured) WHERE id=$13 RETURNING id,title,is_published",[title,subtitle,description,category_id,instructor_id,language,duration,price,original,level,published,featured,course_id])
    if not row:
        fail(404,"Course not found.")
    return {"course":row}


@app.delete("/api/admin/courses/{course_id}")
def admin_delete_course(course_id: str, _admin=Depends(require_admin)):
    if not query("DELETE FROM courses WHERE id=$1 RETURNING id",[course_id]):
        fail(404,"Course not found.")
    return {"deleted":True}


@app.get("/api/admin/categories")
def admin_categories(_admin=Depends(require_admin)):
    return {"categories":query("SELECT * FROM categories ORDER BY name")}


@app.post("/api/admin/categories", status_code=201)
def admin_create_category(body: dict = Body(...), _admin=Depends(require_admin)):
    d=as_object(body)
    name=text(d,"name",2,80)
    slug=slug_value(d,"slug")
    icon=text(d,"icon",0,40,required=False,default="Code2")
    category=rows_one("INSERT INTO categories(name,slug,icon) VALUES($1,$2,$3) RETURNING *",[name,slug,icon])
    return {"category":category}


@app.delete("/api/admin/categories/{category_id}")
def admin_delete_category(category_id: int, _admin=Depends(require_admin)):
    if not query("DELETE FROM categories WHERE id=$1 RETURNING id",[category_id]):
        fail(404,"Category not found.")
    return {"deleted":True}


@app.get("/api/admin/tests")
def admin_tests(_admin=Depends(require_admin)):
    return {"tests":query("SELECT t.*,count(q.id)::int AS actual_questions FROM tests t LEFT JOIN test_questions q ON q.test_id=t.id AND q.is_active=true GROUP BY t.id ORDER BY t.created_at DESC")}


@app.get("/api/admin/tests/{test_id}/questions")
def admin_test_questions(test_id: str, _admin=Depends(require_admin)):
    return {"questions":query("SELECT id,topic,prompt,options,correct_index,explanation,position FROM test_questions WHERE test_id=$1 AND is_active=true ORDER BY position",[test_id])}


@app.post("/api/admin/tests/{test_id}/questions", status_code=201)
def admin_add_test_question(test_id: str, body: dict = Body(...), _admin=Depends(require_admin)):
    d=question_fields(as_object(body),test_question=True)
    row=rows_one("INSERT INTO test_questions(test_id,topic,prompt,options,correct_index,explanation,position) SELECT id,$2,$3,$4,$5,$6,$7 FROM tests WHERE id=$1 RETURNING id,topic,prompt,options,correct_index,explanation,position",[test_id,d["topic"],d["prompt"],d["options"],d["correct_index"],d["explanation"],d["position"]])
    if not row:
        fail(404,"Test not found.")
    return {"question":row}


@app.put("/api/admin/questions/{question_id}")
def admin_update_question(question_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    d=question_fields(as_object(body),test_question=True,existing=True)
    if "topic" not in body:
        d["topic"]=None
    row=rows_one("UPDATE test_questions SET topic=COALESCE($1,topic),prompt=COALESCE($2,prompt),options=COALESCE($3::jsonb,options),correct_index=COALESCE($4,correct_index),explanation=COALESCE($5,explanation),position=COALESCE($6,position) WHERE id=$7 RETURNING id",[d["topic"],d["prompt"],d["options"],d["correct_index"],d["explanation"],d["position"],question_id])
    if not row:
        fail(404,"Question not found.")
    return {"updated":True}


@app.delete("/api/admin/questions/{question_id}")
def admin_delete_question(question_id: int, _admin=Depends(require_admin)):
    if not query("DELETE FROM test_questions WHERE id=$1 RETURNING id",[question_id]):
        fail(404,"Question not found.")
    return {"deleted":True}


@app.post("/api/admin/tests", status_code=201)
def admin_create_test(body: dict = Body(...), _admin=Depends(require_admin)):
    d=as_object(body)
    test_id=slug_value(d)
    title=text(d,"title",3,160)
    description=text(d,"description",0,1000,required=False,default="")
    category=text(d,"category",2,80)
    duration=number(d,"durationMinutes",integer=True,minimum=1,maximum=240)
    total=number(d,"totalMarks",minimum=0.01)
    passing=number(d,"passingPercent",integer=True,minimum=1,maximum=100)
    correct=number(d,"correctMarks",minimum=0.01)
    wrong=number(d,"wrongMarks",minimum=0)
    attempts=number(d,"maxAttempts",integer=True,minimum=1,maximum=10)
    count=number(d,"questionCount",integer=True,minimum=1,maximum=500)
    published=boolean(d,"isPublished",False)
    query("INSERT INTO tests(id,title,description,category,duration_minutes,total_marks,passing_percent,correct_marks,wrong_marks,max_attempts,question_count,is_published) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",[test_id,title,description,category,duration,total,passing,correct,wrong,attempts,count,published])
    return {"test":{"id":test_id,"title":title}}


@app.put("/api/admin/tests/{test_id}")
def admin_update_test(test_id: str, body: dict = Body(...), _admin=Depends(require_admin)):
    d=as_object(body)
    published=boolean(d,"isPublished") if "isPublished" in d else None
    duration=number(d,"durationMinutes",required=False,integer=True,minimum=1,maximum=240) if "durationMinutes" in d else None
    passing=number(d,"passingPercent",required=False,integer=True,minimum=1,maximum=100) if "passingPercent" in d else None
    attempts=number(d,"maxAttempts",required=False,integer=True,minimum=1,maximum=10) if "maxAttempts" in d else None
    leaderboard_enabled=boolean(d,"leaderboardEnabled") if "leaderboardEnabled" in d else None
    row=rows_one("UPDATE tests SET is_published=COALESCE($1,is_published),duration_minutes=COALESCE($2,duration_minutes),passing_percent=COALESCE($3,passing_percent),max_attempts=COALESCE($4,max_attempts),leaderboard_enabled=COALESCE($5,leaderboard_enabled) WHERE id=$6 RETURNING id,title,is_published",[published,duration,passing,attempts,leaderboard_enabled,test_id])
    if not row:
        fail(404,"Test not found.")
    return {"test":row}


@app.delete("/api/admin/tests/{test_id}")
def admin_delete_test(test_id: str, _admin=Depends(require_admin)):
    if not query("DELETE FROM tests WHERE id=$1 RETURNING id",[test_id]):
        fail(404,"Test not found.")
    return {"deleted":True}


@app.get("/api/admin/reviews")
def admin_reviews(_admin=Depends(require_admin)):
    return {"reviews":query("SELECT r.id,r.rating,r.body,r.is_approved,r.created_at,u.full_name AS student,c.title AS course FROM reviews r JOIN users u ON u.id=r.user_id JOIN courses c ON c.id=r.course_id ORDER BY r.created_at DESC LIMIT 100")}


@app.patch("/api/admin/reviews/{review_id}")
def admin_moderate_review(review_id: int, body: dict = Body(...), _admin=Depends(require_admin)):
    approved=boolean(as_object(body),"approved")
    if approved is None:
        fail(400,"approved is required.")
    review=rows_one("UPDATE reviews SET is_approved=$1 WHERE id=$2 RETURNING id,is_approved",[approved,review_id])
    if not review:
        fail(404,"Review not found.")
    return {"review":review}


@app.get("/api/admin/payments")
def admin_payments(_admin=Depends(require_admin)):
    return {"payments":query("SELECT p.id,p.amount_inr,p.method,p.status,p.reference,p.created_at,u.full_name AS student,c.title AS course FROM payments p JOIN users u ON u.id=p.user_id JOIN courses c ON c.id=p.course_id ORDER BY p.created_at DESC LIMIT 200")}


@app.get("/api/admin/certificates")
def admin_certificates(_admin=Depends(require_admin)):
    return {"certificates":query("SELECT x.certificate_code,x.issued_at,u.full_name AS student,c.title AS course FROM certificates x JOIN users u ON u.id=x.user_id JOIN courses c ON c.id=x.course_id ORDER BY x.issued_at DESC LIMIT 200")}
