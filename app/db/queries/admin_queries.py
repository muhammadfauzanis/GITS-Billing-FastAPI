GET_ALL_CLIENT_NAMES = """
SELECT id, name FROM clients ORDER BY name ASC
"""

GET_ALL_USERS_INFO = """
SELECT 
    u.id,
    u.email,
    u.role,
    c.name AS client_name,
    u.is_password_set,
    u.created_at
FROM users u
LEFT JOIN clients c ON u.client_id = c.id
ORDER BY u.created_at ASC;
"""

DELETE_USER_BY_ID = """
DELETE FROM users
WHERE id = %s
"""
