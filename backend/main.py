"""
FastAPI Backend for UK Grocery Compare
Handles user authentication and shopping list management
"""
import os
import sys
import jwt

# Add project root to path so matcher package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matcher.matcher import match as matcher_match, search as matcher_search, find_substitutes as matcher_find_substitutes
from matcher.matcher import _load as matcher_load
import matcher.matcher as _matcher_module
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, EmailStr

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/grocery_db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    shopping_lists = relationship("ShoppingList", back_populates="user", cascade="all, delete-orphan")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="shopping_lists")
    items = relationship("ListItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ListItem(Base):
    __tablename__ = "list_items"
    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    shopping_list = relationship("ShoppingList", back_populates="items")


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ListItemCreate(BaseModel):
    item_name: str
    quantity: float


class ShoppingListCreate(BaseModel):
    name: str
    items: List[ListItemCreate] = []


class ShoppingListUpdate(BaseModel):
    name: Optional[str] = None
    items: Optional[List[ListItemCreate]] = None


class ListItemResponse(BaseModel):
    id: int
    item_name: str
    quantity: float
    class Config:
        from_attributes = True


class ShoppingListResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    items: List[ListItemResponse]
    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    name: str
    name_clean: str
    store: str
    price: float
    price_per_100: Optional[float] = None
    brand: Optional[str] = None
    query: Optional[str] = None
    similarity: float
    confident: bool


class SearchResult(BaseModel):
    name: str
    name_clean: Optional[str] = None
    store: str
    price: float
    price_per_100: Optional[float] = None
    brand: Optional[str] = None
    query: Optional[str] = None


class SubstituteResult(BaseModel):
    substitute_name: str
    substitute_store: str
    substitute_brand: Optional[str] = None
    substitute_price: float
    original_price: float
    saving: float
    saving_pct: float
    cosine_similarity: float


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auth helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(email: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Create FastAPI app
app = FastAPI(title="UK Grocery Compare API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes
@app.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(email=user.email, hashed_password=pwd_context.hash(user.password))
    db.add(db_user)
    db.commit()
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer"}


@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@app.get("/lists", response_model=List[ShoppingListResponse])
def get_lists(current_user: User = Depends(get_current_user)):
    return current_user.shopping_lists


@app.post("/lists", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
def create_list(list_data: ShoppingListCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shopping_list = ShoppingList(name=list_data.name, user_id=current_user.id)
    db.add(shopping_list)
    db.commit()
    db.refresh(shopping_list)
    for item in list_data.items:
        db.add(ListItem(list_id=shopping_list.id, item_name=item.item_name, quantity=item.quantity))
    db.commit()
    db.refresh(shopping_list)
    return shopping_list


@app.get("/lists/{list_id}", response_model=ShoppingListResponse)
def get_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lst = db.query(ShoppingList).filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@app.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(list_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lst = db.query(ShoppingList).filter(ShoppingList.id == list_id, ShoppingList.user_id == current_user.id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    db.delete(lst)
    db.commit()


# ── Matcher endpoints ────────────────────────────────────────────────────────
from fastapi import Query as QueryParam


@app.get("/match-best")
def match_best_product(q: str = QueryParam(..., min_length=1), store: str = None):
    """
    Returns the single best match per store for a query.
    If 'store' is provided, returns only the best match from that store.
    matcher_match returns results sorted by similarity descending, so the
    first result seen for each store is already its best match.
    Includes results with similarity >= 0.5 so all relevant stores appear.
    """
    results = matcher_match(q, top_k=50)
    if not results:
        return []

    if store:
        for r in results:
            if r['store'] == store and (r.get('confident', False) or r['similarity'] >= 0.5):
                return [r]
        return []

    best_per_store = {}
    for r in results:
        s = r['store']
        if s not in best_per_store:
            if r.get('confident', False) or r['similarity'] >= 0.5:
                best_per_store[s] = r

    return list(best_per_store.values())


@app.get("/match", response_model=List[MatchResult])
def match_products(q: str = QueryParam(..., min_length=1), top_k: int = 10):
    """
    Smart product matching using the fine-tuned sentence transformer.
    Returns products sorted by similarity, with a 'confident' flag
    indicating whether the match exceeds TAU_MATCH (0.85).
    """
    results = matcher_match(q, top_k=top_k)
    return results


@app.get("/search", response_model=List[SearchResult])
def search_products(
    q: str = QueryParam(..., min_length=1),
    store: str = None,
    top_k: int = 20,
):
    """
    Text search fallback. Case-insensitive substring match on product names.
    Optionally filter by store.
    """
    results = matcher_search(q, store=store, top_k=top_k)
    return results


@app.get("/substitutes", response_model=List[SubstituteResult])
def get_substitutes(
    product: str = QueryParam(...),
    store: str = QueryParam(...),
    top_k: int = 5,
):
    """
    Find cheaper substitutes for a specific product at a specific store.
    Returns products in the substitution similarity band that are cheaper.
    """
    results = matcher_find_substitutes(product, store, top_k=top_k)
    return results


@app.get("/stores")
def get_stores():
    """Return list of available stores from the catalogue."""
    matcher_load()
    return sorted(_matcher_module._catalogue["store"].unique().tolist())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)