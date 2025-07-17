GET_UNREAD_NOTIFICATIONS_BY_CLIENT_ID = """
    SELECT id, message, created_at
    FROM notifications
    WHERE client_id = %s AND is_read = FALSE
    ORDER BY created_at DESC;
"""

MARK_NOTIFICATION_AS_READ = """
    UPDATE notifications SET is_read = TRUE WHERE id = %s AND client_id = %s;
"""

DELETE_NOTIFICATION_BY_ID = """
    DELETE FROM notifications WHERE id = %s AND client_id = %s;
"""