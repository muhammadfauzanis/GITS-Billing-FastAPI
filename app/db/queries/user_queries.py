GET_CLIENT_NAME_BY_ID = """
    SELECT name FROM clients WHERE id = %s
"""

GET_USER_PROFILE_BY_ID = """
    SELECT
        u.email,
        c.name AS client_name,
        u.whatsapp_id
    FROM users u
    JOIN clients c ON u.client_id = c.id
    WHERE u.id = %s;
"""

UPDATE_USER_WHATSAPP = """
    UPDATE users SET whatsapp_id = %s WHERE id = %s;
"""
