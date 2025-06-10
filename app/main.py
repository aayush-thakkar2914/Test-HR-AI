from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json
import os

from .database import get_db, create_tables, init_sample_data
from .models import Employee, Document, ChatSession, ChatMessage, QueryAnalytics, UserRole, DocumentVisibility, LeaveApplication, LeaveBalance
try:
    from .services.auth import AuthService, Permission, require_permission, require_role
except ImportError:
    # Fallback to basic auth if RBAC service is not available
    from .services.auth import AuthService
    Permission = None
    def require_permission(perm):
        def decorator(func):
            return func
        return decorator
    def require_role(roles):
        def decorator(func):
            return func
        return decorator
from .services.ai_service import AIService
from .services.leave_service import LeaveService
from .utils.document_processor import DocumentProcessor

# Initialize FastAPI app
app = FastAPI(title="HR AI Assistant with Leave Management", description="Intelligent HR Assistant with Role-Based Access Control and Advanced Leave Management", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize services
auth_service = AuthService()
ai_service = AIService()
leave_service = LeaveService()
doc_processor = DocumentProcessor()

# Pydantic models for requests
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None

class FeedbackRequest(BaseModel):
    message_id: int
    rating: int

class CreateEmployeeRequest(BaseModel):
    employee_id: str
    name: str
    email: str
    department: str
    role: str
    user_role: UserRole
    password: str

class UpdateEmployeeRequest(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    user_role: Optional[UserRole] = None
    is_active: Optional[bool] = None

# Helper function to get current employee
def get_current_employee(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Get current authenticated employee"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    employee = auth_service.get_current_employee(db, token)
    if not employee:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    return employee

@app.get("/api/debug/database")
async def debug_database(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check database state"""
    if current_employee.user_role != UserRole.HR_ADMIN:
        raise HTTPException(status_code=403, detail="HR Admin only")
    
    employees = db.query(Employee).all()
    applications = db.query(LeaveApplication).all()
    
    return {
        "employees": [
            {
                "id": emp.id,
                "name": emp.name,
                "role": emp.user_role.value,
                "manager_id": emp.manager_id
            }
            for emp in employees
        ],
        "applications": [
            {
                "id": app.id,
                "number": app.application_number,
                "employee_id": app.employee_id,
                "manager_id": app.manager_id,
                "status": app.status.value
            }
            for app in applications
        ]
    }

# Add this to your main.py file

@app.get("/api/debug/manager/{manager_id}")
async def debug_manager_data(
    manager_id: int,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check manager data"""
    if current_employee.user_role not in [UserRole.HR_ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the manager
    manager = db.query(Employee).filter(Employee.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Get team members
    team_members = db.query(Employee).filter(
        Employee.manager_id == manager_id,
        Employee.is_active == True
    ).all()
    
    # Get all applications
    all_applications = db.query(LeaveApplication).filter(
        LeaveApplication.manager_id == manager_id
    ).all()
    
    # Get pending applications
    pending_applications = db.query(LeaveApplication).filter(
        LeaveApplication.manager_id == manager_id,
        LeaveApplication.status == LeaveStatus.PENDING
    ).all()
    
    return {
        "manager": {
            "id": manager.id,
            "name": manager.name,
            "role": manager.user_role.value,
            "department": manager.department
        },
        "team_members": [
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department
            }
            for emp in team_members
        ],
        "applications": {
            "total": len(all_applications),
            "pending": len(pending_applications),
            "all_apps": [
                {
                    "id": app.id,
                    "number": app.application_number,
                    "employee": app.employee.name,
                    "status": app.status.value,
                    "dates": f"{app.start_date} to {app.end_date}"
                }
                for app in all_applications
            ]
        }
    }

# Also add this simpler debug endpoint
@app.get("/api/debug/applications")
async def debug_all_applications(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Debug all applications in the system"""
    if current_employee.user_role not in [UserRole.HR_ADMIN]:
        raise HTTPException(status_code=403, detail="HR Admin only")
    
    applications = db.query(LeaveApplication).all()
    
    return {
        "total_applications": len(applications),
        "applications": [
            {
                "id": app.id,
                "number": app.application_number,
                "employee_id": app.employee_id,
                "employee_name": app.employee.name,
                "manager_id": app.manager_id,
                "status": app.status.value,
                "start_date": app.start_date.isoformat(),
                "end_date": app.end_date.isoformat()
            }
            for app in applications
        ]
    }
# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and sample data"""
    create_tables()
    init_sample_data()
    print("HR AI Assistant with Leave Management started successfully!")

# Root endpoint - serve main page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main application page"""
    return FileResponse("static/index.html")

# Authentication endpoints
@app.post("/api/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate employee and return access token"""
    employee = auth_service.authenticate_employee(db, request.email, request.password)
    
    if not employee:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": employee.email}, expires_delta=access_token_expires
    )
    
    # Get user permissions
    try:
        permissions = list(auth_service.get_user_permissions(employee.user_role))
    except:
        permissions = []
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "role": employee.role,
            "user_role": employee.user_role.value,
            "permissions": permissions
        }
    }

@app.get("/api/profile")
async def get_profile(current_employee: Employee = Depends(get_current_employee)):
    """Get current employee profile"""
    try:
        permissions = list(auth_service.get_user_permissions(current_employee.user_role))
    except:
        permissions = []
    
    return {
        "id": current_employee.id,
        "name": current_employee.name,
        "email": current_employee.email,
        "department": current_employee.department,
        "role": current_employee.role,
        "employee_id": current_employee.employee_id,
        "user_role": current_employee.user_role.value,
        "permissions": permissions,
        "last_login": current_employee.last_login.isoformat() if current_employee.last_login else None
    }

# Chat endpoints with leave management integration
@app.post("/api/chat")
async def chat_with_ai(
    request: ChatRequest,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Process chat message and return AI response with leave management integration"""
    start_time = datetime.utcnow()
    
    try:
        # Get or create chat session
        if request.session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == request.session_id,
                ChatSession.employee_id == current_employee.id,
                ChatSession.is_active == True
            ).first()
        else:
            session = None
        
        if not session:
            session = ChatSession(employee_id=current_employee.id)
            db.add(session)
            db.flush()
        
        # Save user message
        user_message = ChatMessage(
            session_id=session.id,
            message_text=request.message,
            message_type="user"
        )
        db.add(user_message)
        
        # Check if this is a leave-related query
        intent = ai_service.classify_query_intent(request.message)
        print(f"DEBUG: Classified intent for '{request.message}' as: {intent}")
        
        if intent.startswith('leave_'):
            # Handle leave-related query with specialized service
            
            # Get conversation history for context (more messages for better context)
            recent_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.timestamp.desc()).limit(10).all()  # Increased from 5 to 10
            
            conversation_history = [
                {
                    "type": msg.message_type,
                    "message": msg.message_text,
                    "timestamp": msg.timestamp.isoformat(),
                    "confidence": msg.confidence_score
                }
                for msg in reversed(recent_messages)  # Reverse to get chronological order
            ]
            
            # Process with leave service
            leave_result = leave_service.process_leave_chat_message(
                db, request.message, current_employee, conversation_history
            )
            
            ai_response = leave_result["response"]
            confidence = leave_result["confidence"]
            intent_classification = leave_result["intent_classification"]
            
            # Save AI response with intent classification
            ai_message = ChatMessage(
                session_id=session.id,
                message_text=ai_response,
                message_type="assistant",
                confidence_score=confidence,
                source_documents=json.dumps([]),
                intent_classification=json.dumps(intent_classification)
            )
            db.add(ai_message)
            
            # Save analytics with leave intent details
            analytics = QueryAnalytics(
                employee_id=current_employee.id,
                query_text=request.message,
                query_intent=intent_classification.get("primary_intent", intent),
                response_time=(datetime.utcnow() - start_time).total_seconds(),
                confidence_score=confidence,
                documents_used=json.dumps([]),
                intent_details=json.dumps(intent_classification)
            )
            db.add(analytics)
            
            db.commit()
            
            return {
                "response": ai_response,
                "session_id": session.id,
                "message_id": ai_message.id,
                "confidence": confidence,
                "response_time": (datetime.utcnow() - start_time).total_seconds(),
                "sources": 0,
                "intent": intent_classification.get("primary_intent", intent),
                "actions_performed": leave_result.get("actions_performed", []),
                "follow_up_needed": leave_result.get("follow_up_needed", False)
            }
        
        else:
            # Handle non-leave queries with existing logic
            try:
                accessible_docs = auth_service.get_accessible_documents(db, current_employee)
                relevant_docs = ai_service.search_relevant_documents_from_list(accessible_docs, request.message)
            except Exception as e:
                print(f"Error in document search: {e}")
                relevant_docs = ai_service.search_relevant_documents(db, request.message)
            
            # Generate AI response
            ai_result = ai_service.generate_hr_response(
                request.message, 
                current_employee, 
                relevant_docs
            )
            
            # Save AI response
            ai_message = ChatMessage(
                session_id=session.id,
                message_text=ai_result["response"],
                message_type="assistant",
                confidence_score=ai_result["confidence"],
                source_documents=json.dumps(ai_result["source_documents"])
            )
            db.add(ai_message)
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Save analytics
            analytics = QueryAnalytics(
                employee_id=current_employee.id,
                query_text=request.message,
                query_intent=ai_result["intent"],
                response_time=response_time,
                confidence_score=ai_result["confidence"],
                documents_used=json.dumps(ai_result["source_documents"])
            )
            db.add(analytics)
            
            db.commit()
            
            return {
                "response": ai_result["response"],
                "session_id": session.id,
                "message_id": ai_message.id,
                "confidence": ai_result["confidence"],
                "response_time": response_time,
                "sources": len(ai_result["source_documents"]),
                "intent": ai_result["intent"]
            }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(
    session_id: int,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get chat history for a session"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.employee_id == current_employee.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp).all()
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "text": msg.message_text,
                "type": msg.message_type,
                "timestamp": msg.timestamp.isoformat(),
                "confidence": msg.confidence_score
            }
            for msg in messages
        ]
    }

@app.get("/api/chat/sessions")
async def get_chat_sessions(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for current employee"""
    sessions = db.query(ChatSession).filter(
        ChatSession.employee_id == current_employee.id
    ).order_by(ChatSession.session_start.desc()).limit(10).all()
    
    return [
        {
            "id": session.id,
            "start_time": session.session_start.isoformat(),
            "is_active": session.is_active,
            "message_count": len(session.messages)
        }
        for session in sessions
    ]

# Leave Management API Endpoints
@app.get("/api/leave/balance")
async def get_leave_balance(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get employee's leave balance"""
    try:
        balances = leave_service.get_employee_leave_balances(db, current_employee.id)
        return {
            "employee_id": current_employee.employee_id,
            "employee_name": current_employee.name,
            "balances": balances
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving leave balance: {str(e)}")

@app.get("/api/leave/applications")
async def get_leave_applications(
    status: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get employee's leave applications"""
    try:
        query = db.query(LeaveApplication).filter(
            LeaveApplication.employee_id == current_employee.id
        ).order_by(LeaveApplication.applied_date.desc())
        
        if status:
            from .models import LeaveStatus
            query = query.filter(LeaveApplication.status == LeaveStatus(status))
        
        applications = query.limit(20).all()
        
        return [
            {
                "id": app.id,
                "application_number": app.application_number,
                "leave_type": app.leave_type.value,
                "start_date": app.start_date.isoformat(),
                "end_date": app.end_date.isoformat(),
                "total_days": float(app.total_days),
                "reason": app.reason,
                "status": app.status.value,
                "applied_date": app.applied_date.isoformat(),
                "manager_comments": app.manager_comments,
                "hr_comments": app.hr_comments
            }
            for app in applications
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving applications: {str(e)}")

@app.get("/api/leave/applications/pending")
async def get_pending_approvals(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get pending leave applications for approval (managers and HR)"""
    try:
        if current_employee.user_role not in [UserRole.MANAGER, UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            raise HTTPException(status_code=403, detail="Access denied. Manager or HR role required.")
        
        from .models import LeaveStatus
        
        # Get applications pending approval
        query = db.query(LeaveApplication).filter(
            LeaveApplication.status.in_([LeaveStatus.PENDING, LeaveStatus.MANAGER_APPROVED])
        )
        
        # If manager, only show their team's applications
        if current_employee.user_role == UserRole.MANAGER:
            query = query.filter(LeaveApplication.manager_id == current_employee.id)
        
        applications = query.order_by(LeaveApplication.applied_date.asc()).all()
        
        result = []
        for app in applications:
            result.append({
                "id": app.id,
                "application_number": app.application_number,
                "employee_name": app.employee.name,
                "employee_id": app.employee.employee_id,
                "department": app.employee.department,
                "leave_type": app.leave_type.value,
                "start_date": app.start_date.isoformat(),
                "end_date": app.end_date.isoformat(),
                "total_days": float(app.total_days),
                "reason": app.reason,
                "status": app.status.value,
                "applied_date": app.applied_date.isoformat(),
                "urgency": "emergency" if app.leave_type.value == "emergency" else "normal"
            })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending applications: {str(e)}")

@app.post("/api/leave/applications/{application_id}/approve")
async def approve_leave_application(
    application_id: int,
    comments: str = Form(""),
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Approve a leave application"""
    try:
        if current_employee.user_role not in [UserRole.MANAGER, UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            raise HTTPException(status_code=403, detail="Access denied. Manager or HR role required.")
        
        from .models import LeaveStatus
        
        application = db.query(LeaveApplication).filter(LeaveApplication.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Check authorization
        if current_employee.user_role == UserRole.MANAGER and application.manager_id != current_employee.id:
            raise HTTPException(status_code=403, detail="You can only approve applications from your team")
        
        # Update application based on role
        if current_employee.user_role == UserRole.MANAGER:
            if application.status != LeaveStatus.PENDING:
                raise HTTPException(status_code=400, detail="Application is not pending manager approval")
            
            application.status = LeaveStatus.MANAGER_APPROVED
            application.manager_approved_date = datetime.utcnow()
            application.manager_comments = comments
            
        elif current_employee.user_role in [UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            # HR can approve directly
            application.status = LeaveStatus.HR_APPROVED
            application.hr_approver_id = current_employee.id
            application.hr_approved_date = datetime.utcnow()
            application.hr_comments = comments
            application.final_decision_date = datetime.utcnow()
            
            # Update leave balance - move from pending to used
            leave_service.finalize_leave_balance(db, application.employee_id, application.leave_type, float(application.total_days), approved=True)
        
        db.commit()
        
        return {
            "message": "Application approved successfully",
            "application_number": application.application_number,
            "new_status": application.status.value
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error approving application: {str(e)}")

@app.post("/api/leave/applications/{application_id}/reject")
async def reject_leave_application(
    application_id: int,
    reason: str = Form(...),
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Reject a leave application"""
    try:
        if current_employee.user_role not in [UserRole.MANAGER, UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            raise HTTPException(status_code=403, detail="Access denied. Manager or HR role required.")
        
        from .models import LeaveStatus
        
        application = db.query(LeaveApplication).filter(LeaveApplication.id == application_id).first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Check authorization
        if current_employee.user_role == UserRole.MANAGER and application.manager_id != current_employee.id:
            raise HTTPException(status_code=403, detail="You can only reject applications from your team")
        
        # Update application
        application.status = LeaveStatus.REJECTED
        application.rejection_reason = reason
        application.final_decision_date = datetime.utcnow()
        
        if current_employee.user_role == UserRole.MANAGER:
            application.manager_comments = reason
        else:
            application.hr_approver_id = current_employee.id
            application.hr_comments = reason
        
        # Restore leave balance - remove from pending
        leave_service.finalize_leave_balance(db, application.employee_id, application.leave_type, float(application.total_days), approved=False)
        
        db.commit()
        
        return {
            "message": "Application rejected",
            "application_number": application.application_number,
            "new_status": application.status.value
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error rejecting application: {str(e)}")

# Document endpoints (with RBAC)
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    department: str = Form(None),
    visibility: str = Form("PUBLIC"),
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Upload and process a new document"""
    try:
        # Convert string to enum
        try:
            visibility_enum = DocumentVisibility(visibility)
        except ValueError:
            visibility_enum = DocumentVisibility.PUBLIC
        
        # Check if user can upload this document type
        try:
            if not auth_service.can_upload_document_type(current_employee, document_type):
                raise HTTPException(
                    status_code=403, 
                    detail=f"You don't have permission to upload {document_type} documents"
                )
        except:
            pass  # Skip permission check if method not available
        
        # Regular employees can only create public documents
        if current_employee.user_role == UserRole.EMPLOYEE:
            visibility_enum = DocumentVisibility.PUBLIC
        
        # Read file content
        content = await file.read()
        
        # Process document based on file type
        extracted_text = doc_processor.extract_text_from_file(content, file.filename)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        # Create document record
        document = Document(
            title=title,
            filename=file.filename,
            content=extracted_text,
            document_type=document_type,
            department=department or current_employee.department,
            visibility=visibility_enum,
            uploaded_by=current_employee.id
        )
        
        db.add(document)
        db.flush()
        
        # Process document for search (create chunks)
        chunks = doc_processor.create_document_chunks(extracted_text)
        
        # Save chunks
        from .models import DocumentChunk
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_text,
                chunk_index=i
            )
            db.add(chunk)
        
        db.commit()
        
        return {
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "chunks_created": len(chunks),
            "visibility": visibility_enum.value
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.get("/api/documents")
async def get_documents(
    document_type: Optional[str] = None,
    department: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get list of accessible documents based on user role"""
    try:
        accessible_docs = auth_service.get_accessible_documents(db, current_employee)
    except:
        # Fallback if RBAC not available
        accessible_docs = db.query(Document).filter(Document.is_active == True).all()
    
    # Apply additional filters
    if document_type:
        accessible_docs = [doc for doc in accessible_docs if doc.document_type == document_type]
    
    if department:
        accessible_docs = [doc for doc in accessible_docs if doc.department == department]
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "type": doc.document_type,
            "department": doc.department,
            "upload_date": doc.upload_date.isoformat(),
            "version": doc.version,
            "visibility": getattr(doc, 'visibility', {}).value if hasattr(doc, 'visibility') else "public",
            "uploaded_by": doc.uploader.name if hasattr(doc, 'uploader') and doc.uploader else "Unknown"
        }
        for doc in accessible_docs
    ]

# HR Management endpoints (HR only)
@app.get("/api/hr/employees")
async def get_all_employees(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get list of all employees (HR only)"""
    # Check if user has HR role
    if current_employee.user_role not in [UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied. HR role required.")
    
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    
    return [
        {
            "id": emp.id,
            "employee_id": emp.employee_id,
            "name": emp.name,
            "email": emp.email,
            "department": emp.department,
            "role": emp.role,
            "user_role": emp.user_role.value,
            "join_date": emp.join_date.isoformat(),
            "last_login": emp.last_login.isoformat() if emp.last_login else None
        }
        for emp in employees
    ]

@app.post("/api/hr/employees")
async def create_employee(
    request: CreateEmployeeRequest,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Create new employee (HR Admin only)"""
    # Check if user has HR Admin role
    if current_employee.user_role != UserRole.HR_ADMIN:
        raise HTTPException(status_code=403, detail="Access denied. HR Admin role required.")
    
    try:
        # Check if employee ID or email already exists
        existing = db.query(Employee).filter(
            (Employee.employee_id == request.employee_id) | 
            (Employee.email == request.email)
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID or email already exists")
        
        # Create new employee
        new_employee = Employee(
            employee_id=request.employee_id,
            name=request.name,
            email=request.email,
            department=request.department,
            role=request.role,
            user_role=request.user_role,
            hashed_password=auth_service.get_password_hash(request.password),
            created_by=current_employee.id
        )
        
        db.add(new_employee)
        db.commit()
        
        return {
            "message": "Employee created successfully",
            "employee_id": new_employee.id
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating employee: {str(e)}")

# Enhanced Analytics endpoints (role-based)
@app.get("/api/analytics/usage")
async def get_usage_analytics(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get usage analytics based on user role"""
    if current_employee.user_role == UserRole.EMPLOYEE:
        # Employee can only see their own analytics
        analytics = db.query(QueryAnalytics).filter(
            QueryAnalytics.employee_id == current_employee.id
        ).all()
    else:
        # HR can see system-wide analytics
        analytics = db.query(QueryAnalytics).all()
    
    intent_counts = {}
    total_queries = len(analytics)
    avg_confidence = sum(a.confidence_score or 0 for a in analytics) / max(total_queries, 1)
    avg_response_time = sum(a.response_time or 0 for a in analytics) / max(total_queries, 1)
    
    for analytic in analytics:
        intent = analytic.query_intent or 'general'
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    
    return {
        "total_queries": total_queries,
        "average_confidence": round(avg_confidence, 2),
        "average_response_time": round(avg_response_time, 3),
        "query_breakdown": intent_counts,
        "user_role": current_employee.user_role.value
    }

@app.get("/api/analytics/system")
async def get_system_analytics(
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Get system-wide analytics (HR only)"""
    # Check if user has HR role
    if current_employee.user_role not in [UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied. HR role required.")
    
    # Get employee activity
    total_employees = db.query(Employee).filter(Employee.is_active == True).count()
    active_users = db.query(Employee).filter(
        Employee.last_login >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    # Get document stats
    total_documents = db.query(Document).filter(Document.is_active == True).count()
    documents_by_type = {}
    docs = db.query(Document).filter(Document.is_active == True).all()
    for doc in docs:
        doc_type = doc.document_type or 'unknown'
        documents_by_type[doc_type] = documents_by_type.get(doc_type, 0) + 1
    
    # Get query stats by department
    analytics = db.query(QueryAnalytics).all()
    queries_by_dept = {}
    for analytic in analytics:
        employee = db.query(Employee).filter(Employee.id == analytic.employee_id).first()
        if employee:
            dept = employee.department or 'unknown'
            queries_by_dept[dept] = queries_by_dept.get(dept, 0) + 1
    
    return {
        "employee_stats": {
            "total_employees": total_employees,
            "active_users_30d": active_users,
            "activity_rate": round(active_users / max(total_employees, 1) * 100, 1)
        },
        "document_stats": {
            "total_documents": total_documents,
            "documents_by_type": documents_by_type
        },
        "usage_stats": {
            "queries_by_department": queries_by_dept,
            "total_queries": len(analytics)
        }
    }

# Feedback endpoint
@app.post("/api/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    current_employee: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    """Submit feedback for a chat message"""
    message = db.query(ChatMessage).filter(ChatMessage.id == request.message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Update analytics with feedback
    analytics = db.query(QueryAnalytics).filter(
        QueryAnalytics.employee_id == current_employee.id,
        QueryAnalytics.query_text == message.message_text
    ).first()
    
    if analytics:
        analytics.user_feedback = request.rating
        db.commit()
    
    return {"message": "Feedback submitted successfully"}

# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}