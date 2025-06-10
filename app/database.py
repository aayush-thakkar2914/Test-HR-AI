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

# File: app/database.py - Updated init_sample_data function

def init_sample_data():
    """Initialize sample data for demo with proper manager relationships"""
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
        
        # Create sample employees with different roles - UPDATED WITH MANAGER RELATIONSHIPS
        sample_employees = [
            # HR Admin (can approve everything)
            Employee(
                employee_id="HR002", 
                name="Michael Chen",
                email="michael.chen@company.com",
                department="HR",
                role="HR Director",
                user_role=UserRole.HR_ADMIN,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # HR Admin has no manager
            ),
            # HR Manager
            Employee(
                employee_id="HR001",
                name="Sarah Johnson",
                email="sarah.johnson@company.com",
                department="HR",
                role="HR Manager",
                user_role=UserRole.HR_MANAGER,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to HR Admin after creation
            ),
            # IT Manager (can approve IT department employees)
            Employee(
                employee_id="MGR001",
                name="David Wilson",
                email="david.wilson@company.com",
                department="IT",
                role="IT Manager",
                user_role=UserRole.MANAGER,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to HR Manager after creation
            ),
            # Finance Manager
            Employee(
                employee_id="MGR002",
                name="Lisa Brown",
                email="lisa.brown@company.com",
                department="Finance",
                role="Finance Manager",
                user_role=UserRole.MANAGER,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to HR Manager after creation
            ),
            # Regular Employee in IT
            Employee(
                employee_id="EMP001",
                name="John Doe",
                email="john.doe@company.com",
                department="IT",
                role="Software Engineer",
                user_role=UserRole.EMPLOYEE,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to IT Manager after creation
            ),
            # Regular Employee in Finance
            Employee(
                employee_id="EMP002",
                name="Jane Smith",
                email="jane.smith@company.com",
                department="Finance",
                role="Accountant",
                user_role=UserRole.EMPLOYEE,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to Finance Manager after creation
            ),
            # Additional IT Employee
            Employee(
                employee_id="EMP003",
                name="Bob Johnson",
                email="bob.johnson@company.com",
                department="IT",
                role="DevOps Engineer",
                user_role=UserRole.EMPLOYEE,
                hashed_password=pwd_context.hash("password123"),
                manager_id=None  # Will be set to IT Manager after creation
            )
        ]
        
        # Add all employees first
        for emp in sample_employees:
            db.add(emp)
        
        db.flush()  # Flush to get IDs
        
        # Now set up manager relationships properly
        print("Setting up manager relationships...")
        
        # Get employees by email for easy reference
        hr_admin = db.query(Employee).filter(Employee.email == "michael.chen@company.com").first()
        hr_manager = db.query(Employee).filter(Employee.email == "sarah.johnson@company.com").first()
        it_manager = db.query(Employee).filter(Employee.email == "david.wilson@company.com").first()
        finance_manager = db.query(Employee).filter(Employee.email == "lisa.brown@company.com").first()
        john_doe = db.query(Employee).filter(Employee.email == "john.doe@company.com").first()
        jane_smith = db.query(Employee).filter(Employee.email == "jane.smith@company.com").first()
        bob_johnson = db.query(Employee).filter(Employee.email == "bob.johnson@company.com").first()
        
        # Set up manager hierarchy
        # HR Manager reports to HR Admin
        hr_manager.manager_id = hr_admin.id
        
        # Department Managers report to HR Manager
        it_manager.manager_id = hr_manager.id
        finance_manager.manager_id = hr_manager.id
        
        # Employees report to their department managers
        john_doe.manager_id = it_manager.id
        bob_johnson.manager_id = it_manager.id
        jane_smith.manager_id = finance_manager.id
        
        print(f"Manager relationships set:")
        print(f"- {hr_manager.name} → {hr_admin.name}")
        print(f"- {it_manager.name} → {hr_manager.name}")
        print(f"- {finance_manager.name} → {hr_manager.name}")
        print(f"- {john_doe.name} → {it_manager.name}")
        print(f"- {bob_johnson.name} → {it_manager.name}")
        print(f"- {jane_smith.name} → {finance_manager.name}")
        
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
                3. Personal Leave: Up to 5 days per year for personal matters.
                4. Maternity Leave: Female employees are entitled to 6 months of maternity leave.
                5. Paternity Leave: Male employees are entitled to 15 days of paternity leave.
                6. Emergency Leave: Up to 5 days per year for family emergencies.
                
                Leave Application Process:
                - Submit leave application at least 3 days in advance
                - Get approval from immediate supervisor/manager
                - HR will process the application within 2 business days
                - Emergency leave can be approved retroactively
                
                Approval Hierarchy:
                - Regular employees: Manager approval required
                - Managers: HR Manager approval required
                - All applications: Final HR approval needed
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
                
                Leave Management Guidelines:
                - Managers can approve up to 5 consecutive days
                - HR approval required for longer periods
                - Emergency leave: immediate approval, review later
                
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
                
                Leave Coordination:
                - Notify team lead 1 week in advance for planned leave
                - Document ongoing projects before leave
                - Ensure proper handover for critical systems
                
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
                
                Leave Policy Exceptions:
                - Executives: Unlimited PTO policy
                - Board approval required for extended absences
                - Succession planning during leave periods
                
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
        
        # Create some sample leave applications to test the system
        print("Creating sample leave applications...")
        
        from .models import LeaveApplication, LeaveType, LeaveStatus
        from datetime import date, timedelta
        from decimal import Decimal
        
        # Sample leave applications
        sample_applications = [
            # Pending application from John Doe
            LeaveApplication(
                application_number="LA2024-0001",
                employee_id=john_doe.id,
                leave_type=LeaveType.ANNUAL,
                start_date=date.today() + timedelta(days=7),
                end_date=date.today() + timedelta(days=9),
                total_days=Decimal('3.0'),
                reason="Family vacation",
                manager_id=it_manager.id,
                status=LeaveStatus.PENDING,
                created_via="web"
            ),
            # Manager approved application from Jane Smith
            LeaveApplication(
                application_number="LA2024-0002",
                employee_id=jane_smith.id,
                leave_type=LeaveType.SICK,
                start_date=date.today() + timedelta(days=14),
                end_date=date.today() + timedelta(days=14),
                total_days=Decimal('1.0'),
                reason="Medical appointment",
                manager_id=finance_manager.id,
                status=LeaveStatus.MANAGER_APPROVED,
                manager_comments="Approved - important medical appointment",
                created_via="chat"
            ),
            # Emergency leave from Bob Johnson
            LeaveApplication(
                application_number="LA2024-0003",
                employee_id=bob_johnson.id,
                leave_type=LeaveType.EMERGENCY,
                start_date=date.today() + timedelta(days=2),
                end_date=date.today() + timedelta(days=2),
                total_days=Decimal('1.0'),
                reason="Family emergency",
                manager_id=it_manager.id,
                status=LeaveStatus.PENDING,
                created_via="chat"
            )
        ]
        
        for app in sample_applications:
            db.add(app)
        
        db.commit()
        
        print("\n" + "="*60)
        print("🎉 Sample data with RBAC initialized successfully!")
        print("="*60)
        print("\n📧 Demo accounts:")
        print("┌─────────────────────────────────────────────────────────┐")
        print("│ Role          │ Email                    │ Password      │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ Employee      │ john.doe@company.com     │ password123   │")
        print("│ Employee      │ jane.smith@company.com   │ password123   │")
        print("│ Employee      │ bob.johnson@company.com  │ password123   │")
        print("│ IT Manager    │ david.wilson@company.com │ password123   │")
        print("│ Finance Mgr   │ lisa.brown@company.com   │ password123   │")
        print("│ HR Manager    │ sarah.johnson@company.com│ password123   │")
        print("│ HR Admin      │ michael.chen@company.com │ password123   │")
        print("└─────────────────────────────────────────────────────────┘")
        
        print("\n🏢 Organizational Structure:")
        print("Michael Chen (HR Admin)")
        print("  └── Sarah Johnson (HR Manager)")
        print("      ├── David Wilson (IT Manager)")
        print("      │   ├── John Doe (Software Engineer)")
        print("      │   └── Bob Johnson (DevOps Engineer)")
        print("      └── Lisa Brown (Finance Manager)")
        print("          └── Jane Smith (Accountant)")
        
        print("\n📋 Sample Leave Applications Created:")
        print("• LA2024-0001: John Doe - 3 days annual leave (PENDING)")
        print("• LA2024-0002: Jane Smith - 1 day sick leave (MANAGER_APPROVED)")
        print("• LA2024-0003: Bob Johnson - 1 day emergency leave (PENDING)")
        
        print("\n🧪 Test Scenarios:")
        print("1. Login as john.doe@company.com → Ask 'Where is my leave request?'")
        print("2. Login as david.wilson@company.com → Ask 'Show me pending leave approvals'")
        print("3. Login as sarah.johnson@company.com → Ask 'Show me pending leave approvals'")
        print("4. Try submitting new leave applications via chat")
        
        print("\n✅ System ready for testing!")
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()