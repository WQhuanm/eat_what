from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth_router, profile_router, dish_router, recommend_router, history_router, nlp_router
import uvicorn

# 自动建表（基于 ORM 元数据）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="eat_what API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(profile_router.router)
app.include_router(dish_router.router)
app.include_router(recommend_router.router)
app.include_router(history_router.router)
app.include_router(nlp_router.router)


@app.get("/")
def root():
    return {"msg": "eat_what API is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
