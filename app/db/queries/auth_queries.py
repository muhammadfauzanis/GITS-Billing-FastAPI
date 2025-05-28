check_user_exists_query = "SELECT id FROM users WHERE email = %s"

insert_user_query = """
INSERT INTO users (email, password, client_id, role, is_password_set)
VALUES (%s, %s, %s, %s, FALSE)
"""

get_user_by_email_query = """
SELECT id, email, password, role, client_id, is_password_set 
FROM users 
WHERE email = %s
"""
