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

GET_CLIENTS_COUNT = """
    SELECT
        (SELECT COUNT(id) FROM clients) +
        (SELECT COUNT(id) FROM client_gw)
    AS total_clients;
"""

GET_CONTRACTS_STATS = """
    SELECT
        COUNT(*) FILTER (WHERE end_date >= CURRENT_DATE) AS total_active,
        COUNT(*) FILTER (WHERE end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') AS expiring_soon
    FROM (
        SELECT end_date FROM contracts
        UNION ALL
        SELECT end_date FROM contracts_gw
    ) AS all_contracts;
"""

GET_INVOICES_STATS = """
    SELECT
        COUNT(*) FILTER (WHERE status = 'pending') AS pending_invoices,
        COUNT(*) FILTER (WHERE status = 'overdue') AS overdue_invoices
    FROM invoices;
"""

GET_UPCOMING_RENEWALS = """
    SELECT id, client_name, end_date, 'GCP' as type FROM (
        SELECT c.id, cl.name as client_name, c.end_date
        FROM contracts c
        JOIN clients cl ON c.client_id = cl.id
        WHERE c.end_date >= CURRENT_DATE
    ) AS gcp_contracts
    UNION ALL
    SELECT id, client_name, end_date, 'GW' as type FROM (
        SELECT cg.id, cgw.client as client_name, cg.end_date
        FROM contracts_gw cg
        JOIN client_gw cgw ON cg.client_gw_id = cgw.id
        WHERE cg.end_date >= CURRENT_DATE
    ) AS gw_contracts
    ORDER BY end_date ASC
    LIMIT 5;
"""

GET_RECENT_INVOICES = """
    SELECT
        i.id,
        i.invoice_number,
        c.name AS client_name,
        i.total_amount,
        i.status,
        i.due_date
    FROM invoices i
    JOIN clients c ON i.client_id = c.id
    WHERE i.status IN ('pending', 'overdue')
    ORDER BY i.created_at DESC
    LIMIT 5;
"""
