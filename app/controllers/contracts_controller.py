import os
import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, EmailStr

from app.db.connection import get_db
from app.db.queries.contracts_queries import (
    DELETE_CONTRACT_BY_ID,
    GET_ALL_CONTRACTS,
    GET_CONTRACT_BY_ID,
    GET_SINGLE_CONTRACT_DETAILS,
    INSERT_CONTRACT,
    UPDATE_CONTRACT,
)
from app.middleware.auth_middleware import supabase

router = APIRouter()
SUPABASE_BUCKET_NAME = "contracts"


class ContractResponse(BaseModel):
    id: int
    client_name: str
    start_date: date
    end_date: date
    status: str
    notes: Optional[str]
    file_url: str
    created_at: datetime


class ContractDetailsResponse(BaseModel):
    id: int
    client_id: int
    client_name: str
    start_date: date
    end_date: date
    notes: Optional[str]
    file_url: str
    client_contact_emails: List[EmailStr]
    created_at: datetime
    updated_at: datetime


def get_contract_status(end_date: date) -> str:
    today = date.today()
    if end_date < today:
        return "Expired"
    if end_date <= today + timedelta(days=30):
        return "Expiring Soon"
    return "Active"


@router.get("/", response_model=List[ContractResponse])
def get_all_contracts(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_ALL_CONTRACTS)
    contracts_raw = cursor.fetchall()
    db.close()

    response = []
    for row in contracts_raw:
        contract_id, client_name, start_date, end_date, notes, file_url, created_at = (
            row
        )
        response.append(
            ContractResponse(
                id=contract_id,
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                status=get_contract_status(end_date),
                notes=notes,
                file_url=file_url,
                created_at=created_at,
            )
        )
    return response


@router.get("/{contract_id}", response_model=ContractDetailsResponse)
def get_contract_details(
    contract_id: int, request: Request, db: Annotated = Depends(get_db)
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_SINGLE_CONTRACT_DETAILS, (contract_id,))
    contract = cursor.fetchone()
    db.close()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    (
        id,
        client_id,
        client_name,
        start_date,
        end_date,
        notes,
        file_url,
        client_emails,
        created_at,
        updated_at,
    ) = contract

    return ContractDetailsResponse(
        id=id,
        client_id=client_id,
        client_name=client_name,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
        file_url=file_url,
        client_contact_emails=client_emails,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.post("/")
def create_contract(
    request: Request,
    client_id: Annotated[int, Form()],
    start_date: Annotated[date, Form()],
    end_date: Annotated[date, Form()],
    client_contact_emails: Annotated[List[EmailStr], Form()],
    file: UploadFile = File(...),
    notes: Annotated[Optional[str], Form()] = None,
    db: Annotated = Depends(get_db),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    try:
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_path = f"GCP/{file_name}"

        supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
            path=file_path,
            file=file.file.read(),
            file_options={"content-type": file.content_type},
        )

        file_url_response = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(
            file_path
        )

        cursor = db.cursor()
        cursor.execute(
            INSERT_CONTRACT,
            (
                client_id,
                start_date,
                end_date,
                notes,
                client_contact_emails,
                file_url_response,
            ),
        )
        new_id = cursor.fetchone()[0]
        db.commit()

        return {"message": "Contract created successfully", "contractId": new_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        db.close()


@router.patch("/{contract_id}")
def update_contract(
    contract_id: int,
    request: Request,
    db: Annotated = Depends(get_db),
    client_id: Annotated[Optional[int], Form()] = None,
    start_date: Annotated[Optional[date], Form()] = None,
    end_date: Annotated[Optional[date], Form()] = None,
    client_contact_emails: Annotated[Optional[List[EmailStr]], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
    file: Optional[UploadFile] = File(None),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_SINGLE_CONTRACT_DETAILS, (contract_id,))
    result = cursor.fetchone()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    existing_contract = ContractDetailsResponse.parse_obj(
        dict(zip([desc[0] for desc in cursor.description], result))
    )
    new_file_url = existing_contract.file_url

    try:
        if file:
            if existing_contract.file_url:
                old_file_path = existing_contract.file_url.split(
                    f"{SUPABASE_BUCKET_NAME}/"
                )[1]
                supabase.storage.from_(SUPABASE_BUCKET_NAME).remove([old_file_path])

            file_extension = os.path.splitext(file.filename)[1]
            new_file_name = f"{uuid.uuid4()}{file_extension}"
            new_file_path = f"GCP/{new_file_name}"

            supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
                path=new_file_path,
                file=file.file.read(),
                file_options={"content-type": file.content_type},
            )
            new_file_url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(
                new_file_path
            )

        update_data = (
            client_id if client_id is not None else existing_contract.client_id,
            start_date if start_date is not None else existing_contract.start_date,
            end_date if end_date is not None else existing_contract.end_date,
            notes if notes is not None else existing_contract.notes,
            (
                client_contact_emails
                if client_contact_emails is not None
                else existing_contract.client_contact_emails
            ),
            new_file_url,
            contract_id,
        )

        cursor.execute(UPDATE_CONTRACT, update_data)
        db.commit()
        return {"message": "Contract updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        db.close()


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int, request: Request, db: Annotated = Depends(get_db)
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_CONTRACT_BY_ID, (contract_id,))
    contract = cursor.fetchone()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    try:
        file_url = contract[0]
        if file_url:
            try:
                file_path = file_url.split(f"{SUPABASE_BUCKET_NAME}/")[1]
                response_list = supabase.storage.from_(SUPABASE_BUCKET_NAME).remove(
                    [file_path]
                )
                if (
                    response_list
                    and isinstance(response_list, list)
                    and len(response_list) > 0
                ):
                    first_item = response_list[0]
                    if isinstance(first_item, dict) and first_item.get("error"):
                        raise Exception(f"Supabase error: {first_item['error']}")
            except IndexError:
                print(f"Warning: Could not parse file_path from URL: {file_url}")
            except Exception as e:
                raise e

        cursor.execute(DELETE_CONTRACT_BY_ID, (contract_id,))
        db.commit()
        return {"message": f"Contract with ID {contract_id} has been deleted."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        cursor.close()
        db.close()
