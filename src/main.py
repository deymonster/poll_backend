import os
import uvicorn
from fastapi import FastAPI, Response, Request, Depends
from starlette.middleware.cors import CORSMiddleware

from api import routers
from db.session import SessionLocal, db_session
from fastapi.staticfiles import StaticFiles
from api.utils.security import create_initial_user
from company.scheduler import scheduler
from pkg.mongo_tools.db import session_collection, get_mongo_collection

from user.models import User
from poll.models import Poll
from company.models import Company

# from pkg.mongo_tools.db import mongo_manager
app = FastAPI(
    title="TestDesk",
    description="TestDesk API - это сервис для создания и прохождения опросов.",
    version="0.0.1",
)


origins = [

    "http://localhost:9000",
    "http://testdesk.ru:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# установка пути к папке с медиа файлами
media_path = os.path.abspath("media")

app.mount("/media", StaticFiles(directory=media_path), name="media")


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        request.state.mongo_db = get_mongo_collection()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response


@app.on_event("startup")
async def startup_event():
    create_initial_user(db=db_session())
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()


app.include_router(routers.api_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
