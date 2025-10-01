GET_INVOICES_BY_CLIENT_ID = """
    -- Mengambil daftar invoice untuk klien tertentu.
    -- Invoice dengan status 'draft' atau 'rejected' tidak akan ditampilkan.
    SELECT
        id,
        invoice_number,
        invoice_period,
        total_amount,
        due_date,
        status, -- Status pembayaran (pending, paid, etc.)
        created_at
    FROM invoices
    WHERE
        client_id = %s
        AND approval_status NOT IN ('draft', 'rejected')
    ORDER BY invoice_period DESC;
"""

GET_INVOICE_DETAILS_BY_ID = """
    -- Mengambil detail dasar invoice, biasanya untuk mendapatkan path file.
    SELECT
        id,
        storage_path,
        client_id
    FROM invoices
    WHERE id = %s;
"""


COUNT_INVOICES_FOR_ADMIN = """
    -- Menghitung total invoice untuk pagination di dashboard admin.
    -- Memungkinkan filter berdasarkan status pembayaran, approval_status, client, dan periode.
    SELECT COUNT(i.id)
    FROM invoices i
    WHERE
        (%s IS NULL OR i.status = %s) AND
        (%s IS NULL OR i.approval_status = %s) AND
        (%s IS NULL OR i.client_id = %s) AND
        (%s IS NULL OR EXTRACT(MONTH FROM i.invoice_period) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM i.invoice_period) = %s);
"""

GET_PAGINATED_INVOICES_FOR_ADMIN = """
    -- Mengambil data invoice per halaman untuk ditampilkan di dashboard admin.
    -- Menampilkan kedua status untuk kejelasan.
    SELECT
        i.id,
        i.invoice_number,
        c.name AS client_name,
        i.invoice_period,
        i.due_date,
        i.total_amount,
        i.status, -- Status pembayaran
        i.approval_status, -- Status approval internal
        i.proof_of_payment_url
    FROM invoices i
    JOIN clients c ON i.client_id = c.id
    WHERE
        (%s IS NULL OR i.status = %s) AND
        (%s IS NULL OR i.approval_status = %s) AND
        (%s IS NULL OR i.client_id = %s) AND
        (%s IS NULL OR EXTRACT(MONTH FROM i.invoice_period) = %s) AND
        (%s IS NULL OR EXTRACT(YEAR FROM i.invoice_period) = %s)
    ORDER BY DATE_TRUNC('month', i.invoice_period) DESC, i.id ASC
    LIMIT %s OFFSET %s;
"""

ADMIN_UPDATE_PAYMENT_DETAILS = """
    -- Untuk admin mengupdate detail pembayaran setelah klien membayar.
    UPDATE invoices
    SET
        status = %s,
        payment_date = %s,
        payment_notes = %s,
        proof_of_payment_url = %s
    WHERE id = %s;
"""

GET_INVOICE_APPROVAL_STATUS_AND_CLIENT_ID = """
    -- Memeriksa status approval invoice sebelum melakukan aksi (approve/reject).
    SELECT approval_status, client_id FROM invoices WHERE id = %s;
"""

APPROVE_INVOICE = """
    -- Mengubah status approval menjadi 'approved' dan status pembayaran menjadi 'pending'.
    UPDATE invoices
    SET
        approval_status = 'approved',
        status = 'pending',
        approved_by = %s,
        approved_at = NOW()
    WHERE id = %s AND approval_status = 'draft';
"""

REJECT_INVOICE = """
    -- Mengubah status approval menjadi 'rejected' dan mencatat alasannya.
    UPDATE invoices
    SET
        approval_status = 'rejected',
        rejected_by = %s,
        rejected_at = NOW(),
        rejection_reason = %s
    WHERE id = %s AND approval_status = 'draft';
"""

SET_INVOICE_AS_SENT = """
    -- Dipanggil oleh n8n setelah invoice berhasil dikirim ke klien.
    UPDATE invoices
    SET
        status = 'sent',
        sent_at = NOW()
    WHERE id = %s AND approval_status = 'approved';
"""
