GET_ALL_CLIENT_NAMES = """
    SELECT id, name FROM clients ORDER BY name ASC;
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
    DELETE FROM users WHERE id = %s;
"""

CHECK_USER_EXISTS_BY_ID = """
    SELECT id FROM users WHERE id = %s;
"""

UPDATE_USER_CLIENT_ID = """
    UPDATE users SET client_id = %s WHERE id = %s;
"""