COUNT_ALL_CONTRACTS = """
    SELECT COUNT(c.id)
    FROM contracts c
    WHERE 
        (%s IS NULL OR EXTRACT(MONTH FROM c.end_date) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM c.end_date) = %s);
"""

GET_PAGINATED_CONTRACTS = """
    SELECT
        c.id,
        cl.name AS client_name,
        c.start_date,
        c.end_date,
        c.notes,
        c.file_url,
        c.created_at
    FROM contracts c
    JOIN clients cl ON c.client_id = cl.id
    WHERE 
        (%s IS NULL OR EXTRACT(MONTH FROM c.end_date) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM c.end_date) = %s)
    ORDER BY c.end_date DESC
    LIMIT %s OFFSET %s;
"""

GET_CONTRACT_BY_ID = """
    SELECT file_url FROM contracts WHERE id = %s;
"""

GET_SINGLE_CONTRACT_DETAILS = """
    SELECT
        c.id, c.client_id, cl.name as client_name, c.start_date, c.end_date, c.notes,
        c.file_url, c.client_contact_emails,
        c.created_at, c.updated_at
    FROM contracts c
    JOIN clients cl ON c.client_id = cl.id
    WHERE c.id = %s;
"""

INSERT_CONTRACT = """
    INSERT INTO contracts (
        client_id, start_date, end_date, notes,
        client_contact_emails, file_url
    ) VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id;
"""

UPDATE_CONTRACT = """
    UPDATE contracts
    SET
        client_id = %s,
        start_date = %s,
        end_date = %s,
        notes = %s,
        client_contact_emails = %s,
        file_url = %s,
        updated_at = NOW()
    WHERE id = %s;
"""

DELETE_CONTRACT_BY_ID = """
    DELETE FROM contracts WHERE id = %s;
"""
