from typing import Union, Optional

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

import uuid

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fake database
from db import DB_PROPERTY, Database

db = Database( DB_PROPERTY )
guest = db.create('users', {
    'username': 'guest', 
    'password': 'no_password', 
    'permission': 0, 
    'auth_method': 'no_password',
})
print(guest)
CACHE = {'guest': guest}


@app.get("/api/user/profile")
def read_root(Authorization: Optional[str] = Header(None, convert_underscores=False)):
    print(CACHE, Authorization)
    if Authorization in CACHE:
        return CACHE[Authorization]
    else:
        return {"error": "Authorization Token was wrong or token is missing."}

@app.post("/api/user/session")
def create_user_session(username: str, password: str):
    global CACHE
    users = db.read("users", { "username": username, "password": password })
    if len(users) == 0:
        return {"error": "Wrong username or password."}
    else:
        UUID4 = str(uuid.uuid4())
        user = users[0]
        USER = {
            "username": user["username"], 
            "permission": user["permission"] 
        }
        CACHE[UUID4] = USER
        return {
            'user': USER,
            'token': UUID4
        }

@app.get("/api/user/{user_id}")
def get_single_user(user_id: int):
    user_records = db.read('users', {'user_id': user_id})
    return user_records

@app.post('/api/user')
def create_user(username: str, password: str):
    user = db.create('users', {
        'username': username, 
        'password': password, 
        'permission': 0, 
        'auth_method': 'password',
    })
    return user
