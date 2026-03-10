from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import redis
import json

# Database Configuration
DATABASE_URL = "mysql+pymysql://root:Verve%40123@localhost/redis_demo"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


# Redis Configuration
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


# User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100))
    age = Column(Integer)
    address = Column(String(255))



# FastAPI App
app = FastAPI()


# Create User
@app.post("/users")
def create_user(name: str, email: str, age: int, address: str):

    db = SessionLocal()

    user = User(
        name=name,
        email=email,
        age=age,
        address=address
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # cache clear
    redis_client.delete("users_all")

    return {"message": "User created", "id": user.id}


# Get All Users (Redis Cache)
@app.get("/users")
def get_users():

    # check redis cache
    cached = redis_client.get("users_all")

    if cached:
        print("FROM REDIS CACHE")
        return json.loads(cached)

    db = SessionLocal()

    users = db.query(User).all()

    result = []

    for u in users:
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "age": u.age,
            "address": u.address
        })

    # store in redis cache for 60 seconds
    redis_client.set("users_all", json.dumps(result), ex=60)

    print("FROM DATABASE")

    return result



# Get User By ID
@app.get("/users/{user_id}")
def get_user(user_id: int):

    cache_key = f"user:{user_id}"

    cached = redis_client.get(cache_key)

    if cached:
        print("FROM REDIS CACHE")
        return json.loads(cached)

    db = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "address": user.address
    }

    redis_client.set(cache_key, json.dumps(result), ex=60)

    print("FROM DATABASE")

    return result


# Update User
@app.put("/users/{user_id}")
def update_user(user_id: int, name: str, email: str, age: int, address: str):

    db = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = name
    user.email = email
    user.age = age
    user.address = address

    db.commit()

    # clear redis cache
    redis_client.delete(f"user:{user_id}")
    redis_client.delete("users_all")

    return {"message": "User updated"}


# Delete User
@app.delete("/users/{user_id}")
def delete_user(user_id: int):

    db = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    # clear redis cache
    redis_client.delete(f"user:{user_id}")
    redis_client.delete("users_all")

    return {"message": "User deleted"}