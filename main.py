from typing import Union

from fastapi import FastAPI

app = FastAPI()


# Fake database
from db import DB_PROPERTY, Database

db = Database( DB_PROPERTY )


@app.get("/")
def read_root():
    return {"Hello": "World"}



@app.get("/api/user/{user_id}")
def get_single_user(user_id: int):
    user_records = db.read('users', {'permission': 0})
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