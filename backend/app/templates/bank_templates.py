"""
Bank Template Definitions - Sample templates for banking documents.

Defines templates with their field schemas for:
- Bank guarantees
- Credit agreements
- Payment orders
- Account statements
"""

from typing import Any


# Bank template definitions
BANK_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "bank_guarantee",
        "name": "Bank Kafolati",
        "description": "Bank kafolati - korxona majburiyatlarini ta'minlash uchun",
        "organization": "Bank",
        "category": "Kafolat",
        "file_path": "templates/bank/bank_guarantee.docx",
        "preview_image": "templates/bank/bank_guarantee_preview.png",
        "tags": ["bank", "kafolat", "guarantee", "kredit"],
        "schema": {
            "fields": [
                {"name": "guarantee_number", "type": "string", "required": True, "description": "Kafolat raqami"},
                {"name": "issue_date", "type": "date", "required": True, "description": "Berilgan sana"},
                {"name": "expiry_date", "type": "date", "required": True, "description": "Amal qilish muddati"},
                {"name": "beneficiary_name", "type": "string", "required": True, "description": "Benefitsiar nomi"},
                {"name": "beneficiary_address", "type": "text", "required": False, "description": "Benefitsiar manzili"},
                {"name": "principal_name", "type": "string", "required": True, "description": "Prinsipal (qarzdor) nomi"},
                {"name": "principal_inn", "type": "string", "required": True, "description": "Prinsipal INN"},
                {"name": "guarantee_amount", "type": "number", "required": True, "description": "Kafolat summasi (so'm)"},
                {"name": "guarantee_amount_words", "type": "string", "required": False, "description": "Summa so'z bilan"},
                {"name": "contract_number", "type": "string", "required": False, "description": "Asosiy shartnoma raqami"},
                {"name": "contract_date", "type": "date", "required": False, "description": "Asosiy shartnoma sanasi"},
                {"name": "bank_name", "type": "string", "required": True, "description": "Bank nomi"},
                {"name": "bank_mfo", "type": "string", "required": True, "description": "Bank MFO"},
                {"name": "authorized_person", "type": "string", "required": True, "description": "Vakolatli shaxs"},
                {"name": "authorized_position", "type": "string", "required": True, "description": "Lavozimi"},
            ]
        },
    },
    {
        "id": "credit_agreement",
        "name": "Kredit Shartnomasi",
        "description": "Kredit shartnomasi - bank kreditlari uchun",
        "organization": "Bank",
        "category": "Kredit",
        "file_path": "templates/bank/credit_agreement.docx",
        "preview_image": "templates/bank/credit_agreement_preview.png",
        "tags": ["bank", "kredit", "credit", "loan", "shartnoma"],
        "schema": {
            "fields": [
                {"name": "agreement_number", "type": "string", "required": True, "description": "Shartnoma raqami"},
                {"name": "agreement_date", "type": "date", "required": True, "description": "Shartnoma sanasi"},
                {"name": "borrower_name", "type": "string", "required": True, "description": "Qarz oluvchi nomi"},
                {"name": "borrower_inn", "type": "string", "required": True, "description": "Qarz oluvchi INN"},
                {"name": "borrower_address", "type": "text", "required": True, "description": "Qarz oluvchi manzili"},
                {"name": "borrower_director", "type": "string", "required": True, "description": "Rahbar F.I.O"},
                {"name": "credit_amount", "type": "number", "required": True, "description": "Kredit summasi"},
                {"name": "credit_amount_words", "type": "string", "required": False, "description": "Summa so'z bilan"},
                {"name": "interest_rate", "type": "number", "required": True, "description": "Foiz stavkasi (%)"},
                {"name": "credit_term_months", "type": "number", "required": True, "description": "Kredit muddati (oy)"},
                {"name": "credit_purpose", "type": "text", "required": True, "description": "Kredit maqsadi"},
                {"name": "repayment_schedule", "type": "string", "required": False, "description": "Qaytarish jadvali"},
                {"name": "collateral_description", "type": "text", "required": False, "description": "Garov tavsifi"},
                {"name": "bank_name", "type": "string", "required": True, "description": "Bank nomi"},
                {"name": "bank_mfo", "type": "string", "required": True, "description": "Bank MFO"},
                {"name": "bank_account", "type": "string", "required": True, "description": "Bank hisobraqami"},
            ]
        },
    },
    {
        "id": "payment_order",
        "name": "To'lov Topshiriqnomasi",
        "description": "To'lov topshiriqnomasi - pul o'tkazmalari uchun",
        "organization": "Bank",
        "category": "To'lov",
        "file_path": "templates/bank/payment_order.docx",
        "preview_image": "templates/bank/payment_order_preview.png",
        "tags": ["bank", "tolov", "payment", "transfer", "topshiriqnoma"],
        "schema": {
            "fields": [
                {"name": "order_number", "type": "string", "required": True, "description": "Topshiriqnoma raqami"},
                {"name": "order_date", "type": "date", "required": True, "description": "Sana"},
                {"name": "payer_name", "type": "string", "required": True, "description": "To'lovchi nomi"},
                {"name": "payer_inn", "type": "string", "required": True, "description": "To'lovchi INN"},
                {"name": "payer_account", "type": "string", "required": True, "description": "To'lovchi hisobraqami"},
                {"name": "payer_bank", "type": "string", "required": True, "description": "To'lovchi banki"},
                {"name": "payer_mfo", "type": "string", "required": True, "description": "To'lovchi MFO"},
                {"name": "recipient_name", "type": "string", "required": True, "description": "Oluvchi nomi"},
                {"name": "recipient_inn", "type": "string", "required": True, "description": "Oluvchi INN"},
                {"name": "recipient_account", "type": "string", "required": True, "description": "Oluvchi hisobraqami"},
                {"name": "recipient_bank", "type": "string", "required": True, "description": "Oluvchi banki"},
                {"name": "recipient_mfo", "type": "string", "required": True, "description": "Oluvchi MFO"},
                {"name": "amount", "type": "number", "required": True, "description": "Summa"},
                {"name": "amount_words", "type": "string", "required": False, "description": "Summa so'z bilan"},
                {"name": "payment_purpose", "type": "text", "required": True, "description": "To'lov maqsadi"},
                {"name": "payment_code", "type": "string", "required": False, "description": "To'lov kodi"},
            ]
        },
    },
    {
        "id": "account_statement",
        "name": "Hisob Ko'chirma",
        "description": "Bank hisobvarag'i bo'yicha ko'chirma",
        "organization": "Bank",
        "category": "Hisobot",
        "file_path": "templates/bank/account_statement.xlsx",
        "preview_image": "templates/bank/account_statement_preview.png",
        "tags": ["bank", "hisob", "statement", "kochirma", "hisobot"],
        "schema": {
            "fields": [
                {"name": "account_number", "type": "string", "required": True, "description": "Hisob raqami"},
                {"name": "account_holder", "type": "string", "required": True, "description": "Hisob egasi"},
                {"name": "period_start", "type": "date", "required": True, "description": "Davr boshi"},
                {"name": "period_end", "type": "date", "required": True, "description": "Davr oxiri"},
                {"name": "opening_balance", "type": "number", "required": True, "description": "Ochilish qoldig'i"},
                {"name": "closing_balance", "type": "number", "required": True, "description": "Yopilish qoldig'i"},
                {"name": "total_debit", "type": "number", "required": False, "description": "Jami debet"},
                {"name": "total_credit", "type": "number", "required": False, "description": "Jami kredit"},
                {"name": "bank_name", "type": "string", "required": True, "description": "Bank nomi"},
                {"name": "bank_mfo", "type": "string", "required": True, "description": "Bank MFO"},
                {"name": "statement_date", "type": "date", "required": True, "description": "Ko'chirma sanasi"},
            ]
        },
    },
    {
        "id": "deposit_agreement",
        "name": "Depozit Shartnomasi",
        "description": "Bank depoziti shartnomasi",
        "organization": "Bank",
        "category": "Depozit",
        "file_path": "templates/bank/deposit_agreement.docx",
        "preview_image": "templates/bank/deposit_agreement_preview.png",
        "tags": ["bank", "depozit", "deposit", "omonat", "shartnoma"],
        "schema": {
            "fields": [
                {"name": "agreement_number", "type": "string", "required": True, "description": "Shartnoma raqami"},
                {"name": "agreement_date", "type": "date", "required": True, "description": "Shartnoma sanasi"},
                {"name": "depositor_name", "type": "string", "required": True, "description": "Omonatchi nomi"},
                {"name": "depositor_passport", "type": "string", "required": True, "description": "Passport seriya/raqami"},
                {"name": "depositor_address", "type": "text", "required": False, "description": "Manzil"},
                {"name": "depositor_phone", "type": "phone", "required": False, "description": "Telefon"},
                {"name": "deposit_amount", "type": "number", "required": True, "description": "Depozit summasi"},
                {"name": "deposit_term_months", "type": "number", "required": True, "description": "Muddat (oy)"},
                {"name": "interest_rate", "type": "number", "required": True, "description": "Foiz stavkasi (%)"},
                {"name": "interest_payment", "type": "string", "required": True, "description": "Foiz to'lash tartibi", 
                 "options": ["Oylik", "Choraklik", "Muddat oxirida"]},
                {"name": "maturity_date", "type": "date", "required": True, "description": "Tugash sanasi"},
                {"name": "bank_name", "type": "string", "required": True, "description": "Bank nomi"},
                {"name": "bank_mfo", "type": "string", "required": True, "description": "Bank MFO"},
            ]
        },
    },
    {
        "id": "loan_application",
        "name": "Kredit Uchun Ariza",
        "description": "Kredit olish uchun ariza shakli",
        "organization": "Bank",
        "category": "Kredit",
        "file_path": "templates/bank/loan_application.docx",
        "preview_image": "templates/bank/loan_application_preview.png",
        "tags": ["bank", "kredit", "ariza", "application", "loan"],
        "schema": {
            "fields": [
                {"name": "applicant_name", "type": "string", "required": True, "description": "Ariza beruvchi nomi"},
                {"name": "applicant_inn", "type": "string", "required": True, "description": "INN"},
                {"name": "applicant_address", "type": "text", "required": True, "description": "Manzil"},
                {"name": "applicant_phone", "type": "phone", "required": True, "description": "Telefon"},
                {"name": "applicant_email", "type": "email", "required": False, "description": "Email"},
                {"name": "business_type", "type": "string", "required": True, "description": "Faoliyat turi"},
                {"name": "annual_revenue", "type": "number", "required": True, "description": "Yillik daromad"},
                {"name": "requested_amount", "type": "number", "required": True, "description": "So'ralayotgan summa"},
                {"name": "loan_purpose", "type": "text", "required": True, "description": "Kredit maqsadi"},
                {"name": "requested_term", "type": "number", "required": True, "description": "So'ralayotgan muddat (oy)"},
                {"name": "collateral_type", "type": "string", "required": False, "description": "Garov turi",
                 "options": ["Ko'chmas mulk", "Avtotransport", "Uskunalar", "Boshqa"]},
                {"name": "collateral_value", "type": "number", "required": False, "description": "Garov qiymati"},
                {"name": "application_date", "type": "date", "required": True, "description": "Ariza sanasi"},
            ]
        },
    },
]


# Government/Tax templates
GOVERNMENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "tax_report_quarterly",
        "name": "Choraklik Soliq Hisoboti",
        "description": "Choraklik soliq hisoboti shakli",
        "organization": "Soliq",
        "category": "Hisobot",
        "file_path": "templates/government/tax_report_quarterly.xlsx",
        "preview_image": "templates/government/tax_report_preview.png",
        "tags": ["soliq", "tax", "hisobot", "report", "quarterly", "chorak"],
        "schema": {
            "fields": [
                {"name": "company_name", "type": "string", "required": True, "description": "Korxona nomi"},
                {"name": "inn", "type": "string", "required": True, "description": "INN"},
                {"name": "report_quarter", "type": "number", "required": True, "description": "Chorak (1-4)"},
                {"name": "report_year", "type": "number", "required": True, "description": "Yil"},
                {"name": "total_revenue", "type": "number", "required": True, "description": "Jami daromad"},
                {"name": "total_expenses", "type": "number", "required": True, "description": "Jami xarajatlar"},
                {"name": "taxable_income", "type": "number", "required": True, "description": "Soliqqqa tortiladigan daromad"},
                {"name": "tax_amount", "type": "number", "required": True, "description": "Soliq summasi"},
                {"name": "submission_date", "type": "date", "required": True, "description": "Topshirish sanasi"},
                {"name": "director_name", "type": "string", "required": True, "description": "Rahbar F.I.O"},
                {"name": "accountant_name", "type": "string", "required": True, "description": "Bosh hisobchi F.I.O"},
            ]
        },
    },
    {
        "id": "vat_declaration",
        "name": "QQS Deklaratsiyasi",
        "description": "Qo'shilgan qiymat solig'i deklaratsiyasi",
        "organization": "Soliq",
        "category": "Deklaratsiya",
        "file_path": "templates/government/vat_declaration.xlsx",
        "preview_image": "templates/government/vat_declaration_preview.png",
        "tags": ["soliq", "tax", "qqs", "vat", "deklaratsiya"],
        "schema": {
            "fields": [
                {"name": "company_name", "type": "string", "required": True, "description": "Korxona nomi"},
                {"name": "inn", "type": "string", "required": True, "description": "INN"},
                {"name": "report_month", "type": "number", "required": True, "description": "Oy"},
                {"name": "report_year", "type": "number", "required": True, "description": "Yil"},
                {"name": "sales_amount", "type": "number", "required": True, "description": "Sotish summasi"},
                {"name": "vat_on_sales", "type": "number", "required": True, "description": "Sotishdan QQS"},
                {"name": "purchases_amount", "type": "number", "required": True, "description": "Xarid summasi"},
                {"name": "vat_on_purchases", "type": "number", "required": True, "description": "Xariddan QQS"},
                {"name": "vat_payable", "type": "number", "required": True, "description": "To'lanadigan QQS"},
                {"name": "submission_date", "type": "date", "required": True, "description": "Topshirish sanasi"},
            ]
        },
    },
]


# Contract templates
CONTRACT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "service_contract",
        "name": "Xizmat Ko'rsatish Shartnomasi",
        "description": "Xizmat ko'rsatish shartnomasi",
        "organization": "Umumiy",
        "category": "Shartnoma",
        "file_path": "templates/contracts/service_contract.docx",
        "preview_image": "templates/contracts/service_contract_preview.png",
        "tags": ["shartnoma", "contract", "xizmat", "service"],
        "schema": {
            "fields": [
                {"name": "contract_number", "type": "string", "required": True, "description": "Shartnoma raqami"},
                {"name": "contract_date", "type": "date", "required": True, "description": "Shartnoma sanasi"},
                {"name": "client_name", "type": "string", "required": True, "description": "Buyurtmachi nomi"},
                {"name": "client_inn", "type": "string", "required": True, "description": "Buyurtmachi INN"},
                {"name": "client_address", "type": "text", "required": True, "description": "Buyurtmachi manzili"},
                {"name": "client_director", "type": "string", "required": True, "description": "Buyurtmachi rahbari"},
                {"name": "provider_name", "type": "string", "required": True, "description": "Ijrochi nomi"},
                {"name": "provider_inn", "type": "string", "required": True, "description": "Ijrochi INN"},
                {"name": "provider_address", "type": "text", "required": True, "description": "Ijrochi manzili"},
                {"name": "provider_director", "type": "string", "required": True, "description": "Ijrochi rahbari"},
                {"name": "service_description", "type": "text", "required": True, "description": "Xizmat tavsifi"},
                {"name": "contract_amount", "type": "number", "required": True, "description": "Shartnoma summasi"},
                {"name": "start_date", "type": "date", "required": True, "description": "Boshlanish sanasi"},
                {"name": "end_date", "type": "date", "required": True, "description": "Tugash sanasi"},
                {"name": "payment_terms", "type": "text", "required": False, "description": "To'lov shartlari"},
            ]
        },
    },
    {
        "id": "supply_contract",
        "name": "Yetkazib Berish Shartnomasi",
        "description": "Mahsulot yetkazib berish shartnomasi",
        "organization": "Umumiy",
        "category": "Shartnoma",
        "file_path": "templates/contracts/supply_contract.docx",
        "preview_image": "templates/contracts/supply_contract_preview.png",
        "tags": ["shartnoma", "contract", "yetkazish", "supply", "mahsulot"],
        "schema": {
            "fields": [
                {"name": "contract_number", "type": "string", "required": True, "description": "Shartnoma raqami"},
                {"name": "contract_date", "type": "date", "required": True, "description": "Shartnoma sanasi"},
                {"name": "buyer_name", "type": "string", "required": True, "description": "Xaridor nomi"},
                {"name": "buyer_inn", "type": "string", "required": True, "description": "Xaridor INN"},
                {"name": "buyer_address", "type": "text", "required": True, "description": "Xaridor manzili"},
                {"name": "seller_name", "type": "string", "required": True, "description": "Sotuvchi nomi"},
                {"name": "seller_inn", "type": "string", "required": True, "description": "Sotuvchi INN"},
                {"name": "seller_address", "type": "text", "required": True, "description": "Sotuvchi manzili"},
                {"name": "product_description", "type": "text", "required": True, "description": "Mahsulot tavsifi"},
                {"name": "quantity", "type": "number", "required": True, "description": "Miqdori"},
                {"name": "unit_price", "type": "number", "required": True, "description": "Birlik narxi"},
                {"name": "total_amount", "type": "number", "required": True, "description": "Jami summa"},
                {"name": "delivery_date", "type": "date", "required": True, "description": "Yetkazish sanasi"},
                {"name": "delivery_address", "type": "text", "required": True, "description": "Yetkazish manzili"},
            ]
        },
    },
]


# HR templates
HR_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "employment_contract",
        "name": "Mehnat Shartnomasi",
        "description": "Xodim bilan mehnat shartnomasi",
        "organization": "HR",
        "category": "Mehnat",
        "file_path": "templates/hr/employment_contract.docx",
        "preview_image": "templates/hr/employment_contract_preview.png",
        "tags": ["hr", "mehnat", "employment", "contract", "xodim"],
        "schema": {
            "fields": [
                {"name": "contract_number", "type": "string", "required": True, "description": "Shartnoma raqami"},
                {"name": "contract_date", "type": "date", "required": True, "description": "Shartnoma sanasi"},
                {"name": "employee_name", "type": "string", "required": True, "description": "Xodim F.I.O"},
                {"name": "employee_passport", "type": "string", "required": True, "description": "Passport ma'lumotlari"},
                {"name": "employee_address", "type": "text", "required": True, "description": "Yashash manzili"},
                {"name": "employee_phone", "type": "phone", "required": False, "description": "Telefon raqami"},
                {"name": "position", "type": "string", "required": True, "description": "Lavozim"},
                {"name": "department", "type": "string", "required": False, "description": "Bo'lim"},
                {"name": "salary", "type": "number", "required": True, "description": "Oylik maosh"},
                {"name": "start_date", "type": "date", "required": True, "description": "Ish boshlash sanasi"},
                {"name": "contract_term", "type": "string", "required": True, "description": "Shartnoma muddati",
                 "options": ["Muddatsiz", "1 yil", "2 yil", "3 yil"]},
                {"name": "probation_period", "type": "number", "required": False, "description": "Sinov muddati (kun)"},
                {"name": "company_name", "type": "string", "required": True, "description": "Korxona nomi"},
                {"name": "company_director", "type": "string", "required": True, "description": "Rahbar F.I.O"},
            ]
        },
    },
    {
        "id": "termination_order",
        "name": "Ishdan Bo'shatish Buyrug'i",
        "description": "Xodimni ishdan bo'shatish buyrug'i",
        "organization": "HR",
        "category": "Buyruq",
        "file_path": "templates/hr/termination_order.docx",
        "preview_image": "templates/hr/termination_order_preview.png",
        "tags": ["hr", "buyruq", "order", "boshatish", "termination"],
        "schema": {
            "fields": [
                {"name": "order_number", "type": "string", "required": True, "description": "Buyruq raqami"},
                {"name": "order_date", "type": "date", "required": True, "description": "Buyruq sanasi"},
                {"name": "employee_name", "type": "string", "required": True, "description": "Xodim F.I.O"},
                {"name": "position", "type": "string", "required": True, "description": "Lavozim"},
                {"name": "department", "type": "string", "required": False, "description": "Bo'lim"},
                {"name": "termination_date", "type": "date", "required": True, "description": "Bo'shash sanasi"},
                {"name": "termination_reason", "type": "text", "required": True, "description": "Bo'shatish sababi"},
                {"name": "company_name", "type": "string", "required": True, "description": "Korxona nomi"},
                {"name": "director_name", "type": "string", "required": True, "description": "Rahbar F.I.O"},
            ]
        },
    },
]


# All templates combined
ALL_TEMPLATES = BANK_TEMPLATES + GOVERNMENT_TEMPLATES + CONTRACT_TEMPLATES + HR_TEMPLATES


def get_all_template_definitions() -> list[dict[str, Any]]:
    """Get all template definitions."""
    return ALL_TEMPLATES


def get_template_by_id(template_id: str) -> dict[str, Any] | None:
    """Get a template definition by ID."""
    for template in ALL_TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_templates_by_organization(organization: str) -> list[dict[str, Any]]:
    """Get templates by organization."""
    return [t for t in ALL_TEMPLATES if t["organization"].lower() == organization.lower()]


def get_templates_by_category(category: str) -> list[dict[str, Any]]:
    """Get templates by category."""
    return [t for t in ALL_TEMPLATES if t["category"].lower() == category.lower()]


def get_template_field_names(template_id: str) -> list[str]:
    """Get list of field names for a template."""
    template = get_template_by_id(template_id)
    if template and template.get("schema"):
        return [f["name"] for f in template["schema"].get("fields", [])]
    return []
