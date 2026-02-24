from typing import Any, Dict

INVOICE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": ["string", "null"]},
        "invoice_date": {"type": ["string", "null"]},
        "supplier_name": {"type": ["string", "null"]},
        "total_amount": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_name": {"type": ["string", "null"]},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                },
                "required": ["item_name", "quantity", "unit_price"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "invoice_number",
        "invoice_date",
        "supplier_name",
        "total_amount",
        "currency",
        "line_items",
    ],
    "additionalProperties": False,
}

PURCHASE_ORDER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "po_number": {"type": ["string", "null"]},
        "po_date": {"type": ["string", "null"]},
        "buyer_name": {"type": ["string", "null"]},
        "supplier_name": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
        "total_amount": {"type": ["number", "null"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_name": {"type": ["string", "null"]},
                    "part_number": {"type": ["string", "null"]},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                },
                "required": ["item_name", "part_number", "quantity", "unit_price"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["po_number", "po_date", "buyer_name", "supplier_name", "currency", "total_amount", "items"],
    "additionalProperties": False,
}

TECHNICAL_REPORT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "report_title": {"type": ["string", "null"]},
        "report_date": {"type": ["string", "null"]},
        "project_code": {"type": ["string", "null"]},
        "author": {"type": ["string", "null"]},
        "summary": {"type": ["string", "null"]},
        "findings": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "report_title",
        "report_date",
        "project_code",
        "author",
        "summary",
        "findings",
        "recommendations",
    ],
    "additionalProperties": False,
}

CONTRACT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "contract_number": {"type": ["string", "null"]},
        "effective_date": {"type": ["string", "null"]},
        "party_a": {"type": ["string", "null"]},
        "party_b": {"type": ["string", "null"]},
        "contract_value": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "key_terms": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["contract_number", "effective_date", "party_a", "party_b", "contract_value", "currency", "key_terms"],
    "additionalProperties": False,
}

UNKNOWN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": ["string", "null"]},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "key_points"],
    "additionalProperties": False,
}

SCHEMA_MAP: Dict[str, Dict[str, Any]] = {
    "invoice": INVOICE_SCHEMA,
    "purchase_order": PURCHASE_ORDER_SCHEMA,
    "technical_report": TECHNICAL_REPORT_SCHEMA,
    "contract": CONTRACT_SCHEMA,
    "unknown": UNKNOWN_SCHEMA,
}
