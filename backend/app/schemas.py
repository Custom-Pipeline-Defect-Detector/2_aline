from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role_name: Optional[str] = None


class RoleOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class UserOut(UserBase):
    id: int
    is_active: bool
    roles: List[RoleOut] = []

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    filename: str
    mime: str
    storage_path: str
    file_hash: str
    processing_status: str
    document_type: Optional[str]
    classification_confidence: Optional[float]
    extracted_fields: Optional[Dict[str, Any]]
    agent_summary: Optional[str]
    needs_review: bool
    processing_error: Optional[str]
    customer_id: Optional[int]
    project_id: Optional[int]
    customer_name: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime
    versions: List["DocumentVersionOut"] = []
    proposals: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ReprocessJobOut(BaseModel):
    job_id: str
    document_id: int
    status: str


class DocumentProcessingStatusOut(BaseModel):
    document_id: int
    status: str
    processing_error: Optional[str] = None


class DocumentUpdate(BaseModel):
    document_type: Optional[str]
    classification_confidence: Optional[float]
    extracted_fields: Optional[Dict[str, Any]]
    agent_summary: Optional[str]
    needs_review: Optional[bool]
    processing_status: Optional[str]
    processing_error: Optional[str]
    customer_id: Optional[int]
    project_id: Optional[int]


class DocumentVersionOut(BaseModel):
    id: int
    doc_id: int
    version: int
    extracted_text_path: Optional[str]
    router_json: Optional[Dict[str, Any]]
    extractor_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ProposalOut(BaseModel):
    id: int
    doc_version_id: int
    proposed_action: str
    target_module: str
    target_table: str
    target_entity_id: Optional[int]
    proposed_fields: Dict[str, Any]
    field_confidence: Dict[str, Any]
    evidence: Dict[str, Any]
    questions: Dict[str, Any]
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewer_id: Optional[int]

    class Config:
        from_attributes = True


class ProposalUpdate(BaseModel):
    proposed_fields: Dict[str, Any]
    field_confidence: Dict[str, Any]
    evidence: Dict[str, Any]
    questions: Dict[str, Any]


class ProposalDecision(BaseModel):
    status: str
    reviewer_note: Optional[str] = None


class ProposalApprove(BaseModel):
    proposed_fields: Dict[str, Any]


class ProposalReject(BaseModel):
    reason: Optional[str] = None


class DashboardCounts(BaseModel):
    projects: int
    tasks: int
    pending_proposals: int
    ncrs: int


class DashboardSummary(BaseModel):
    projects: int
    open_tasks: int
    open_issues: int
    open_ncrs: int
    pending_ai_actions: int
    ncrs_weekly: List[Dict[str, Any]] = []
    tasks_by_status: List[Dict[str, Any]] = []
    projects_by_stage: List[Dict[str, Any]] = []


class NotificationOut(BaseModel):
    id: int
    user_id: Optional[int]
    role: Optional[str]
    type: Optional[str]
    message: str
    entity_table: Optional[str]
    entity_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: int
    project_code: str
    name: str
    customer_id: int
    status: str
    stage: str
    value_amount: Optional[float] = None
    currency: str
    start_date: Optional[date]
    due_date: Optional[date]
    health: str
    risk: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str]
    status: Optional[str]
    stage: Optional[str]
    value_amount: Optional[float]
    currency: Optional[str]
    start_date: Optional[date]
    due_date: Optional[date]


class ProjectDetail(ProjectOut):
    tasks: List[Dict[str, Any]]
    issues: List[Dict[str, Any]]
    ncrs: List[Dict[str, Any]]
    recent_documents: List[Dict[str, Any]] = []
    pending_ai_actions: int = 0


class MilestoneBase(BaseModel):
    name: str
    due_date: Optional[date]
    status: Optional[str] = "planned"


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: Optional[str]
    due_date: Optional[date]
    status: Optional[str]


class MilestoneOut(MilestoneBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerContactCreate(BaseModel):
    name: str
    email: Optional[EmailStr]
    role_title: Optional[str]
    phone: Optional[str]


class CustomerContactOut(CustomerContactCreate):
    id: int
    customer_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerBase(BaseModel):
    name: str
    aliases: List[str] = []
    status: Optional[str] = "lead"
    industry: Optional[str]
    owner_id: Optional[int]
    notes: Optional[str]
    tags: List[str] = []


class CustomerCreate(CustomerBase):
    contacts: Optional[List[CustomerContactCreate]] = None


class CustomerUpdate(BaseModel):
    name: Optional[str]
    aliases: Optional[List[str]]
    status: Optional[str]
    industry: Optional[str]
    owner_id: Optional[int]
    notes: Optional[str]
    tags: Optional[List[str]]


class CustomerOut(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    contacts: List[CustomerContactOut] = []
    active_projects: int = 0
    proposals_count: int = 0
    documents_count: int = 0
    last_activity_at: Optional[datetime]
    projects: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class AIProposedAction(BaseModel):
    label: str
    method: Literal["POST", "PATCH", "DELETE"]
    path: str
    body: Dict[str, Any] = {}


class AIChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class AIChatResponse(BaseModel):
    reply: str
    proposed_actions: List[AIProposedAction] = []


class AIExecuteRequest(BaseModel):
    confirm: bool
    method: Literal["POST", "PATCH", "DELETE"]
    path: str
    body: Optional[Dict[str, Any]] = None


class AIExecuteResponse(BaseModel):
    ok: bool
    result: Optional[Any] = None


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatSessionOut(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatReplyOut(BaseModel):
    reply: str
    memory_updated: bool


class UserMemoryOut(BaseModel):
    id: int
    type: str
    key: Optional[str]
    content: str
    relevance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageRoomOut(BaseModel):
    id: int
    type: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageUserOut(BaseModel):
    id: int
    name: str
    # FIX: EmailStr rejects *.local; dev seed uses @aline.local -> causes ResponseValidationError
    email: str

    class Config:
        from_attributes = True


class MessageSenderOut(BaseModel):
    id: int
    name: str
    # FIX: same reason as MessageUserOut
    email: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_user_id: int
    content: str
    created_at: datetime
    sender: MessageSenderOut

    class Config:
        from_attributes = True


class DashboardAdmin(BaseModel):
    counts: Dict[str, int]
    queue: Dict[str, int]
    recent_audit_events: List[Dict[str, Any]]


class DashboardSales(BaseModel):
    customer_status_counts: Dict[str, int]
    proposal_status_counts: Dict[str, int]
    stale_customers: List[Dict[str, Any]]


class DashboardEngineering(BaseModel):
    my_tasks: List[Dict[str, Any]]
    blocked_tasks: List[Dict[str, Any]]
    projects_due_soon: List[Dict[str, Any]]


class DashboardQuality(BaseModel):
    issue_counts: Dict[str, int]
    worst_projects: List[Dict[str, Any]]
    documents_needing_review: int


class AgentRunOut(BaseModel):
    id: int
    document_id: int
    model: str
    prompt_version: str
    started_at: datetime
    ended_at: Optional[datetime]
    tool_calls_json: Optional[Dict[str, Any]]
    final_result_json: Optional[Dict[str, Any]]
    error: Optional[str]

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    owner_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[str] = "open"
    priority: Optional[str] = "med"
    type: Optional[str] = "engineering"
    source_doc_id: Optional[int] = None


class TaskCreate(TaskBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class TaskUpdate(BaseModel):
    project_id: Optional[int]
    project_code: Optional[str] = None
    title: Optional[str]
    description: Optional[str]
    owner_id: Optional[int]
    due_date: Optional[date]
    status: Optional[str]
    priority: Optional[str]
    type: Optional[str]
    source_doc_id: Optional[int]
    completed_at: Optional[datetime]


class TaskOut(TaskBase):
    id: int
    completed_at: Optional[datetime]
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class WorkLogBase(BaseModel):
    user_id: Optional[int]
    project_id: int
    date: date
    summary: str
    derived_from_doc_id: Optional[int] = None


class WorkLogCreate(WorkLogBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class WorkLogUpdate(BaseModel):
    user_id: Optional[int]
    project_id: Optional[int]
    project_code: Optional[str] = None
    date: Optional[date]
    summary: Optional[str]
    derived_from_doc_id: Optional[int]


class WorkLogOut(WorkLogBase):
    id: int
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class NCRBase(BaseModel):
    project_id: int
    description: str
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    status: Optional[str] = "open"
    source_doc_id: Optional[int] = None
    opened_date: Optional[date] = None
    closed_date: Optional[date] = None


class NCRCreate(NCRBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class NCRUpdate(BaseModel):
    project_id: Optional[int]
    project_code: Optional[str] = None
    description: Optional[str]
    root_cause: Optional[str]
    corrective_action: Optional[str]
    status: Optional[str]
    source_doc_id: Optional[int]
    opened_date: Optional[date]
    closed_date: Optional[date]


class NCROut(NCRBase):
    id: int
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None

    class Config:
        from_attributes = True


class IssueBase(BaseModel):
    project_id: int
    severity: str
    description: str
    owner_id: Optional[int] = None
    status: Optional[str] = "open"
    source_doc_id: Optional[int] = None


class IssueCreate(IssueBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class IssueUpdate(BaseModel):
    project_id: Optional[int]
    project_code: Optional[str] = None
    severity: Optional[str]
    description: Optional[str]
    owner_id: Optional[int]
    status: Optional[str]
    source_doc_id: Optional[int]


class IssueOut(IssueBase):
    id: int
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None

    class Config:
        from_attributes = True


class BOMItemBase(BaseModel):
    project_id: int
    part_no: str
    name: str
    qty: float
    supplier: Optional[str] = None
    lead_time_days: Optional[int] = None
    status: Optional[str] = "pending"


class BOMItemCreate(BOMItemBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class BOMItemUpdate(BaseModel):
    project_id: Optional[int]
    project_code: Optional[str] = None
    part_no: Optional[str]
    name: Optional[str]
    qty: Optional[float]
    supplier: Optional[str]
    lead_time_days: Optional[int]
    status: Optional[str]


class BOMItemOut(BOMItemBase):
    id: int
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None

    class Config:
        from_attributes = True


class InspectionRecordBase(BaseModel):
    project_id: int
    inspector_id: Optional[int] = None
    date: date
    status: Optional[str] = "open"
    summary: Optional[str] = None


class InspectionRecordCreate(InspectionRecordBase):
    project_id: Optional[int] = None
    project_code: Optional[str] = None


class InspectionRecordUpdate(BaseModel):
    project_id: Optional[int]
    project_code: Optional[str] = None
    inspector_id: Optional[int]
    date: Optional[date]
    status: Optional[str]
    summary: Optional[str]


class InspectionRecordOut(InspectionRecordBase):
    id: int
    created_at: datetime
    project_name: Optional[str] = None
    project_code: Optional[str] = None

    class Config:
        from_attributes = True


class InspectionItemBase(BaseModel):
    inspection_id: int
    label: str
    status: Optional[str] = "pending"
    notes: Optional[str] = None


class InspectionItemCreate(InspectionItemBase):
    pass


class InspectionItemUpdate(BaseModel):
    label: Optional[str]
    status: Optional[str]
    notes: Optional[str]


class InspectionItemOut(InspectionItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int
    action: str
    entity_table: str
    entity_id: int
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


DocumentOut.model_rebuild()
