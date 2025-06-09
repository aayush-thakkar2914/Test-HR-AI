from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

# Database URL
DATABASE_URL = "sqlite:///./hr_assistant.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_sample_data():
    """Initialize sample data for demo"""
    try:
        from .models import Employee, Document, UserRole, DocumentVisibility
        from passlib.context import CryptContext
    except ImportError as e:
        print(f"Import error in init_sample_data: {e}")
        return
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Employee).first():
            return
        
        # Create sample employees with different roles
        sample_employees = [
            # Regular Employee
            Employee(
                employee_id="EMP001",
                name="John Doe",
                email="john.doe@company.com",
                department="IT",
                role="Software Engineer",
                user_role=UserRole.EMPLOYEE,
                hashed_password=pwd_context.hash("password123")
            ),
            # HR Manager
            Employee(
                employee_id="HR001",
                name="Sarah Johnson",
                email="sarah.johnson@company.com",
                department="HR",
                role="HR Manager",
                user_role=UserRole.HR_MANAGER,
                hashed_password=pwd_context.hash("password123")
            ),
            # HR Admin
            Employee(
                employee_id="HR002", 
                name="Michael Chen",
                email="michael.chen@company.com",
                department="HR",
                role="HR Director",
                user_role=UserRole.HR_ADMIN,
                hashed_password=pwd_context.hash("password123")
            ),
            # Another regular employee
            Employee(
                employee_id="EMP002",
                name="Jane Smith",
                email="jane.smith@company.com",
                department="Finance",
                role="Accountant",
                user_role=UserRole.EMPLOYEE,
                hashed_password=pwd_context.hash("password123")
            )
        ]
        
        for emp in sample_employees:
            db.add(emp)
        
        db.flush()  # Flush to get IDs for relationships
        
        # Get the HR admin for document creation
        hr_admin = db.query(Employee).filter(Employee.email == "michael.chen@company.com").first()
        
        # Create sample documents with different visibility levels
        sample_documents = [
            # Public document - everyone can see
            Document(
                title="Employee Leave Policy",
                filename="leave_policy.txt",
                content="""
                EMPLOYEE LEAVE POLICY
                
                1. Annual Leave: All employees are entitled to 21 days of annual leave per year.
                2. Sick Leave: Employees can take up to 10 days of sick leave per year.
                3. Maternity Leave: Female employees are entitled to 6 months of maternity leave.
                4. Paternity Leave: Male employees are entitled to 15 days of paternity leave.
                5. Emergency Leave: Up to 5 days per year for family emergencies.
                
                Leave Application Process:
                - Submit leave application at least 3 days in advance
                - Get approval from immediate supervisor
                - HR will process the application within 2 business days
                """,
                document_type="policy",
                department="HR",
                visibility=DocumentVisibility.PUBLIC,
                uploaded_by=hr_admin.id
            ),
            # HR Only document
            Document(
                title="Salary Bands and Compensation Structure",
                filename="salary_bands.txt",
                content="""
                CONFIDENTIAL - HR ONLY
                
                Salary Bands by Level:
                - Junior: $45,000 - $65,000
                - Mid-level: $65,000 - $85,000  
                - Senior: $85,000 - $120,000
                - Lead: $120,000 - $150,000
                - Manager: $130,000 - $180,000
                
                Performance Review Process:
                - Annual reviews determine salary adjustments
                - Merit increases: 3-8% based on performance
                - Promotion increases: 10-20%
                
                Confidential Information - Do not share with employees
                """,
                document_type="compensation",
                department="HR",
                visibility=DocumentVisibility.HR_ONLY,
                uploaded_by=hr_admin.id
            ),
            # Department specific document
            Document(
                title="IT Department Security Guidelines",
                filename="it_security.txt",
                content="""
                IT DEPARTMENT SECURITY GUIDELINES
                
                Access Controls:
                - Use strong passwords (12+ characters)
                - Enable 2FA on all accounts
                - Lock workstation when away
                
                Development Practices:
                - Code review required for all commits
                - No hardcoded credentials
                - Regular security scans
                
                Data Handling:
                - Encrypt sensitive data
                - Regular backups required
                - No personal data on local drives
                
                This document is specific to IT department personnel.
                """,
                document_type="procedure",
                department="IT", 
                visibility=DocumentVisibility.DEPARTMENT,
                uploaded_by=hr_admin.id
            ),
            # Restricted document - admin only
            Document(
                title="Executive Compensation and Board Decisions",
                filename="exec_compensation.txt",
                content="""
                RESTRICTED - ADMIN ACCESS ONLY
                
                Executive Compensation 2024:
                - CEO: Base $400,000 + Bonus $200,000
                - CTO: Base $350,000 + Bonus $150,000
                - CFO: Base $320,000 + Bonus $140,000
                
                Board Meeting Minutes:
                - Approved 5% budget increase for 2025
                - Discussion on potential acquisition targets
                - Executive bonus structure changes
                
                HIGHLY CONFIDENTIAL - HR ADMIN ONLY
                """,
                document_type="executive",
                department="Executive",
                visibility=DocumentVisibility.RESTRICTED,
                uploaded_by=hr_admin.id
            )
        ]
        
        for doc in sample_documents:
            db.add(doc)
        
        db.commit()
        print("Sample data with RBAC initialized successfully!")
        print("Demo accounts:")
        print("- Employee: john.doe@company.com / password123")
        print("- HR Manager: sarah.johnson@company.com / password123") 
        print("- HR Admin: michael.chen@company.com / password123")
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        db.rollback()
    finally:
        db.close()