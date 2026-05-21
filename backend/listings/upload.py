from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import os
import uuid
from audit.audit import log_action
from server import engine
from sqlmodel import Session
from auth.dependencies import get_current_user_id
from pydantic import BaseModel

UPLOAD_DIR = "listings/photos"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

router = APIRouter()

class ImageUploadOut(BaseModel):
    url: str

@router.post("/upload-image", response_model=ImageUploadOut, status_code=200)
def upload_image(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    with Session(engine) as session:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            log_action(
                session=session,
                user_id=user_id,
                action="upload_image",
                target_type="listing_photo",
                success=False,
                status_code=400,
                details={"reason": "invalid_file_type"}
            )
            session.commit()
            raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

        # Validate file size
        contents = file.file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")
        

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        ext = file.content_type.split("/")[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        url = filename  # Store only the filename, not full URL

        log_action(
            session=session,
            user_id=user_id,
            action="upload_image",
            target_type="listing_photo",
            success=True,
            status_code=201,
            details={
                "filename": filename,
                "content_type": file.content_type
            }
        )

        session.commit()

        return {"url": url}