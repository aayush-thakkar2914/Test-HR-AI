from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, Enum, Date, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR_MANAGER = "hr_manager"
    HR_ADMIN = "hr_admin"

class DocumentVisibility(enum.Enum):
    PUBLIC = "public"          # All employees can see
    HR_ONLY = "hr_only"        # Only HR can see
    DEPARTMENT = "department"   # Only same department
    RESTRICTED = "restricted"   # Admin only

class LeaveType(enum.Enum):
    ANNUAL = "annual"
    SICK = "sick"
    PERSONAL = "personal"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    EMERGENCY = "emergency"
    BEREAVEMENT = "bereavement"
    STUDY = "study"

class LeaveStatus(enum.Enum):
    PENDING = "pending"
    MANAGER_APPROVED = "manager_approved"
    HR_APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    department = Column(String(50))
    role = Column(String(50))  # Job role (Engineer, Manager, etc.)
    user_role = Column(Enum(UserRole), default=UserRole.EMPLOYEE)  # System role
    manager_id = Column(Integer, ForeignKey("employees.id"))
    join_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    hashed_password = Column(String(255))
    last_login = Column(DateTime)
    created_by = Column(Integer, ForeignKey("employees.id"))
    
    # Relationships with explicit foreign_keys to avoid ambiguity
    chat_sessions = relationship("ChatSession", back_populates="employee")
    created_employees = relationship("Employee", remote_side=[id], foreign_keys=[created_by])
    manager = relationship("Employee", remote_side=[id], foreign_keys=[manager_id])
    leave_balances = relationship("LeaveBalance", back_populates="employee", foreign_keys="LeaveBalance.employee_id")
    leave_applications = relationship("LeaveApplication", back_populates="employee", foreign_keys="LeaveApplication.employee_id")

class LeaveTypeConfig(Base):
    __tablename__ = "leave_type_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    leave_type = Column(Enum(LeaveType), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    max_days_per_year = Column(Integer, default=0)
    max_consecutive_days = Column(Integer, default=365)
    carry_forward_allowed = Column(Boolean, default=False)
    requires_documentation = Column(Boolean, default=False)
    requires_manager_approval = Column(Boolean, default=True)
    requires_hr_approval = Column(Boolean, default=False)
    notice_period_days = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    year = Column(Integer, nullable=False)
    total_allocated = Column(Numeric(5, 2), default=0.0)
    used_days = Column(Numeric(5, 2), default=0.0)
    pending_days = Column(Numeric(5, 2), default=0.0)
    remaining_days = Column(Numeric(5, 2), default=0.0)
    carried_forward = Column(Numeric(5, 2), default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships with explicit foreign_keys
    employee = relationship("Employee", back_populates="leave_balances", foreign_keys=[employee_id])

class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(50), unique=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text)
    emergency_contact = Column(String(200))
    supporting_documents = Column(Text)  # JSON array of file paths
    
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    applied_date = Column(DateTime, default=datetime.utcnow)
    
    # Manager approval
    manager_id = Column(Integer, ForeignKey("employees.id"))
    manager_approved_date = Column(DateTime)
    manager_comments = Column(Text)
    
    # HR approval
    hr_approver_id = Column(Integer, ForeignKey("employees.id"))
    hr_approved_date = Column(DateTime)
    hr_comments = Column(Text)
    
    # Final decision
    final_decision_date = Column(DateTime)
    rejection_reason = Column(Text)
    
    # Metadata
    created_via = Column(String(50), default="web")  # web, chat, api
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    
    # Relationships with explicit foreign_keys
    employee = relationship("Employee", back_populates="leave_applications", foreign_keys=[employee_id])
    manager = relationship("Employee", foreign_keys=[manager_id])
    hr_approver = relationship("Employee", foreign_keys=[hr_approver_id])
    chat_session = relationship("ChatSession")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    filename = Column(String(255), nullable=False)
    content = Column(Text)
    document_type = Column(String(50))  # policy, procedure, handbook, etc.
    department = Column(String(50))
    version = Column(String(20), default="1.0")
    visibility = Column(Enum(DocumentVisibility), default=DocumentVisibility.PUBLIC)
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("employees.id"))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document")
    uploader = relationship("Employee", foreign_keys=[uploaded_by])

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    embedding_vector = Column(Text)  # JSON string of vector
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20))  # 'user' or 'assistant'
    timestamp = Column(DateTime, default=datetime.utcnow)
    confidence_score = Column(Float)
    source_documents = Column(Text)  # JSON string of document IDs used
    intent_classification = Column(Text)  # JSON string of intent analysis
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")

class QueryAnalytics(Base):
    __tablename__ = "query_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    query_text = Column(Text, nullable=False)
    query_intent = Column(String(50))  # leave, policy, benefits, etc.
    response_time = Column(Float)
    confidence_score = Column(Float)
    user_feedback = Column(Integer)  # 1-5 rating
    timestamp = Column(DateTime, default=datetime.utcnow)
    documents_used = Column(Text)  # JSON string
    intent_details = Column(Text)  # JSON string of detailed intent analysis