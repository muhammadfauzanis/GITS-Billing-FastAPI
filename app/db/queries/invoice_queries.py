GET_INVOICES_BY_CLIENT_ID = """
    SELECT
        id,
        invoice_number,
        invoice_period,
        total_amount,
        due_date,
        status,
        created_at
    FROM invoices
    WHERE client_id = %s
    ORDER BY invoice_period DESC;
"""

GET_INVOICE_DETAILS_BY_ID = """
    SELECT
        id,
        storage_path,
        client_id
    FROM invoices
    WHERE id = %s;
"""

UPDATE_INVOICE_STATUS = """
    UPDATE invoices
    SET status = %s
    WHERE id = %s;
"""