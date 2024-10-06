from fastapi import FastAPI,Request
from starlette.middleware.cors import CORSMiddleware
from app.chat import router as chat_router
from app.user import router as user_router
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()


# Example of adding middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; customize as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logging.info(f"Request: {request.method} {request.url} - Status: {response.status_code}")
    return response

# Include the routers from chat.py and user.py
app.include_router(chat_router)
app.include_router(user_router)

# Optionally, you can specify a prefix for the routers
# app.include_router(chat_router, prefix="/chat")
# app.include_router(user_router, prefix="/user")

# Example root route
@app.get("/")
async def root():
    return {"message": "Welcome to the API!"}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
