from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversation import router as conversation_router
from app.api.course import router as course_router
from app.api.material import router as material_router
from app.api.study_plan import router as study_plan_router
from app.api.users import router as users_router
from app.core.agent import init_agent


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 服务器启动时初始化一次 Agent
    init_agent()
    yield


app = FastAPI(title="Campus Copilot Pro", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(course_router)
app.include_router(study_plan_router)
app.include_router(material_router)
app.include_router(users_router)
