from enum import Enum


class EntityType(str, Enum):
    CLIENT = "client"
    BUILDING = "building"
    VENDOR = "vendor"
    BROKER = "broker"
    CONTACT = "contact"
    DEAL = "deal"
    SPACE = "space"
    CANDIDATE = "candidate"
    HR_ROLE = "hr_role"


class RelationshipType(str, Enum):
    TENANT_OF = "tenant_of"           # client → building
    BROKER_FOR = "broker_for"         # broker → deal or client
    VENDOR_FOR = "vendor_for"         # vendor → building or service
    CONTACT_AT = "contact_at"         # contact → client or vendor
    LOCATED_IN = "located_in"         # space → building
    PART_OF_DEAL = "part_of_deal"     # client/space/building → deal
    MANAGES = "manages"               # contact → building or space
    REFERRED_BY = "referred_by"       # deal/client → broker
    HIRED_FOR = "hired_for"
    APPLIED_FOR = "applied_for"
    REPORTS_TO_MANAGER = "reports_to_manager"


class DecisionType(str, Enum):
    LEAD_APPROVAL = "lead_approval"
    LEAD_REJECTION = "lead_rejection"
    DEAL_CLOSURE = "deal_closure"
    PRICING_DECISION = "pricing_decision"
    VENDOR_SELECTION = "vendor_selection"
    BROKER_COMMISSION = "broker_commission"
    SPACE_ALLOCATION = "space_allocation"
    CONTRACT_APPROVAL = "contract_approval"
    OUTREACH_APPROVAL = "outreach_approval"
    HIRE_APPROVAL = "hire_approval"
    HIRE_REJECTION = "hire_rejection"
    SHORTLIST_APPROVAL = "shortlist_approval"
    OFFER_APPROVAL = "offer_approval"


class DecisionActor(str, Enum):
    ADMIN = "admin"
    ADMIN2 = "admin2"
    TEAM = "team"
    SYSTEM = "system"


class DataSource(str, Enum):
    GOOGLE_SHEETS = "google_sheets"
    GMAIL = "gmail"
    HUBSPOT = "hubspot"
    DOCUMENT = "document"
    MANUAL = "manual"
    INFERRED = "inferred"
    LINKEDIN_INBOUND = "linkedin_inbound"
    LINKEDIN_SOURCED = "linkedin_sourced"
    NAUKRI = "naukri"
    INSTAHYRE = "instahyre"
    CAREERS_FORM = "careers_form"


class ContentType(str, Enum):
    ENTITY_SUMMARY = "entity_summary"
    EMAIL_THREAD = "email_thread"
    DOCUMENT_CHUNK = "document_chunk"
    DECISION_CONTEXT = "decision_context"
    RELATIONSHIP_SUMMARY = "relationship_summary"


class QualityCheckType(str, Enum):
    DUPLICATE_DETECTION = "duplicate_detection"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    STALE_DATA = "stale_data"
    CONFIDENCE_DRIFT = "confidence_drift"
    ORPHANED_ENTITY = "orphaned_entity"
    PII_EXPOSURE = "pii_exposure"


# ── HR Engine enums (AI Hire) ───────────────────────────────────────────────
# Appended below existing enums — non-breaking additions only.

class CandidateSource(str, Enum):
    LINKEDIN_INBOUND = "linkedin_inbound"
    LINKEDIN_SOURCED = "linkedin_sourced"
    NAUKRI = "naukri"
    INSTAHYRE = "instahyre"
    CAREERS_FORM = "careers_form"
    EMAIL = "email"
    REFERRAL = "referral"
    MANUAL = "manual"


class RoleType(str, Enum):
    BD_MANAGER = "bd_manager"
    OPERATIONS_MANAGER = "operations_manager"
    FINANCE_ASSOCIATE = "finance_associate"
    FACILITY_MANAGER = "facility_manager"
    TECH = "tech"
    ADMIN = "admin"
    OTHER = "other"
