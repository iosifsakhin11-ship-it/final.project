# HomeFinder Portal — 5CM505 Software Engineering

A full-stack property listing web application where users can browse, list, favourite, bid on, and schedule viewings for residential, commercial, and rental properties. Authentication uses two-factor login: email + bcrypt password validation in step one, then a 6-digit OTP emailed to the user in step two.

## Tech Stack

| Layer    | Technology                                               |
|----------|----------------------------------------------------------|
| Frontend | React 18, Vite, Tailwind CSS, react-router, react-hot-toast |
| Backend  | Python 3.10, FastAPI, SQLModel, APScheduler              |
| Database | MariaDB 10+                                              |
| Auth     | Bcrypt password + email verification + 6-digit OTP (2FA) |
| Email    | fastapi-mail (SMTP)                                      |
| Testing  | pytest 8 + FastAPI TestClient                            |

## Setup

1. Create database: `mysql -u root -p < sql/setup_db.sql`
2. Configure: `cp backend/.env.example backend/.env` and fill in credentials
3. Backend: `cd backend && pip install -r ../requirements.txt && uvicorn main:app --reload`
4. Frontend: `cd homefinder && npm install && npm run dev`

Backend: http://localhost:8000 | API docs: http://localhost:8000/docs | Frontend: http://localhost:5173

## Project Structure

```
backend/          FastAPI (auth, listings, favorites, chats/bids/viewings, admin, audit, reports, subscriptions, payments)
homefinder/       React SPA (Login 2FA, Browse, Property, Favourites)
sql/              schema.sql (14 tables, clean DDL) + setup_db.sql
docs/uml/         PlantUML sources + PNGs
docs/reports/     SDS, SIS, SES documents
```

Full route documentation: `routes.txt` | Full Swagger: `http://localhost:8000/docs`
