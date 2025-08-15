GET_ALL_INTERNAL_EMAILS = """
    SELECT email FROM internal_notification_emails ORDER BY email ASC;
"""

INSERT_INTERNAL_EMAIL = """
    INSERT INTO internal_notification_emails (email) VALUES (%s)
    ON CONFLICT (email) DO NOTHING;
"""

DELETE_INTERNAL_EMAIL_BY_VALUE = """
    DELETE FROM internal_notification_emails WHERE email = %s;
"""
