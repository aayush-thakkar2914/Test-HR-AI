# HR AI Assistant with Advanced Leave Management

🤖 **An intelligent HR assistant powered by AI with comprehensive leave management, role-based access control, and document processing capabilities.**

## 🌟 Features

### 🧠 **AI-Powered Chat Assistant**
- **Groq AI Integration**: Powered by Llama 3.3 70B for natural conversation
- **Context-Aware Responses**: Understands conversation history and employee context
- **Intent Classification**: Automatically detects leave requests, policy questions, and manager queries
- **Multi-turn Conversations**: Handles complex leave application flows

### 🏖️ **Advanced Leave Management**
- **Intelligent Leave Applications**: Apply for leave through natural conversation
- **Automated Approval Workflows**: Manager → HR approval hierarchy
- **Real-time Balance Tracking**: Track used, pending, and remaining leave days
- **Emergency Leave Handling**: Fast-track urgent leave requests
- **Leave Analytics**: Comprehensive reporting for managers and HR

### 🔐 **Role-Based Access Control (RBAC)**
- **Employee**: Basic chat, leave applications, document access
- **Manager**: Team leave approvals, pending reviews, team analytics
- **HR Manager**: Department oversight, advanced document access
- **HR Admin**: Full system access, employee management, system configuration

### 📚 **Document Management**
- **Multi-format Support**: PDF, DOCX, TXT document processing
- **Intelligent Search**: AI-powered document retrieval with context
- **Visibility Controls**: Public, HR-only, department-specific, and restricted documents
- **Chunking & Indexing**: Optimized search performance

### 📊 **Analytics & Reporting**
- **Usage Analytics**: Query patterns, confidence scores, response times
- **Leave Analytics**: Team availability, approval bottlenecks
- **Performance Metrics**: AI confidence tracking and user feedback

## 🏗️ **Architecture**

### **Tech Stack**
- **Backend**: FastAPI (Python 3.8+)
- **AI/ML**: Groq API (Llama 3.3), scikit-learn
- **Database**: SQLAlchemy with SQLite (production-ready for PostgreSQL)
- **Authentication**: JWT with bcrypt password hashing
- **Document Processing**: PyPDF2, python-docx
- **Frontend**: Vanilla JavaScript with Tailwind CSS

### **Project Structure**
```
hr-ai-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # Database configuration and sample data
│   ├── models.py               # SQLAlchemy models and enums
│   ├── services/
│   │   ├── ai_service.py       # Groq AI integration and NLP
│   │   ├── auth.py             # Authentication and RBAC
│   │   └── leave_service.py    # Leave management business logic
│   └── utils/
│       └── document_processor.py # Document parsing and chunking
├── static/
│   └── index.html              # Single-page web application
├── requirements.txt            # Python dependencies
├── run.py                      # Application launcher
└── .env                        # Environment configuration
```

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.8 or higher
- Groq API key ([Get one here](https://console.groq.com/))

### **Installation**

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd hr-ai-assistant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Create .env file
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

5. **Start the application**
```bash
python run.py
```

6. **Access the application**
- Open your browser to `http://127.0.0.1:8000`
- Login with demo credentials (see below)

## 👥 **Demo Accounts**

The system comes pre-loaded with demo data for testing:

| Role | Email | Password | Capabilities |
|------|-------|----------|-------------|
| **Employee** | john.doe@company.com | password123 | Apply for leave, check balance, chat |
| **Employee** | jane.smith@company.com | password123 | Apply for leave, check balance, chat |
| **IT Manager** | david.wilson@company.com | password123 | Approve team leave, manage IT employees |
| **Finance Manager** | lisa.brown@company.com | password123 | Approve team leave, manage Finance employees |
| **HR Manager** | sarah.johnson@company.com | password123 | Department oversight, advanced access |
| **HR Admin** | michael.chen@company.com | password123 | Full system access, employee management |

## 🧪 **Sample Conversations**

### **Employee Leave Application**
```
User: "I need 3 days off next week for a family trip"
AI: "I'd be happy to help you apply for leave! I need a bit more information:
     1. Specific dates (which days next week?)
     2. Type of leave (annual/vacation)
     
     For example: 'I need 3 days of annual leave from December 15-17'"

User: "December 15th to 17th, annual leave"
AI: "✅ Leave Application Submitted Successfully!
     📋 Application Details:
     • Application Number: LA2024-0001
     • Employee: John Doe
     • Leave Type: Annual
     • Dates: December 15, 2024 to December 17, 2024
     • Duration: 3 day(s)
     ..."
```

### **Manager Approval Workflow**
```
Manager: "Show me pending leave approvals"
AI: "📋 Pending Leave Approvals for David Wilson
     You have 2 application(s) waiting for approval:
     
     📅 Application #1
     • Employee: John Doe (IT)
     • Application #: LA2024-0001
     • Type: Annual Leave
     • Dates: Dec 15 - Dec 17, 2024
     ..."
```

### **Leave Balance Inquiry**
```
User: "What's my leave balance?"
AI: "Hi John! Here are your current leave balances:
     📅 Annual Leave:
        • Remaining: 18 days
        • Used: 3 days
        • Total Allocated: 21 days
     📅 Sick Leave:
        • Remaining: 10 days
        • Used: 0 days
        ..."
```

## 🔧 **API Endpoints**

### **Authentication**
- `POST /api/login` - Employee authentication
- `GET /api/profile` - Get current user profile

### **Chat & AI**
- `POST /api/chat` - Send message to AI assistant
- `GET /api/chat/history/{session_id}` - Get chat history
- `GET /api/chat/sessions` - List chat sessions

### **Leave Management**
- `GET /api/leave/balance` - Get employee leave balances
- `GET /api/leave/applications` - List employee applications
- `GET /api/leave/applications/pending` - Get pending approvals (managers/HR)
- `POST /api/leave/applications/{id}/approve` - Approve leave application
- `POST /api/leave/applications/{id}/reject` - Reject leave application

### **Document Management**
- `POST /api/documents/upload` - Upload new document
- `GET /api/documents` - List accessible documents

### **HR Management** (HR only)
- `GET /api/hr/employees` - List all employees
- `POST /api/hr/employees` - Create new employee

### **Analytics**
- `GET /api/analytics/usage` - Personal usage statistics
- `GET /api/analytics/system` - System-wide analytics (HR only)

## 🧠 **AI Capabilities**

### **Intent Classification**
The AI can understand and route various types of queries:
- **Leave Management**: Applications, balance checks, status inquiries
- **Manager Queries**: Team approvals, pending reviews, staff scheduling
- **Policy Questions**: Leave policies, benefits, procedures
- **General HR**: Benefits, payroll, conduct guidelines

### **Context Awareness**
- **Employee Role Recognition**: Adapts responses based on user permissions
- **Conversation Memory**: Maintains context across multi-turn interactions
- **Department Awareness**: Provides relevant department-specific information
- **Approval Hierarchy**: Understands reporting relationships and workflows

## 🔒 **Security Features**

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **Role-Based Access**: Granular permissions system
- **Document Visibility**: Multi-level document access controls
- **API Security**: Protected endpoints with authentication middleware

## 📈 **Monitoring & Analytics**

### **System Metrics**
- Query response times and success rates
- AI confidence scores and accuracy
- User engagement and adoption rates
- Document search effectiveness

### **Business Intelligence**
- Leave application patterns and trends
- Approval bottlenecks and processing times
- Team availability and resource planning
- HR workload distribution

## 🚀 **Deployment**

### **Development**
```bash
python run.py
```

### **Production**
```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Using gunicorn (recommended)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

Currently working on these improvements:

--> To get a formatted response from the AI Agent.

--> To add more KRAs for the assistant

--> To perform better query processing and intent classification.

--> Leave approval endpoint in the chat assistant

Screenshots:
![image](https://github.com/user-attachments/assets/86407ca8-acb6-4f3a-947a-10d1ae0c4dac)

![image](https://github.com/user-attachments/assets/79d2a58b-7f16-4287-94fa-7d8d34f63ceb)

![image](https://github.com/user-attachments/assets/4e9b5b76-9cac-489c-8c34-9ee7981d7511)

![image](https://github.com/user-attachments/assets/c167cba1-f918-4c23-a191-a356c014f61e)




