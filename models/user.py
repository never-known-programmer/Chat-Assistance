from pydantic import BaseModel

# Define the User model with user_id included
class User(BaseModel):
    user_id: str
    name: str
    email: str
    password: str