import os

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import get_db

load_dotenv()

app = FastAPI(title="SaaS Messenger Bot API")
templates = Jinja2Templates(directory="templates")


class MessagePayload(BaseModel):
    page_id: str
    sender_id: str
    message_text: str
    access_token: str


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# FIX: We now check if the user exists, and create them if they don't!
@app.post("/api/products")
async def add_product(
    name: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    db: Session = Depends(get_db),
):
    # 1. Check if our dummy user (ID: 1) exists in the database
    user = db.query(models.User).filter(models.User.id == 1).first()

    # 2. If the user doesn't exist, create them so the database is happy
    if not user:
        user = models.User(id=1, email="testuser@example.com")
        db.add(user)
        db.commit()  # Save the user to the database

    # 3. Now it is safe to add the product linked to user_id=1
    new_product = models.Product(
        name=name, description=description, price=price, user_id=1
    )
    db.add(new_product)
    db.commit()

    return {"message": "Product added successfully!"}


@app.post("/api/process_message")
async def process_message(payload: MessagePayload, db: Session = Depends(get_db)):

    # A. Fetch products for this specific user from the database
    products = db.query(models.Product).filter(models.Product.user_id == 1).all()

    # Format the products into a readable string for the AI
    if products:
        context = "\n".join(
            [f"- {p.name}: {p.description} (Price: {p.price})" for p in products]
        )
    else:
        context = "No products found in the database for this business."

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "your-key-here")

    # B. Call OpenRouter AI to generate a response
    async with httpx.AsyncClient() as client:
        ai_response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "SaaS Messenger Bot",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful customer service AI. Answer the user's question using ONLY this context: {context}. If the answer is not in the context, politely say you don't have that information and suggest contacting human support. Keep replies friendly and concise.",
                    },
                    {"role": "user", "content": payload.message_text},
                ],
            },
        )

        ai_reply = ai_response.json()["choices"][0]["message"]["content"]

    # C. Send the AI's reply back to the user via Facebook Graph API
    await client.post(
        f"https://graph.facebook.com/v20.0/me/messages?access_token={payload.access_token}",
        json={"recipient": {"id": payload.sender_id}, "message": {"text": ai_reply}},
    )

    return {"status": "success", "reply": ai_reply}
