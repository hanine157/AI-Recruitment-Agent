from fastapi import FastAPI
from app.database import engine

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend is running!"}
@app.get("/test-db")
def test_database():
    try:
        connection = engine.connect()
        connection.close()

        return {
            "message": "Database connected successfully"
        }

    except Exception as e:
        return {
            "error": str(e)
        }