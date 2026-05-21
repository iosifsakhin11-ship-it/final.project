from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apscheduler.schedulers.background import BackgroundScheduler
from audit.cleanup import cleanup_old_logs

from auth.create_user import router as create_user_router
from auth.login import router as login_router
from auth.logout import router as logout_router
from favorites.create_favorite import router as create_favorite_router
from favorites.delete_favorite import router as delete_favorite_router
from listings.browse_listing import router as browse_listing_router
from listings.create_listing import router as create_listing_router
from listings.delete_listing import router as delete_listing_router
from listings.update_listing import router as update_listing_router
from favorites.view_favorites import router as view_favorites_router
from listings.view_details import router as view_details_router
from chats.send_message import router as send_message_router
from chats.get_chats import router as get_chats_router
from listings.upload import router as import_photos_router
from chats.bids.bid import router as bids_router
from chats.viewings.viewings import router as viewings_router
from chats.get_chat_details import router as get_chat_details_router
from auth.get_user import router as get_user_me
from auth.user_update import router as user_update_router
from reports.inquiries import router as reports_router
from admin.users import router as admin_users_router
from admin.listings import router as admin_listings_router
from subscriptions.subscriptions import router as sub_router
from payments.payments import router as payments_router

from server import engine
from sqlmodel import SQLModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        cleanup_old_logs,
        trigger="cron",
        hour=2,
        minute=0
    )
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

app.mount("/listings/photos", StaticFiles(directory="listings"), name="photos")

app.include_router(login_router)
app.include_router(create_user_router)
app.include_router(create_listing_router)
app.include_router(logout_router)
app.include_router(create_favorite_router)
app.include_router(delete_favorite_router)
app.include_router(delete_listing_router)
app.include_router(browse_listing_router)
app.include_router(update_listing_router)
app.include_router(view_favorites_router)
app.include_router(view_details_router)
app.include_router(send_message_router)
app.include_router(get_chats_router)
app.include_router(import_photos_router)
app.include_router(bids_router)
app.include_router(viewings_router)
app.include_router(get_chat_details_router)
app.include_router(get_user_me)
app.include_router(reports_router)
app.include_router(admin_listings_router)
app.include_router(admin_users_router)
app.include_router(sub_router)
app.include_router(payments_router)
app.include_router(user_update_router)

# Create all tables — runs after all models are imported via router imports above
SQLModel.metadata.create_all(engine)