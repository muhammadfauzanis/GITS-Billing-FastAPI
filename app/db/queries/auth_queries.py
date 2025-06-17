CHECK_USER_EXIST= """
SELECT id FROM users WHERE email = %s
"""

INSERT_USER_QUERY = """
INSERT INTO users (email, client_id, role, is_password_set, supabase_auth_id) 
VALUES (%s, %s, %s, %s, %s) 
"""
GET_USER_BY_EMAIL = """
SELECT id, email, password, role, client_id, is_password_set
FROM users
WHERE email = %s
"""
GET_USER_PASSWORD_AND_STATUS = """
SELECT password, is_password_set FROM users WHERE id = %s;
"""
UPDATE_USER_PASSWORD = """
UPDATE users SET password = %s, is_password_set = %s WHERE id = %s;
"""