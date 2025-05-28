GET_CLIENT_NAME_BY_ID = """
    SELECT name FROM clients WHERE id = %s
"""

GET_ALL_CLIENT_NAMES = """
SELECT id, name FROM clients ORDER BY name ASC
"""
