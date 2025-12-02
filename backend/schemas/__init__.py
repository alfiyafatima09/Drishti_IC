"""Pydantic schemas for API request/response validation."""
from schemas.common import (
    ScanStatus,
    ActionRequired,
    QueueStatus,
    FakeSource,
    SyncStatus,
    CaptureType,
    SuccessResponse,
    ErrorResponse,
)
from schemas.ic import (
    ICSpecificationBase,
    ICSpecificationCreate,
    ICSpecificationResponse,
    ICSearchResult,
)
from schemas.scan import (
    MatchDetails,
    FakeRegistryInfo,
    ScanResult,
    ManualOverrideRequest,
    ScanListItem,
    ScanListResult,
    ScanDetails,
)
from schemas.queue import (
    QueueItem,
    QueueListResult,
)
from schemas.fake import (
    FakeRegistryItem,
    FakeListResult,
    MarkFakeRequest,
)
from schemas.sync import (
    SyncStartRequest,
    SyncJobInfo,
    SyncStatusResponse,
    SyncHistoryItem,
    SyncHistoryResult,
)
from schemas.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
)
from schemas.dashboard import (
    RecentCounterfeit,
    DashboardStats,
)
from schemas.system import (
    HealthResponse,
    DatabaseStatus,
    CameraStatus,
    NetworkStatus,
    StorageStatus,
    LastSyncInfo,
    SystemStatusResponse,
)
from schemas.camera import (
    CaptureRequest,
    CaptureResponse,
)

__all__ = [
    # Common
    "ScanStatus",
    "ActionRequired",
    "QueueStatus",
    "FakeSource",
    "SyncStatus",
    "CaptureType",
    "SuccessResponse",
    "ErrorResponse",
    # IC
    "ICSpecificationBase",
    "ICSpecificationCreate",
    "ICSpecificationResponse",
    "ICSearchResult",
    # Scan
    "MatchDetails",
    "FakeRegistryInfo",
    "ScanResult",
    "ManualOverrideRequest",
    "ScanListItem",
    "ScanListResult",
    "ScanDetails",
    # Queue
    "QueueItem",
    "QueueListResult",
    # Fake
    "FakeRegistryItem",
    "FakeListResult",
    "MarkFakeRequest",
    # Sync
    "SyncStartRequest",
    "SyncJobInfo",
    "SyncStatusResponse",
    "SyncHistoryItem",
    "SyncHistoryResult",
    # Settings
    "SettingsResponse",
    "SettingsUpdateRequest",
    "SettingsUpdateResponse",
    # Dashboard
    "RecentCounterfeit",
    "DashboardStats",
    # System
    "HealthResponse",
    "DatabaseStatus",
    "CameraStatus",
    "NetworkStatus",
    "StorageStatus",
    "LastSyncInfo",
    "SystemStatusResponse",
    # Camera
    "CaptureRequest",
    "CaptureResponse",
]

