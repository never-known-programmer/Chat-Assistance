import os
import csv
from fastapi import FastAPI, HTTPException
from typing import List
from models.user import User
import logging
from fastapi import FastAPI, HTTPException, Request,APIRouter

router = APIRouter()


# Path to the CSV file
CSV_FILE = "user_data.csv"

# Function to save a user to the CSV file
def save_user_to_csv(user: User):
    # Check if the CSV file already exists
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Write header if the file did not exist
        if not file_exists:
            writer.writerow(["user_id", "name", "email", "password"])  # Add headers if file is new
        # Write the user's data
        writer.writerow([user.user_id, user.name, user.email, user.password])  # Add user details

@router.post("/register/")
async def register_user(user: User):
    # Check if the user_id already exists
    if user_exists(user.user_id):
        raise HTTPException(status_code=400, detail="User ID already exists.")

    # Save user details to the CSV file
    save_user_to_csv(user)
    return {"user_id": user.user_id}

# Function to check if the user_id already exists
def user_exists(user_id: str) -> bool:
    if not os.path.isfile(CSV_FILE):
        return False

    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["user_id"] == user_id:
                return True
    return False

# Function to retrieve user details from the CSV file
def retrieve_user_from_csv(email: str):
    if not os.path.isfile(CSV_FILE):
        raise HTTPException(status_code=404, detail="User data not found.")

    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["email"] == email:
                return row  # Return user details as a dictionary
    raise HTTPException(status_code=404, detail="User not found.")

@router.post("/login/")
async def login_user(user: User):
    registered_user = retrieve_user_from_csv(user.email)  # Retrieve user from CSV
    if registered_user and registered_user["password"] == user.password:
        return {"message": f"User '{registered_user['name']}' logged in successfully.", "user_details": registered_user}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

# Sample route to demonstrate retrieval of all users (for testing purposes)
@router.get("/users/", response_model=List[User])
async def get_all_users():
    if not os.path.isfile(CSV_FILE):
        return []
    
    with open(CSV_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        users = [User(user_id=row["user_id"], name=row["name"], email=row["email"], password=row["password"]) for row in reader]
    
    return users

@router.post("/user/interactions/")
async def log_user_interaction(user_id: str, query: str):
    # Log user interactions and query patterns
    logging.info(f"User {user_id} queried: {query}")
    return {"message": "User interaction logged."}
