from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.db.connection import get_db
from app.db.queries.settings_queries import (
    GET_ALL_INTERNAL_EMAILS,
    INSERT_INTERNAL_EMAIL,
    DELETE_INTERNAL_EMAIL_BY_VALUE,
)

router = APIRouter()


class EmailSchema(BaseModel):
    email: EmailStr


class EmailListResponse(BaseModel):
    emails: List[str]


@router.get("/internal-emails", response_model=EmailListResponse)
def get_internal_emails(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_ALL_INTERNAL_EMAILS)
    results = cursor.fetchall()
    db.close()

    email_list = [row[0] for row in results]
    return EmailListResponse(emails=email_list)


@router.post("/internal-emails")
def add_internal_email(
    payload: EmailSchema,
    request: Request,
    db: Annotated = Depends(get_db),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    try:
        cursor = db.cursor()
        cursor.execute(INSERT_INTERNAL_EMAIL, (payload.email,))
        db.commit()
        return {"message": f"Email '{payload.email}' added successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        cursor.close()
        db.close()


@router.delete("/internal-emails")
def delete_internal_email(
    payload: EmailSchema,
    request: Request,
    db: Annotated = Depends(get_db),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    try:
        cursor = db.cursor()
        cursor.execute(DELETE_INTERNAL_EMAIL_BY_VALUE, (payload.email,))

        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found to delete.",
            )

        db.commit()
        return {"message": f"Email '{payload.email}' deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        cursor.close()
        db.close()
