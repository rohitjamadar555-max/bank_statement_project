BANK_CONFIGS = {
    "generic_signed": {
        "column_map": {
            "Date": "date",
            "Description": "description",
            "Amount": "amount",
            "Type": "transaction_type",
            "Payment_Mode": "payment_mode",
            "Balance": "balance",
        },
        "amount_mode": "signed",
        "date_format": None,
        "currency": "INR",
    },
    "debit_credit_bank": {
        "column_map": {
            "Txn Date": "date",
            "Narration": "description",
            "Debit": "debit",
            "Credit": "credit",
            "Closing Balance": "balance",
        },
        "amount_mode": "debit_credit",
        "date_format": "%d/%m/%Y",
        "currency": "INR",
    },
}
