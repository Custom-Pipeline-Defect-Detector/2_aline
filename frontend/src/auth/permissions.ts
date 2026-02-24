export const ROLES = ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC', 'Viewer'] as const
export type Role = (typeof ROLES)[number]

export const PERMISSIONS = {
  // Everyone can see Inbox button already (since AppShell removed permission),
  // so this can stay as-is or be expanded — your choice.
  inboxAccess: ['Admin', 'Manager', 'PM', 'Sales'],

  // ✅ ADD THESE (so sidebar buttons show again)
  dashboardAccess: ['Admin', 'Manager', 'PM', 'Sales','Viewer'],
  projectsAccess: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC'],
  documentsAccess: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC', 'Viewer'],

  // Existing
  auditAccess: ['Admin', 'Manager', 'PM'],
  adminToolsAccess: ['Admin', 'Manager','PM'],
  documentsWrite: ['Admin', 'Manager', 'PM', 'Sales'],
  workWrite: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC'],
  qualityWrite: ['Admin', 'Manager', 'QC', 'Engineer', 'Technician'],
  customerWrite: ['Admin', 'Manager', 'Sales', 'PM'],
} as const satisfies Record<string, Role[]>

export type Permission = keyof typeof PERMISSIONS
