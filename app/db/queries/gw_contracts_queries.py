COUNT_ALL_GW_CONTRACTS = """
    SELECT COUNT(c.id)
    FROM contracts_gw c
    WHERE 
        (%s IS NULL OR EXTRACT(MONTH FROM c.end_date) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM c.end_date) = %s);
"""

GET_PAGINATED_GW_CONTRACTS = """
    SELECT
        c.id,
        cl.client AS client_name,
        c.start_date,
        c.end_date,
        c.notes,
        c.file_url,
        c.created_at,
        cl.domain,
        cl.sku
    FROM contracts_gw c
    JOIN client_gw cl ON c.client_gw_id = cl.id
    WHERE 
        (%s IS NULL OR EXTRACT(MONTH FROM c.end_date) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM c.end_date) = %s)
    ORDER BY c.end_date DESC
    LIMIT %s OFFSET %s;
"""
GET_GW_CONTRACT_BY_ID = """
    SELECT file_url FROM contracts_gw WHERE id = %s;
"""

GET_SINGLE_GW_CONTRACT_DETAILS = """
    SELECT
        c.id, c.client_gw_id, cl.client as client_name, c.start_date, c.end_date, c.notes,
        c.file_url, c.client_contact_emails,
        c.created_at, c.updated_at
    FROM contracts_gw c
    JOIN client_gw cl ON c.client_gw_id = cl.id
    WHERE c.id = %s;
"""

INSERT_GW_CONTRACT = """
    INSERT INTO contracts_gw (
        client_gw_id, start_date, end_date, notes,
        client_contact_emails, file_url
    ) VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id;
"""

UPDATE_GW_CONTRACT = """
    UPDATE contracts_gw
    SET
        client_gw_id = %s,
        start_date = %s,
        end_date = %s,
        notes = %s,
        client_contact_emails = %s,
        file_url = %s,
        updated_at = NOW()
    WHERE id = %s;
"""

DELETE_GW_CONTRACT_BY_ID = """
    DELETE FROM contracts_gw WHERE id = %s;
"""

GET_ALL_GW_CLIENTS = """
    SELECT id, client as name FROM client_gw ORDER BY name ASC;
"""

GET_CLIENT_NAME_BY_ID_GW = """
    SELECT client FROM client_gw WHERE id = %s;
"""
