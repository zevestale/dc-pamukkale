from fastapi import FastAPI, WebSocket, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from typing import List
from passlib.context import CryptContext
from fastapi import Request

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fake_users_db = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "message": ""})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if username in fake_users_db:
        return templates.TemplateResponse("login.html", {"request": request, "message": "Username already exists. Please choose another."})

    fake_users_db[username] = {
        "username": username,
        "password": pwd_context.hash(password)
    }
    return templates.TemplateResponse("login.html", {"request": request, "message": "User registered successfully! You can now log in."})

@app.post("/token", response_class=HTMLResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user['password']):
        return templates.TemplateResponse("login.html", {"request": request, "message": "Invalid username or password."})

    # Redirect to chat page with the username
    return RedirectResponse(url=f"/chat?username={form_data.username}", status_code=303)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, username: str):
    return templates.TemplateResponse("chat.html", {"request": request})

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.usernames: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.usernames[websocket] = username

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        del self.usernames[websocket]

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, username: str = None):
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{username}: {data}")  # Broadcast with username
    except:
        manager.disconnect(websocket)
