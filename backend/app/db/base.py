"""
Aggregates every model onto Base.metadata. Import this module (not
base_class) only from places that need the *complete* metadata graph -
Alembic's env.py and app.seed's Base.metadata.create_all() safety net.
Model modules themselves must import Base/TimestampMixin/UUIDMixin from
app.db.base_class directly to avoid a circular import back into this file.
"""
from app.db.base_class import Base, TimestampMixin, UUIDMixin  # noqa: F401

from app.models.user import Role, User  # noqa: E402,F401
from app.models.cpse import CPSEOrganization  # noqa: E402,F401
from app.models.material import (  # noqa: E402,F401
    Material,
    MaterialAttribute,
    MaterialImage,
    MaterialEmbedding,
)
from app.models.matching import MaterialMatch, AIAnalysis  # noqa: E402,F401
from app.models.harmonization import HarmonizationRequest, CommonMaterialCode  # noqa: E402,F401
from app.models.approval import ApprovalRequest, ApprovalAction  # noqa: E402,F401
from app.models.audit import AuditLog  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.settings import SystemSetting  # noqa: E402,F401
from app.models.upload_batch import UploadBatch  # noqa: E402,F401
