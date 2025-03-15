from pydantic import BaseModel


class User(BaseModel):
    username: str
    name: str
    surname: str
    email: str
    password: str
    profile_photo: str | None = None
    latitude: float | None = None  # Опционально
    longitude: float | None = None

class UserInteraction(BaseModel):
    user_id: int
    target_id: int
    interaction_type: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    username: str
    name: str
    surname: str
    email: str
    profile_photo: str | None


class Location(BaseModel):
    latitude: float
    longitude: float

class LikeRequest(BaseModel):
    target_user_id: int