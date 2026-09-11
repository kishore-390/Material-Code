import enum


class RoleName(str, enum.Enum):
    ADMIN = "ADMIN"
    MATERIAL_EXPERT = "MATERIAL_EXPERT"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"


class CPSESector(str, enum.Enum):
    OIL_AND_GAS = "Oil & Gas"
    POWER = "Power"
    STEEL = "Steel"
    MINING = "Mining"
    HEAVY_ENGINEERING = "Heavy Engineering"
    OTHER = "Other"


class SynchronizationStatus(str, enum.Enum):
    NEVER_SYNCED = "NEVER_SYNCED"
    SYNCING = "SYNCING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class MaterialStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ANALYZED = "ANALYZED"
    HARMONIZED = "HARMONIZED"
    FAILED = "FAILED"


class Criticality(str, enum.Enum):
    CRITICAL = "CRITICAL"
    NORMAL = "NORMAL"
    NON_CRITICAL = "NON_CRITICAL"
    UNSPECIFIED = "UNSPECIFIED"


# Spec section 8 - the AI must distinguish these, never collapse into "duplicate".
class MatchDecision(str, enum.Enum):
    IDENTICAL = "IDENTICAL"
    DUPLICATE = "DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    TECHNICAL_CONFLICT = "TECHNICAL_CONFLICT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


# Spec section 5.4 - mapping_type on common_material_mappings.
class MappingType(str, enum.Enum):
    IDENTICAL = "IDENTICAL"
    DUPLICATE = "DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    FUNCTIONALLY_EQUIVALENT = "FUNCTIONALLY_EQUIVALENT"
    MANUAL_MAPPING = "MANUAL_MAPPING"
    LEGACY_MAPPING = "LEGACY_MAPPING"


# Spec section 5.4 - decision_status on common_material_mappings.
class MappingDecisionStatus(str, enum.Enum):
    AI_RECOMMENDED = "AI_RECOMMENDED"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED_AND_APPROVED = "EDITED_AND_APPROVED"
    TECHNICAL_CONFLICT = "TECHNICAL_CONFLICT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


# Spec section 13 - lifecycle of a common material / legacy code, distinct
# from the per-mapping decision_status above.
class CommonMaterialStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MAPPED = "MAPPED"
    RATIONALIZED = "RATIONALIZED"
    RETIRED = "RETIRED"
    REPLACED = "REPLACED"


class ApprovalActionType(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    EDIT_AND_APPROVE = "EDIT_AND_APPROVE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ActorType(str, enum.Enum):
    AI_ENGINE = "AI_ENGINE"
    USER = "USER"
    SYSTEM = "SYSTEM"


class DatabaseType(str, enum.Enum):
    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    ORACLE = "ORACLE"
    SQLSERVER = "SQLSERVER"


class SyncType(str, enum.Enum):
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"


class SyncStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class NotificationType(str, enum.Enum):
    MATERIAL_SYNCED = "MATERIAL_SYNCED"
    AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED"
    HIGH_CONFIDENCE_RECOMMENDATION = "HIGH_CONFIDENCE_RECOMMENDATION"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    APPROVAL_COMPLETED = "APPROVAL_COMPLETED"
    MAPPING_REJECTED = "MAPPING_REJECTED"
    COMMON_CODE_GENERATED = "COMMON_CODE_GENERATED"
    SYNC_COMPLETED = "SYNC_COMPLETED"
    SYNC_FAILED = "SYNC_FAILED"
    AI_PROCESSING_FAILED = "AI_PROCESSING_FAILED"
