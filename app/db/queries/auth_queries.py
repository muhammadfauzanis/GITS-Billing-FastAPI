check_user_exists_query = "SELECT id FROM users WHERE email = %s"

insert_user_query = """
INSERT INTO users (email, client_id, role, is_password_set, supabase_auth_id) 
VALUES (%s, %s, %s, %s, %s) 
"""
get_user_by_email_query = """
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