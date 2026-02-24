from __future__ import annotations

from typing import Final

READ_ROLES_ALL: Final = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC", "Viewer"]
WRITE_ROLES_DEFAULT: Final = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC"]
APPROVE_ROLES: Final = ["Admin", "Manager", "PM"]

CUSTOMERS_READ_ROLES: Final = READ_ROLES_ALL
CUSTOMERS_WRITE_ROLES: Final = ["Admin", "Manager", "Sales", "PM"]

DOCUMENTS_READ_ROLES: Final = READ_ROLES_ALL
DOCUMENTS_WRITE_ROLES: Final = ["Admin", "Manager", "PM", "Sales", "Engineer", "Technician", "QC"]

PROPOSALS_READ_ROLES: Final = ["Admin", "Manager", "PM", "Sales"]
PROPOSALS_APPROVE_ROLES: Final = ["Admin", "Manager"]

QUALITY_READ_ROLES: Final = READ_ROLES_ALL
QUALITY_WRITE_ROLES: Final = ["Admin", "Manager", "QC", "Engineer", "Technician"]

AUDIT_READ_ROLES: Final = ["Admin", "Manager", "PM", "QC"]

TASKS_READ_ROLES: Final = READ_ROLES_ALL
TASKS_WRITE_ROLES: Final = WRITE_ROLES_DEFAULT

PROJECTS_READ_ROLES: Final = READ_ROLES_ALL
PROJECTS_WRITE_ROLES: Final = WRITE_ROLES_DEFAULT

NOTIFICATION_READ_ROLES: Final = READ_ROLES_ALL
NOTIFICATION_WRITE_ROLES: Final = WRITE_ROLES_DEFAULT

ADMIN_ONLY_ROLES: Final = ["Admin"]
MANAGER_ADMIN_ROLES: Final = ["Admin", "Manager"]
