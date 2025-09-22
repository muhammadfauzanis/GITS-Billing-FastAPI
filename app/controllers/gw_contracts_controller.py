import os
import uuid
from datetime import date, datetime
from typing import Annotated, List, Optional
from math import ceil

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    Query,
)
from pydantic import BaseModel, EmailStr
from app.utils.helpers import get_contract_status, sanitize_filename

from app.db.connection import get_db
from app.db.queries.gw_contracts_queries import (
    DELETE_GW_CONTRACT_BY_ID,
    COUNT_ALL_GW_CONTRACTS,
    GET_PAGINATED_GW_CONTRACTS,
    GET_GW_CONTRACT_BY_ID,
    GET_SINGLE_GW_CONTRACT_DETAILS,
    INSERT_GW_CONTRACT,
    UPDATE_GW_CONTRACT,
    GET_CLIENT_NAME_BY_ID_GW,
)
from app.middleware.auth_middleware import supabase

router = APIRouter()
SUPABASE_BUCKET_NAME = "contracts"


class GWContractResponse(BaseModel):
    id: int
    client_name: str
    start_date: date
    end_date: date
    status: str
    notes: Optional[str]
    file_url: str
    created_at: datetime
    domain: Optional[str]
    sku: Optional[str]


class GWContractDetailsResponse(BaseModel):
    id: int
    client_gw_id: int
    client_name: str
    start_date: date
    end_date: date
    notes: Optional[str]
    file_url: str
    client_contact_emails: List[EmailStr]
    created_at: datetime
    updated_at: datetime


class PaginationResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int


class PaginatedGWContractResponse(BaseModel):
    pagination: PaginationResponse
    data: List[GWContractResponse]


@router.get("/", response_model=PaginatedGWContractResponse)
def get_all_gw_contracts(
    request: Request,
    db: Annotated = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    filter_params = (month, month, year, year)

    cursor.execute(COUNT_ALL_GW_CONTRACTS, filter_params)
    total_items = cursor.fetchone()[0]
    total_pages = ceil(total_items / limit)

    offset = (page - 1) * limit
    paginated_params = (*filter_params, limit, offset)
    cursor.execute(GET_PAGINATED_GW_CONTRACTS, paginated_params)
    contracts_raw = cursor.fetchall()
    db.close()

    response_data = []
    for row in contracts_raw:
        (
            contract_id,
            client_name,
            start_date,
            end_date,
            notes,
            file_url,
            created_at,
            domain,
            sku,
        ) = row
        response_data.append(
            GWContractResponse(
                id=contract_id,
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                status=get_contract_status(end_date),
                notes=notes,
                file_url=file_url,
                created_at=created_at,
                domain=domain,
                sku=sku,
            )
        )

    return PaginatedGWContractResponse(
        pagination=PaginationResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            limit=limit,
        ),
        data=response_data,
    )


@router.get("/{contract_gw_id}", response_model=GWContractDetailsResponse)
def get_gw_contract_details(
    contract_gw_id: int, request: Request, db: Annotated = Depends(get_db)
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_SINGLE_GW_CONTRACT_DETAILS, (contract_gw_id,))
    contract = cursor.fetchone()
    db.close()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    (
        id,
        client_gw_id,
        client_name,
        start_date,
        end_date,
        notes,
        file_url,
        client_emails,
        created_at,
        updated_at,
    ) = contract

    return GWContractDetailsResponse(
        id=id,
        client_gw_id=client_gw_id,
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
def create_gw_contract(
    request: Request,
    client_gw_id: Annotated[int, Form()],
    client_name: Annotated[str, Form()],
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
        year = start_date.year
        original_filename = sanitize_filename(file.filename)
        file_path = f"GW/{year}/{original_filename}"

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
            INSERT_GW_CONTRACT,
            (
                client_gw_id,
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


@router.patch("/{contract_gw_id}")
def update_gw_contract(
    contract_gw_id: int,
    request: Request,
    db: Annotated = Depends(get_db),
    client_gw_id: Annotated[Optional[int], Form()] = None,
    client_name: Annotated[Optional[str], Form()] = None,
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
    cursor.execute(GET_SINGLE_GW_CONTRACT_DETAILS, (contract_gw_id,))
    result = cursor.fetchone()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    existing_contract = GWContractDetailsResponse.parse_obj(
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

            final_client_id = (
                client_gw_id
                if client_gw_id is not None
                else existing_contract.client_gw_id
            )
            final_start_date = (
                start_date if start_date is not None else existing_contract.start_date
            )

            current_client_name = client_name
            if not current_client_name:
                cursor.execute(GET_CLIENT_NAME_BY_ID_GW, (final_client_id,))
                name_result = cursor.fetchone()
                current_client_name = (
                    name_result[0] if name_result else existing_contract.client_name
                )

            year = final_start_date.year
            original_filename = sanitize_filename(file.filename)
            new_file_path = f"GW/{year}/{original_filename}"

            supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
                path=new_file_path,
                file=file.file.read(),
                file_options={"content-type": file.content_type},
            )
            new_file_url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(
                new_file_path
            )

        update_data = (
            (
                client_gw_id
                if client_gw_id is not None
                else existing_contract.client_gw_id
            ),
            start_date if start_date is not None else existing_contract.start_date,
            end_date if end_date is not None else existing_contract.end_date,
            notes if notes is not None else existing_contract.notes,
            (
                client_contact_emails
                if client_contact_emails is not None
                else existing_contract.client_contact_emails
            ),
            new_file_url,
            contract_gw_id,
        )
        cursor.execute(UPDATE_GW_CONTRACT, update_data)
        db.commit()
        return {"message": "Contract updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        db.close()


@router.delete("/{contract_gw_id}")
def delete_gw_contract(
    contract_gw_id: int, request: Request, db: Annotated = Depends(get_db)
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    cursor = db.cursor()
    cursor.execute(GET_GW_CONTRACT_BY_ID, (contract_gw_id,))
    contract = cursor.fetchone()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found"
        )

    try:
        file_url = contract[0]
        if file_url:
            try:
                cleaned_url = file_url.split("?")[0]
                file_path = cleaned_url.split(f"{SUPABASE_BUCKET_NAME}/")[1]
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

        cursor.execute(DELETE_GW_CONTRACT_BY_ID, (contract_gw_id,))
        db.commit()
        return {"message": f"Contract with ID {contract_gw_id} has been deleted."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        cursor.close()
        db.close()
