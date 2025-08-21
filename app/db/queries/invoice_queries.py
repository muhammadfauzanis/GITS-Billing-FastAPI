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

# Query for Admin change invoices status

COUNT_INVOICES_FOR_ADMIN = """
    SELECT COUNT(i.id)
    FROM invoices i
    WHERE
        (%s IS NULL OR i.status = %s) AND
        (%s IS NULL OR i.client_id = %s) AND
        (%s IS NULL OR EXTRACT(MONTH FROM i.invoice_period) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM i.invoice_period) = %s);
"""

# Query BARU untuk mengambil data invoice per halaman
GET_PAGINATED_INVOICES_FOR_ADMIN = """
    SELECT
        i.id, i.invoice_number, c.name AS client_name, i.invoice_period,
        i.due_date, i.total_amount, i.status, i.proof_of_payment_url
    FROM invoices i
    JOIN clients c ON i.client_id = c.id
    WHERE
        (%s IS NULL OR i.status = %s) AND
        (%s IS NULL OR i.client_id = %s) AND
        (%s IS NULL OR EXTRACT(MONTH FROM i.invoice_period) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM i.invoice_period) = %s)
    ORDER BY DATE_TRUNC('month', i.invoice_period) DESC, i.id ASC
    LIMIT %s OFFSET %s;
"""

ADMIN_UPDATE_INVOICE_DETAILS = """
    UPDATE invoices
    SET
        status = %s,
        payment_date = %s,
        payment_notes = %s
    WHERE id = %s;
"""
