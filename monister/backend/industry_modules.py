"""
Monister Industry Modules - Modular industry-specific configurations.

Each industry module defines:
- Name and description
- Document types and templates
- Required fields for each document
- Compliance rules
- Workflow definitions
- Terminology (Uzbek)
"""

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from config import settings


@dataclass
class DocumentTemplate:
    """A document type within an industry."""
    id: str
    name: str
    name_uz: str
    description: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    template_file: str = ""  # relative path in templates/
    compliance_rules: list[str] = field(default_factory=list)
    deadline_days: int = 0  # 0 = no deadline


@dataclass
class IndustryModule:
    """Configuration for an industry vertical."""
    id: str
    name: str
    name_uz: str
    icon: str
    description: str
    description_uz: str
    documents: list[DocumentTemplate] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# ============== Industry Definitions ==============

HEALTHCARE = IndustryModule(
    id="healthcare",
    name="Healthcare",
    name_uz="Tibbiyot",
    icon="🏥",
    description="Medical documentation automation",
    description_uz="Tibbiy hujjatlarni avtomatlashtirish",
    keywords=["tibbiy", "kasallik", "retsept", "vrach", "bemor", "shifoxona",
              "medical", "hospital", "doctor", "patient", "prescription"],
    documents=[
        DocumentTemplate(
            id="sick_leave",
            name="Sick Leave Certificate",
            name_uz="Kasallik varaqasi",
            description="Issue sick leave certificates",
            required_fields=["patient_name", "patient_id", "diagnosis_code", "start_date", "end_date", "doctor_name"],
            optional_fields=["workplace", "notes"],
            template_file="Tibbiyot/kasallik_varaqasi.docx",
            compliance_rules=["ICD-10 code required", "Max 10 days without commission"],
            deadline_days=10,
        ),
        DocumentTemplate(
            id="prescription",
            name="Prescription",
            name_uz="Retsept",
            description="Generate medical prescriptions",
            required_fields=["patient_name", "patient_dob", "medication", "dosage", "frequency", "doctor_name", "doctor_license"],
            template_file="Tibbiyot/retsept.docx",
            compliance_rules=["Controlled substances require additional approval"],
        ),
        DocumentTemplate(
            id="medical_checkup",
            name="Medical Checkup Report",
            name_uz="Tibbiy ko'rik xulosasi",
            description="Pre-employment or annual medical checkup",
            required_fields=["patient_name", "patient_dob", "checkup_type", "results", "doctor_name", "date"],
            optional_fields=["blood_pressure", "vision", "hearing", "blood_tests"],
            template_file="Tibbiyot/tibbiy_korik.docx",
            deadline_days=365,
        ),
        DocumentTemplate(
            id="referral",
            name="Referral Letter",
            name_uz="Yo'llama",
            description="Patient referral to specialist",
            required_fields=["patient_name", "from_doctor", "to_specialist", "reason", "date"],
            template_file="Tibbiyot/yollama.docx",
        ),
    ],
)

EDUCATION = IndustryModule(
    id="education",
    name="Education",
    name_uz="Ta'lim",
    icon="🎓",
    description="Educational institution document automation",
    description_uz="Ta'lim muassasasi hujjatlarini avtomatlashtirish",
    keywords=["talim", "talaba", "universitet", "maktab", "diplom", "stipendiya",
              "education", "student", "university", "school", "transcript"],
    documents=[
        DocumentTemplate(
            id="application",
            name="Student Application",
            name_uz="Ariza (talaba)",
            description="Student application/request form",
            required_fields=["student_name", "student_id", "faculty", "course", "request_type", "date"],
            template_file="Talim/ariza.docx",
        ),
        DocumentTemplate(
            id="transcript",
            name="Academic Transcript",
            name_uz="Akademik ma'lumotnoma",
            description="Official academic transcript",
            required_fields=["student_name", "student_id", "faculty", "specialization", "grades"],
            template_file="Talim/transcript.docx",
        ),
        DocumentTemplate(
            id="diploma_supplement",
            name="Diploma Supplement",
            name_uz="Diplom ilovasi",
            description="Diploma supplement document",
            required_fields=["student_name", "graduation_year", "specialization", "gpa", "courses"],
            template_file="Talim/diplom_ilovasi.docx",
        ),
        DocumentTemplate(
            id="scholarship",
            name="Scholarship Application",
            name_uz="Stipendiya arizasi",
            description="Scholarship application form",
            required_fields=["student_name", "student_id", "gpa", "scholarship_type", "reason"],
            template_file="Talim/stipendiya.docx",
        ),
        DocumentTemplate(
            id="recommendation",
            name="Recommendation Letter",
            name_uz="Tavsiyanoma",
            description="Academic recommendation letter",
            required_fields=["student_name", "recommender_name", "position", "qualities", "date"],
            template_file="Talim/tavsiyanoma.docx",
        ),
    ],
)

LEGAL = IndustryModule(
    id="legal",
    name="Legal",
    name_uz="Huquq",
    icon="⚖️",
    description="Legal document automation",
    description_uz="Huquqiy hujjatlarni avtomatlashtirish",
    keywords=["huquq", "shartnoma", "ishonchnoma", "davvo", "advokat", "sud",
              "legal", "contract", "agreement", "court", "lawyer", "attorney"],
    documents=[
        DocumentTemplate(
            id="power_of_attorney",
            name="Power of Attorney",
            name_uz="Ishonchnoma",
            description="General or specific power of attorney",
            required_fields=["grantor_name", "grantor_passport", "grantee_name", "grantee_passport", "scope", "validity_period"],
            template_file="Huquq/ishonchnoma.docx",
            compliance_rules=["Must be notarized", "Max validity 3 years"],
            deadline_days=1095,
        ),
        DocumentTemplate(
            id="nda",
            name="Non-Disclosure Agreement",
            name_uz="Maxfiylik shartnomasi (NDA)",
            description="Confidentiality agreement",
            required_fields=["party_a", "party_b", "scope", "duration", "effective_date"],
            template_file="Huquq/nda.docx",
        ),
        DocumentTemplate(
            id="service_contract",
            name="Service Contract",
            name_uz="Xizmat shartnomasi",
            description="Service agreement between parties",
            required_fields=["client_name", "provider_name", "services", "payment_terms", "start_date", "end_date"],
            template_file="Huquq/xizmat_shartnoma.docx",
        ),
        DocumentTemplate(
            id="claim",
            name="Legal Claim",
            name_uz="Da'vo arizasi",
            description="Court claim filing",
            required_fields=["plaintiff_name", "defendant_name", "court_name", "claim_amount", "grounds"],
            template_file="Huquq/davo.docx",
            compliance_rules=["Must include court jurisdiction", "State duty payment required"],
        ),
        DocumentTemplate(
            id="lease_agreement",
            name="Lease Agreement",
            name_uz="Ijara shartnomasi",
            description="Property lease/rental agreement",
            required_fields=["landlord_name", "tenant_name", "property_address", "monthly_rent", "start_date", "duration"],
            template_file="Huquq/ijara.docx",
        ),
    ],
)

FINANCE = IndustryModule(
    id="finance",
    name="Finance & Banking",
    name_uz="Moliya va Bank",
    icon="🏦",
    description="Financial document automation",
    description_uz="Moliyaviy hujjatlarni avtomatlashtirish",
    keywords=["moliya", "bank", "kredit", "invoice", "soliq", "hisob",
              "finance", "banking", "credit", "tax", "invoice", "accounting"],
    documents=[
        DocumentTemplate(
            id="loan_application",
            name="Loan Application",
            name_uz="Kredit arizasi",
            description="Bank loan application form",
            required_fields=["applicant_name", "passport", "income", "loan_amount", "loan_purpose", "term_months"],
            template_file="Moliya/kredit_ariza.docx",
            compliance_rules=["Income verification required", "Credit history check"],
        ),
        DocumentTemplate(
            id="invoice",
            name="Invoice",
            name_uz="Hisob-faktura",
            description="Commercial invoice",
            required_fields=["seller_name", "buyer_name", "items", "total_amount", "date", "invoice_number"],
            template_file="Moliya/invoice.docx",
        ),
        DocumentTemplate(
            id="tax_declaration",
            name="Tax Declaration",
            name_uz="Soliq deklaratsiyasi",
            description="Tax filing declaration",
            required_fields=["taxpayer_name", "tin", "period", "income", "deductions", "tax_amount"],
            template_file="Moliya/soliq_deklaratsiya.docx",
            deadline_days=90,
            compliance_rules=["Quarterly filing deadline", "Supporting documents required"],
        ),
        DocumentTemplate(
            id="financial_report",
            name="Financial Report",
            name_uz="Moliyaviy hisobot",
            description="Quarterly/annual financial report",
            required_fields=["company_name", "period", "revenue", "expenses", "net_income", "assets", "liabilities"],
            template_file="Moliya/moliyaviy_hisobot.docx",
        ),
    ],
)

GOVERNMENT = IndustryModule(
    id="government",
    name="Government",
    name_uz="Davlat",
    icon="🏛️",
    description="Government and public sector automation",
    description_uz="Davlat sektori hujjatlarini avtomatlashtirish",
    keywords=["davlat", "hokimiyat", "ruxsat", "fuqaro", "murojaat", "litsenziya",
              "government", "permit", "license", "citizen", "appeal"],
    documents=[
        DocumentTemplate(
            id="permit",
            name="Activity Permit",
            name_uz="Faoliyat ruxsatnomasi",
            description="Business or activity permit application",
            required_fields=["applicant_name", "organization", "activity_type", "address", "date"],
            template_file="Davlat/ruxsatnoma.docx",
            deadline_days=365,
        ),
        DocumentTemplate(
            id="citizen_appeal",
            name="Citizen Appeal",
            name_uz="Fuqarolar murojaati",
            description="Citizen appeal/complaint to government body",
            required_fields=["citizen_name", "address", "appeal_subject", "description", "target_organization"],
            template_file="Davlat/murojaat.docx",
            compliance_rules=["Response required within 30 days"],
            deadline_days=30,
        ),
        DocumentTemplate(
            id="license",
            name="License Application",
            name_uz="Litsenziya arizasi",
            description="Professional or business license",
            required_fields=["applicant_name", "license_type", "qualifications", "organization"],
            template_file="Davlat/litsenziya.docx",
        ),
        DocumentTemplate(
            id="certificate",
            name="Official Certificate",
            name_uz="Guvohnoma",
            description="Government-issued certificate",
            required_fields=["recipient_name", "certificate_type", "issuing_body", "date", "registration_number"],
            template_file="Davlat/guvohnoma.docx",
        ),
    ],
)

HR = IndustryModule(
    id="hr",
    name="Human Resources",
    name_uz="Kadrlar",
    icon="👥",
    description="HR and personnel document automation",
    description_uz="Kadrlar ishi hujjatlarini avtomatlashtirish",
    keywords=["kadrlar", "ishga", "buyruq", "mehnat", "xodim", "ish",
              "hr", "employee", "hiring", "contract", "order", "labor"],
    documents=[
        DocumentTemplate(
            id="employment_contract",
            name="Employment Contract",
            name_uz="Mehnat shartnomasi",
            description="Employment agreement",
            required_fields=["employee_name", "position", "salary", "start_date", "department", "employer_name"],
            template_file="Kadrlar/mehnat_shartnoma.docx",
        ),
        DocumentTemplate(
            id="hiring_order",
            name="Hiring Order",
            name_uz="Ishga qabul buyrug'i",
            description="Employee hiring order",
            required_fields=["employee_name", "position", "department", "start_date", "salary", "order_number"],
            template_file="Kadrlar/ishga_qabul.docx",
        ),
        DocumentTemplate(
            id="termination_order",
            name="Termination Order",
            name_uz="Ishdan bo'shatish buyrug'i",
            description="Employee termination order",
            required_fields=["employee_name", "position", "termination_date", "reason", "order_number"],
            template_file="Kadrlar/ishdan_boshatish.docx",
        ),
        DocumentTemplate(
            id="vacation_request",
            name="Vacation Request",
            name_uz="Ta'til arizasi",
            description="Employee vacation/leave request",
            required_fields=["employee_name", "position", "start_date", "end_date", "vacation_type"],
            template_file="Kadrlar/tatil_ariza.docx",
        ),
        DocumentTemplate(
            id="business_trip",
            name="Business Trip Order",
            name_uz="Xizmat safari buyrug'i",
            description="Business trip assignment order",
            required_fields=["employee_name", "destination", "start_date", "end_date", "purpose"],
            template_file="Kadrlar/xizmat_safari.docx",
        ),
    ],
)

CONSTRUCTION = IndustryModule(
    id="construction",
    name="Construction",
    name_uz="Qurilish",
    icon="🏗️",
    description="Construction industry document automation",
    description_uz="Qurilish sohasidagi hujjatlarni avtomatlashtirish",
    keywords=["qurilish", "ruxsat", "smeta", "loyiha", "texnik", "nazorat",
              "construction", "building", "permit", "estimate", "project"],
    documents=[
        DocumentTemplate(
            id="construction_permit",
            name="Construction Permit",
            name_uz="Qurilish ruxsati",
            description="Building construction permit application",
            required_fields=["applicant_name", "project_address", "building_type", "area_sqm", "estimated_cost"],
            template_file="Qurilish/qurilish_ruxsat.docx",
            compliance_rules=["Environmental assessment required", "Architect approval needed"],
        ),
        DocumentTemplate(
            id="technical_supervision",
            name="Technical Supervision Act",
            name_uz="Texnik nazorat dalolatnomasi",
            description="Technical supervision inspection report",
            required_fields=["project_name", "inspector_name", "inspection_date", "findings", "status"],
            template_file="Qurilish/texnik_nazorat.docx",
        ),
        DocumentTemplate(
            id="cost_estimate",
            name="Cost Estimate",
            name_uz="Smeta",
            description="Construction cost estimate",
            required_fields=["project_name", "items", "quantities", "unit_prices", "total"],
            template_file="Qurilish/smeta.xlsx",
        ),
    ],
)

LOGISTICS = IndustryModule(
    id="logistics",
    name="Logistics & Trade",
    name_uz="Logistika",
    icon="🚛",
    description="Logistics and international trade automation",
    description_uz="Logistika va tashqi savdo hujjatlarini avtomatlashtirish",
    keywords=["logistika", "yuk", "bojxona", "deklaratsiya", "transport",
              "logistics", "cargo", "customs", "declaration", "shipping", "CMR"],
    documents=[
        DocumentTemplate(
            id="waybill",
            name="Waybill",
            name_uz="Yuk xati",
            description="Cargo waybill / consignment note",
            required_fields=["sender_name", "receiver_name", "cargo_description", "weight", "origin", "destination"],
            template_file="Logistika/yuk_xati.docx",
        ),
        DocumentTemplate(
            id="customs_declaration",
            name="Customs Declaration",
            name_uz="Bojxona deklaratsiyasi",
            description="Customs import/export declaration",
            required_fields=["declarant_name", "goods_description", "hs_code", "value", "origin_country", "destination_country"],
            template_file="Logistika/bojxona_deklaratsiya.docx",
            compliance_rules=["HS code must be valid", "Commercial invoice required"],
        ),
        DocumentTemplate(
            id="cmr",
            name="CMR Consignment Note",
            name_uz="CMR yuk xati",
            description="International road transport consignment note",
            required_fields=["sender", "receiver", "carrier", "cargo", "loading_place", "delivery_place"],
            template_file="Logistika/cmr.docx",
        ),
    ],
)

INSURANCE = IndustryModule(
    id="insurance",
    name="Insurance",
    name_uz="Sug'urta",
    icon="🛡️",
    description="Insurance document automation",
    description_uz="Sug'urta hujjatlarini avtomatlashtirish",
    keywords=["sugurta", "polisi", "zarar", "talabnoma", "hodisa",
              "insurance", "policy", "claim", "damage", "accident"],
    documents=[
        DocumentTemplate(
            id="insurance_policy",
            name="Insurance Policy",
            name_uz="Sug'urta polisi",
            description="Insurance policy issuance",
            required_fields=["policyholder_name", "insurance_type", "coverage_amount", "premium", "start_date", "end_date"],
            template_file="Sugurta/polisi.docx",
            deadline_days=365,
        ),
        DocumentTemplate(
            id="damage_claim",
            name="Damage Claim",
            name_uz="Zarar talabnomasi",
            description="Insurance damage claim form",
            required_fields=["claimant_name", "policy_number", "incident_date", "damage_description", "claim_amount"],
            template_file="Sugurta/zarar_talabnoma.docx",
            compliance_rules=["Must be filed within 30 days of incident"],
            deadline_days=30,
        ),
    ],
)

AGRICULTURE = IndustryModule(
    id="agriculture",
    name="Agriculture",
    name_uz="Qishloq xo'jaligi",
    icon="🌾",
    description="Agricultural documentation automation",
    description_uz="Qishloq xo'jaligi hujjatlarini avtomatlashtirish",
    keywords=["qishloq", "fermer", "yer", "hosil", "ekin",
              "agriculture", "farming", "crop", "land", "harvest"],
    documents=[
        DocumentTemplate(
            id="land_lease",
            name="Land Lease Agreement",
            name_uz="Yer ijara shartnomasi",
            description="Agricultural land lease agreement",
            required_fields=["lessor_name", "lessee_name", "land_area", "location", "purpose", "lease_term", "annual_rent"],
            template_file="Qishloq/yer_ijara.docx",
        ),
        DocumentTemplate(
            id="harvest_report",
            name="Harvest Report",
            name_uz="Hosil hisoboti",
            description="Crop harvest report",
            required_fields=["farm_name", "crop_type", "area_hectares", "yield_tons", "season", "date"],
            template_file="Qishloq/hosil_hisobot.docx",
        ),
        DocumentTemplate(
            id="phytosanitary",
            name="Phytosanitary Certificate",
            name_uz="Fitosanitar sertifikati",
            description="Plant health certification",
            required_fields=["exporter_name", "product", "quantity", "origin", "destination", "inspection_date"],
            template_file="Qishloq/fitosanitar.docx",
        ),
    ],
)


# ============== Module Registry ==============

ALL_MODULES: dict[str, IndustryModule] = {
    "healthcare": HEALTHCARE,
    "education": EDUCATION,
    "legal": LEGAL,
    "finance": FINANCE,
    "government": GOVERNMENT,
    "hr": HR,
    "construction": CONSTRUCTION,
    "logistics": LOGISTICS,
    "insurance": INSURANCE,
    "agriculture": AGRICULTURE,
}


def get_all_modules() -> list[dict]:
    """Get all industry modules as dicts for API."""
    result = []
    for mid, module in ALL_MODULES.items():
        result.append({
            "id": module.id,
            "name": module.name,
            "name_uz": module.name_uz,
            "icon": module.icon,
            "description": module.description,
            "description_uz": module.description_uz,
            "document_count": len(module.documents),
            "keywords": module.keywords,
        })
    return result


def get_module(module_id: str) -> IndustryModule | None:
    """Get a specific industry module."""
    return ALL_MODULES.get(module_id)


def get_module_documents(module_id: str) -> list[dict]:
    """Get documents for a specific module."""
    module = ALL_MODULES.get(module_id)
    if not module:
        return []
    return [
        {
            "id": doc.id,
            "name": doc.name,
            "name_uz": doc.name_uz,
            "description": doc.description,
            "required_fields": doc.required_fields,
            "optional_fields": doc.optional_fields,
            "template_file": doc.template_file,
            "has_template": (settings.templates_dir / doc.template_file).exists() if doc.template_file else False,
            "deadline_days": doc.deadline_days,
            "compliance_rules": doc.compliance_rules,
        }
        for doc in module.documents
    ]


def detect_industry(text: str) -> list[dict]:
    """
    Detect which industry modules are relevant based on text input.
    Returns sorted list of matching modules with confidence scores.
    """
    text_lower = text.lower()
    matches = []

    for mid, module in ALL_MODULES.items():
        score = 0
        matched_keywords = []

        for keyword in module.keywords:
            if keyword.lower() in text_lower:
                score += 1
                matched_keywords.append(keyword)

        # Also check document names
        for doc in module.documents:
            if doc.name_uz.lower() in text_lower or doc.name.lower() in text_lower:
                score += 2
                matched_keywords.append(doc.name_uz)

        if score > 0:
            matches.append({
                "module_id": mid,
                "name": module.name,
                "name_uz": module.name_uz,
                "icon": module.icon,
                "score": score,
                "matched_keywords": matched_keywords,
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def build_industry_context(module_id: str = None, text: str = None) -> str:
    """
    Build a context string for the AI agent about available industry documents.
    Used to enhance the system prompt with relevant industry knowledge.
    """
    context = "\n\n[SOHA MODULLARI - Quyidagi hujjat turlari mavjud]\n"

    if module_id:
        modules = [ALL_MODULES.get(module_id)] if module_id in ALL_MODULES else []
    elif text:
        detected = detect_industry(text)
        modules = [ALL_MODULES[d["module_id"]] for d in detected[:3]]
    else:
        modules = list(ALL_MODULES.values())

    for module in modules:
        if not module:
            continue
        context += f"\n{module.icon} {module.name_uz} ({module.name}):\n"
        for doc in module.documents:
            has_template = "✅" if doc.template_file and (settings.templates_dir / doc.template_file).exists() else "📝"
            context += f"  {has_template} {doc.name_uz} — {doc.description}\n"
            if doc.required_fields:
                context += f"     Maydonlar: {', '.join(doc.required_fields)}\n"
            if doc.compliance_rules:
                context += f"     ⚠️ Qoidalar: {'; '.join(doc.compliance_rules)}\n"

    context += "\nFoydalanuvchi mos hujjat so'rasa, tegishli template va ma'lumotlarni ishlating.\n"
    return context


# ============== Exports ==============
__all__ = [
    "IndustryModule",
    "DocumentTemplate",
    "ALL_MODULES",
    "get_all_modules",
    "get_module",
    "get_module_documents",
    "detect_industry",
    "build_industry_context",
]
