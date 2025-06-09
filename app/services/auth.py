from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..models import Employee, UserRole, Document, DocumentVisibility
from ..database import get_db
from functools import wraps
from fastapi import HTTPException, status

# Security configuration
SECRET_KEY = "xK7mP9vQ2wR8tY6uI3oE1nM5sA4dF7gH9jL2kX8vC6z"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Permission:
    """Define system permissions"""
    # Chat permissions
    CHAT_WITH_AI = "chat_with_ai"
    VIEW_CHAT_HISTORY = "view_chat_history"
    
    # Document permissions
    UPLOAD_DOCUMENT = "upload_document"
    VIEW_PUBLIC_DOCUMENTS = "view_public_documents"
    VIEW_HR_DOCUMENTS = "view_hr_documents"
    VIEW_ALL_DOCUMENTS = "view_all_documents"
    MANAGE_DOCUMENTS = "manage_documents"
    DELETE_DOCUMENTS = "delete_documents"
    
    # Analytics permissions
    VIEW_OWN_ANALYTICS = "view_own_analytics"
    VIEW_TEAM_ANALYTICS = "view_team_analytics"
    VIEW_SYSTEM_ANALYTICS = "view_system_analytics"
    
    # User management permissions
    CREATE_EMPLOYEES = "create_employees"
    EDIT_EMPLOYEES = "edit_employees"
    DELETE_EMPLOYEES = "delete_employees"
    VIEW_ALL_EMPLOYEES = "view_all_employees"
    
    # System permissions
    ACCESS_AUDIT_LOGS = "access_audit_logs"
    SYSTEM_CONFIGURATION = "system_configuration"
    EXPORT_REPORTS = "export_reports"

class RolePermissions:
    """Define role-based permissions"""
    
    EMPLOYEE_PERMISSIONS = {
        Permission.CHAT_WITH_AI,
        Permission.VIEW_CHAT_HISTORY,
        Permission.UPLOAD_DOCUMENT,  # Limited document types
        Permission.VIEW_PUBLIC_DOCUMENTS,
        Permission.VIEW_OWN_ANALYTICS,
    }
    
    HR_MANAGER_PERMISSIONS = EMPLOYEE_PERMISSIONS | {
        Permission.VIEW_HR_DOCUMENTS,
        Permission.MANAGE_DOCUMENTS,
        Permission.VIEW_TEAM_ANALYTICS,
        Permission.VIEW_ALL_EMPLOYEES,
        Permission.EXPORT_REPORTS,
    }
    
    HR_ADMIN_PERMISSIONS = HR_MANAGER_PERMISSIONS | {
        Permission.VIEW_ALL_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.VIEW_SYSTEM_ANALYTICS,
        Permission.CREATE_EMPLOYEES,
        Permission.EDIT_EMPLOYEES,
        Permission.DELETE_EMPLOYEES,
        Permission.ACCESS_AUDIT_LOGS,
        Permission.SYSTEM_CONFIGURATION,
    }

class AuthService:
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def authenticate_employee(db: Session, email: str, password: str) -> Optional[Employee]:
        """Authenticate employee with email and password"""
        employee = db.query(Employee).filter(Employee.email == email).first()
        if not employee:
            return None
        if not AuthService.verify_password(password, employee.hashed_password):
            return None
        
        # Update last login
        employee.last_login = datetime.utcnow()
        db.commit()
        
        return employee
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode JWT access token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                return None
            return {"email": email}
        except JWTError:
            return None
    
    @staticmethod
    def get_current_employee(db: Session, token: str) -> Optional[Employee]:
        """Get current employee from token"""
        payload = AuthService.decode_access_token(token)
        if payload is None:
            return None
        
        email = payload.get("email")
        if email is None:
            return None
        
        employee = db.query(Employee).filter(Employee.email == email).first()
        return employee
    
    @staticmethod
    def get_user_permissions(user_role: UserRole) -> set:
        """Get permissions for a user role"""
        if user_role == UserRole.EMPLOYEE:
            return RolePermissions.EMPLOYEE_PERMISSIONS
        elif user_role == UserRole.HR_MANAGER:
            return RolePermissions.HR_MANAGER_PERMISSIONS
        elif user_role == UserRole.HR_ADMIN:
            return RolePermissions.HR_ADMIN_PERMISSIONS
        else:
            return set()
    
    @staticmethod
    def has_permission(employee: Employee, permission: str) -> bool:
        """Check if employee has specific permission"""
        user_permissions = AuthService.get_user_permissions(employee.user_role)
        return permission in user_permissions
    
    @staticmethod
    def can_access_document(employee: Employee, document: Document) -> bool:
        """Check if employee can access a specific document"""
        # Public documents - everyone can access
        if document.visibility == DocumentVisibility.PUBLIC:
            return True
        
        # HR only documents
        if document.visibility == DocumentVisibility.HR_ONLY:
            return employee.user_role in [UserRole.HR_MANAGER, UserRole.HR_ADMIN]
        
        # Department specific documents
        if document.visibility == DocumentVisibility.DEPARTMENT:
            return (employee.department == document.department or 
                   employee.user_role in [UserRole.HR_MANAGER, UserRole.HR_ADMIN])
        
        # Restricted documents - admin only
        if document.visibility == DocumentVisibility.RESTRICTED:
            return employee.user_role == UserRole.HR_ADMIN
        
        return False
    
    @staticmethod
    def can_upload_document_type(employee: Employee, document_type: str) -> bool:
        """Check if employee can upload specific document type"""
        if employee.user_role in [UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            return True
        
        # Regular employees can only upload certain types
        allowed_types = ["general", "feedback", "suggestion"]
        return document_type in allowed_types
    
    @staticmethod
    def get_accessible_documents(db: Session, employee: Employee) -> List[Document]:
        """Get all documents accessible to the employee"""
        query = db.query(Document).filter(Document.is_active == True)
        
        if employee.user_role == UserRole.HR_ADMIN:
            # Admin can see everything
            return query.all()
        elif employee.user_role == UserRole.HR_MANAGER:
            # HR Manager can see public, HR only, and department docs
            return query.filter(
                Document.visibility.in_([
                    DocumentVisibility.PUBLIC,
                    DocumentVisibility.HR_ONLY,
                    DocumentVisibility.DEPARTMENT
                ])
            ).all()
        else:
            # Regular employees see public and their department docs
            return query.filter(
                (Document.visibility == DocumentVisibility.PUBLIC) |
                ((Document.visibility == DocumentVisibility.DEPARTMENT) & 
                 (Document.department == employee.department))
            ).all()

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get current employee from kwargs (should be injected by FastAPI)
            current_employee = kwargs.get('current_employee')
            if not current_employee:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not AuthService.has_permission(current_employee, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(required_roles: List[UserRole]):
    """Decorator to require specific role(s)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_employee = kwargs.get('current_employee')
            if not current_employee:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_employee.user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {[role.value for role in required_roles]}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator