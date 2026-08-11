import logging
import os
import platform
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import psutil
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from auth import (
    create_access_token,
    get_current_admin,
    get_current_user,
    hash_password,
    verify_password,
)
from database.session import create_db, get_session
from models.product import (
    Product,
    ProductCreate,
    ProductUpdate,
)
from models.user import (
    User,
    UserRegister,
    UserResponse,
)



# ENVIRONMENT


load_dotenv()



# APPLICATION

app = FastAPI(
    title="Product API",
    description="Product management API with authentication",
    version="1.0.0"
)

start_time = time.time()


# LOGGING


LOG_FILE = os.getenv(
    "LOG_FILE",
    "app.log"
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=10485760,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# DATABASE STARTUP

@app.on_event("startup")
def on_startup():
    create_db()



# REQUEST LOGGING

@app.middleware("http")
async def log_requests(
    request: Request,
    call_next
):
    request_start = time.time()

    response = await call_next(request)

    process_time = (
        time.time() - request_start
    )

    logger.info(
        f"{request.method} "
        f"{request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response



# ERROR HANDLING

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors()
        }
    )


@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc
):
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "message": "Resource not found"
        }
    )



# AUTHENTICATION

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    session: Session = Depends(get_session)
):
    existing_username = session.exec(
        select(User).where(
            User.username == user_data.username
        )
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    existing_email = session.exec(
        select(User).where(
            User.email == user_data.email
        )
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=hash_password(
            user_data.password
        ),
        is_admin=False
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user


@app.post("/login")
def login_user(
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    statement = select(User).where(
        User.username == username
    )

    user = session.exec(
        statement
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={
            "sub": user.username
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }



# PRODUCTS


@app.post(
    "/products",
    response_model=Product,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    product_data: ProductCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_user
    )
):
    if not product_data.name.strip():
        raise HTTPException(
            status_code=422,
            detail="Product name cannot be empty"
        )

    if product_data.price < 0:
        raise HTTPException(
            status_code=422,
            detail="Price cannot be negative"
        )

    if product_data.stock < 0:
        raise HTTPException(
            status_code=422,
            detail="Stock cannot be negative"
        )

    product = Product(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock
    )

    session.add(product)
    session.commit()
    session.refresh(product)

    return product


@app.get(
    "/products",
    response_model=list[Product]
)
def list_products(
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_user
    )
):
    products = session.exec(
        select(Product)
    ).all()

    return products


@app.get(
    "/products/{product_id}",
    response_model=Product
)
def get_product(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_user
    )
):
    product = session.get(
        Product,
        product_id
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


@app.patch(
    "/products/{product_id}",
    response_model=Product
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_user
    )
):
    product = session.get(
        Product,
        product_id
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product_data.name is not None:

        if not product_data.name.strip():
            raise HTTPException(
                status_code=422,
                detail="Product name cannot be empty"
            )

        product.name = product_data.name

    if product_data.description is not None:
        product.description = (
            product_data.description
        )

    if product_data.price is not None:

        if product_data.price < 0:
            raise HTTPException(
                status_code=422,
                detail="Price cannot be negative"
            )

        product.price = product_data.price

    if product_data.stock is not None:

        if product_data.stock < 0:
            raise HTTPException(
                status_code=422,
                detail="Stock cannot be negative"
            )

        product.stock = product_data.stock

    session.add(product)
    session.commit()
    session.refresh(product)

    return product


@app.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_user
    )
):
    product = session.get(
        Product,
        product_id
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    session.delete(product)
    session.commit()

    return None


# USERS


@app.get("/users")
def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(
        get_current_admin
    )
):
    users = session.exec(
        select(User)
    ).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
        for user in users
    ]



# MONITORING


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime": time.time() - start_time,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version()
        }
    }


@app.get("/metrics")
def get_metrics(
    current_user: User = Depends(
        get_current_admin
    )
):
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": (
            psutil.virtual_memory().percent
        ),
        "disk_usage": (
            psutil.disk_usage("/").percent
        )
    }