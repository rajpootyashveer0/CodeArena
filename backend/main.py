from fastapi import FastAPI

app = FastAPI(title="CodeArena API")


@app.get("/")
def home():
    return {"message": "Welcome to CodeArena!"}