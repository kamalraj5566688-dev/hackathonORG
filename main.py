import uvicorn
from api import app

if __name__ == "__main__":
    print("Starting AI Interview Agent Server...")
    # This runs the FastAPI app defined in api.py
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)