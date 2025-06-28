from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Environment, PackageLoader, select_autoescape
import os

app = FastAPI(title="Portfolio Backend API")

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME = "princee0391@gmail.com",
    MAIL_PASSWORD = "pege ccfk lint lrvp",  # Your Gmail app password
    MAIL_FROM = "princee0391@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True
)

# Template environment
env = Environment(
    loader=PackageLoader('backend', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "portfolio_db"

# Database connection
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    app.mongodb = app.mongodb_client[DATABASE_NAME]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

# Models
class ContactForm(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    subject: Optional[str] = None
    message: str
    created_at: datetime = datetime.utcnow()

class FeedbackForm(BaseModel):
    name: str
    email: EmailStr
    rating: int
    feedback: str
    created_at: datetime = datetime.utcnow()

# Email sending functions
async def send_contact_email(contact: ContactForm):
    template = env.get_template('contact_email.html')
    html_content = template.render(
        full_name=contact.full_name,
        email=contact.email,
        phone_number=contact.phone_number or "Not provided",
        subject=contact.subject or "No subject",
        message=contact.message,
        created_at=contact.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    message = MessageSchema(
        subject=f"New Contact Form Submission from {contact.full_name}",
        recipients=["princee0391@gmail.com"],  # Your email
        body=html_content,
        subtype="html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_feedback_email(feedback: FeedbackForm):
    template = env.get_template('feedback_email.html')
    html_content = template.render(
        name=feedback.name,
        email=feedback.email,
        rating=feedback.rating,
        feedback=feedback.feedback,
        created_at=feedback.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    message = MessageSchema(
        subject=f"New Feedback from {feedback.name} - Rating: {feedback.rating}/5",
        recipients=["princee0391@gmail.com"],  # Your email
        body=html_content,
        subtype="html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)

# Routes
@app.post("/api/contact")
async def submit_contact(contact: ContactForm, background_tasks: BackgroundTasks):
    try:
        # Store in database
        result = await app.mongodb.contacts.insert_one(contact.dict())
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to submit contact form")
        
        # Send email in background
        background_tasks.add_task(send_contact_email, contact)
        
        return {"status": "success", "message": "Contact form submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackForm, background_tasks: BackgroundTasks):
    try:
        if not 1 <= feedback.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Store in database
        result = await app.mongodb.feedback.insert_one(feedback.dict())
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
        
        # Send email in background
        background_tasks.add_task(send_feedback_email, feedback)
        
        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 