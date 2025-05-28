from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated
from app.db.connection import get_db
from app.db.queries.admin_queries import GET_ALL_CLIENT_NAMES
from app.db.queries.admin_queries import GET_ALL_USERS_INFO
from app.db.queries.admin_queries import DELETE_USER_BY_ID

router = APIRouter() 

@router.get("/clients")
def get_all_clients(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    cursor = db.cursor()
    cursor.execute(GET_ALL_CLIENT_NAMES)
    results = cursor.fetchall()

    clients = [{"id": row[0], "name": row[1]} for row in results]
    return {"clients": clients}

@router.get("/users")
def get_all_users(request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_USERS_INFO)
    results = cursor.fetchall()

    users = []
    for row in results:
        id, email, role, client_name, is_password_set, created_at = row
        users.append({
            "id":id,
            "email": email,
            "role": role,
            "client": client_name or "-",
            "status": "Aktif" if is_password_set else "Nonaktif",
            "createdAt": created_at.strftime("%-d/%-m/%Y") 
        })

    return {"users": users}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(DELETE_USER_BY_ID, (user_id,))
    db.commit()

    return {"message": f"User with ID {user_id} has been deleted successfully."}