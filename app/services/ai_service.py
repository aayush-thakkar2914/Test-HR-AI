import os
from groq import Groq
from typing import List, Dict, Optional
import json
import re
from sqlalchemy.orm import Session

class AIService:
    
    def __init__(self):
        # Initialize Groq client - you'll need to set your API key
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("⚠️  Warning: GROQ_API_KEY not found in environment variables")
            print("Please set your Groq API key in the .env file")
            api_key = "dummy_key_for_testing"
        
        try:
            self.groq_client = Groq(api_key=api_key)
        except Exception as e:
            print(f"Error initializing Groq client: {e}")
            self.groq_client = None
    
    def classify_query_intent(self, query: str, employee_context: Dict = None) -> str:
        """Enhanced intent classification using Groq AI model"""
        
        if not employee_context:
            employee_context = {}
        
        # Build intent classification prompt
        prompt = self.build_intent_classification_prompt(query, employee_context)
        
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert HR intent classifier. Analyze the user query and classify it into the most appropriate category. Return only the intent category name."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,
                    max_tokens=50
                )
                
                if response and response.choices and len(response.choices) > 0:
                    ai_intent = response.choices[0].message.content.strip().lower()
                    
                    # Map AI response to our intent categories
                    intent_mapping = {
                        'leave_balance': 'leave_balance',
                        'leave_application': 'leave_application', 
                        'leave_status': 'leave_status',
                        'leave_cancellation': 'leave_cancellation',
                        'emergency_leave': 'emergency_leave',
                        'manager_query': 'manager_query',
                        'leave_policy': 'leave_policy',
                        'benefits': 'benefits',
                        'policy': 'policy',
                        'payroll': 'payroll',
                        'conduct': 'conduct',
                        'general': 'general'
                    }
                    
                    # Find best match
                    for key in intent_mapping:
                        if key in ai_intent:
                            print(f"DEBUG: Groq classified '{query}' as '{key}'")
                            return intent_mapping[key]
                    
                    print(f"DEBUG: Groq returned unmapped intent: '{ai_intent}', using fallback")
                    return self.fallback_intent_classification(query)
                    
            except Exception as e:
                print(f"Error with Groq intent classification: {e}")
                return self.fallback_intent_classification(query)
        
        # Fallback to keyword-based classification
        return self.fallback_intent_classification(query)
    
    def build_intent_classification_prompt(self, query: str, employee_context: Dict) -> str:
        """Build prompt for intent classification"""
        
        user_role = employee_context.get('user_role', 'employee')
        
        prompt = f"""
Classify the following HR-related query into one of these categories:

EMPLOYEE QUERIES:
- leave_balance: Questions about remaining leave days, balance checks
- leave_application: Requests to apply for leave, time off requests
- leave_status: Questions about existing leave application status
- leave_cancellation: Requests to cancel existing leave applications
- emergency_leave: Urgent leave requests requiring immediate attention
- leave_policy: Questions about leave policies and rules
- benefits: Questions about health insurance, retirement, benefits
- policy: Questions about company policies and procedures
- payroll: Questions about salary, pay, compensation
- conduct: Questions about workplace behavior and guidelines

MANAGER/HR QUERIES:
- manager_query: Manager asking about team leave, pending approvals, team schedules

GENERAL:
- general: Any other HR-related questions

USER CONTEXT:
- User Role: {user_role}
- Query: "{query}"

CLASSIFICATION RULES:
1. If user is a manager/HR and asks about "pending", "approval", "team leave" → manager_query
2. If asking about "balance", "remaining", "how many days" → leave_balance  
3. If requesting leave with dates/duration → leave_application
4. If asking "where is my", "status of", "approved" → leave_status
5. If contains "emergency", "urgent", "asap" → emergency_leave
6. If asking about "cancel", "withdraw" leave → leave_cancellation

Return only the category name (e.g., "leave_balance", "manager_query", etc.):
"""
        
        return prompt
    
    def fallback_intent_classification(self, query: str) -> str:
        """Fallback intent classification using keyword matching"""
        query_lower = query.lower()
        
        # Manager/HR patterns - check first for specificity
        manager_keywords = ['pending', 'approval', 'approve', 'team', 'applications', 'requests']
        if any(word in query_lower for word in manager_keywords):
            manager_patterns = [
                'pending leave', 'leave approval', 'team leave', 'who is on leave',
                'leave requests', 'pending applications', 'show me pending'
            ]
            if any(pattern in query_lower for pattern in manager_patterns):
                return 'manager_query'
        
        # Leave-related intents (priority check)
        leave_keywords = ['leave', 'vacation', 'holiday', 'time off', 'pto', 'days off', 'day off']
        balance_keywords = ['balance', 'remaining', 'left', 'how many', 'check my']
        apply_keywords = ['apply', 'request', 'take', 'book', 'need', 'want', 'get']
        status_keywords = ['status', 'approved', 'pending', 'where is', 'application']
        
        # Check for leave-related terms first
        has_leave_term = any(word in query_lower for word in leave_keywords)
        
        # Specific date patterns that indicate leave application
        date_patterns = [
            'december', 'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november',
            'next week', 'next month', 'tomorrow', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday', 'from', 'to', '-'
        ]
        has_date_pattern = any(pattern in query_lower for pattern in date_patterns)
        
        # Duration patterns
        duration_patterns = ['days', 'day', 'week', 'weeks', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        has_duration = any(pattern in query_lower for pattern in duration_patterns)
        
        # Reason patterns
        reason_patterns = ['family', 'personal', 'sick', 'vacation', 'trip', 'emergency', 'wedding', 'funeral']
        has_reason = any(pattern in query_lower for pattern in reason_patterns)
        
        # Strong leave application indicators
        strong_application_indicators = [
            'i need', 'i want', 'i would like', 'can i get', 'apply for',
            'request', 'book', 'take leave', 'time off'
        ]
        has_strong_indicator = any(indicator in query_lower for indicator in strong_application_indicators)
        
        # Classify leave intents with better logic
        if has_leave_term or has_strong_indicator or (has_date_pattern and has_duration):
            if any(word in query_lower for word in balance_keywords):
                return 'leave_balance'
            elif any(word in query_lower for word in status_keywords):
                return 'leave_status'
            elif any(word in query_lower for word in ['cancel', 'withdraw', 'remove']):
                return 'leave_cancellation'
            elif any(word in query_lower for word in ['emergency', 'urgent', 'asap']):
                return 'emergency_leave'
            elif (has_strong_indicator or 
                  (has_date_pattern and has_duration) or 
                  (has_leave_term and (has_date_pattern or has_duration or has_reason))):
                return 'leave_application'
            else:
                return 'leave_general'
        
        # Check for specific leave application patterns even without "leave" keyword
        application_patterns = [
            'i need * days', 'i want * days', 'can i get * days',
            'december *', 'january *', 'from * to *', '* for * days'
        ]
        
        for pattern in application_patterns:
            if self._matches_pattern(query_lower, pattern):
                return 'leave_application'
        
        # Other HR intents
        if any(word in query_lower for word in ['benefit', 'insurance', 'health', '401k', 'retirement']):
            return 'benefits'
        elif any(word in query_lower for word in ['policy', 'rule', 'guideline', 'procedure']):
            return 'policy'
        elif any(word in query_lower for word in ['payroll', 'salary', 'pay', 'compensation']):
            return 'payroll'
        elif any(word in query_lower for word in ['conduct', 'behavior', 'dress code', 'ethics']):
            return 'conduct'
        else:
            return 'general'
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple pattern matching with wildcards"""
        import re
        # Convert simple wildcard pattern to regex
        regex_pattern = pattern.replace('*', r'.*?')
        return bool(re.search(regex_pattern, text))
    
    def search_relevant_documents(self, db: Session, query: str, limit: int = 3) -> List[Dict]:
        """Search for relevant documents based on query (original method for backward compatibility)"""
        # Import here to avoid circular imports
        from ..models import Document
        
        query_words = query.lower().split()
        
        documents = db.query(Document).filter(Document.is_active == True).all()
        scored_docs = []
        
        for doc in documents:
            if doc.content:
                content_lower = doc.content.lower()
                score = 0
                
                # Calculate relevance score based on keyword matches
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        score += content_lower.count(word)
                
                # Boost score for title matches
                title_lower = doc.title.lower()
                for word in query_words:
                    if word in title_lower:
                        score += 3
                
                if score > 0:
                    scored_docs.append({
                        'document': doc,
                        'score': score,
                        'relevant_content': self.extract_relevant_content(doc.content, query_words)
                    })
        
        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:limit]
    
    def search_relevant_documents_from_list(self, documents: List, query: str, limit: int = 3) -> List[Dict]:
        """Search for relevant documents from a pre-filtered list (for RBAC)"""
        query_words = query.lower().split()
        scored_docs = []
        
        for doc in documents:
            if doc.content:
                content_lower = doc.content.lower()
                score = 0
                
                # Calculate relevance score based on keyword matches
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        score += content_lower.count(word)
                
                # Boost score for title matches
                title_lower = doc.title.lower()
                for word in query_words:
                    if word in title_lower:
                        score += 3
                
                if score > 0:
                    scored_docs.append({
                        'document': doc,
                        'score': score,
                        'relevant_content': self.extract_relevant_content(doc.content, query_words)
                    })
        
        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:limit]
    
    def extract_relevant_content(self, content: str, query_words: List[str], max_length: int = 500) -> str:
        """Extract most relevant content snippet from document"""
        sentences = content.split('.')
        scored_sentences = []
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue
                
            score = 0
            sentence_lower = sentence.lower()
            for word in query_words:
                if len(word) > 2 and word in sentence_lower:
                    score += 1
            
            if score > 0:
                scored_sentences.append((sentence.strip(), score))
        
        # Sort by relevance and combine top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        result = ""
        for sentence, _ in scored_sentences[:3]:
            if len(result + sentence) < max_length:
                result += sentence + ". "
            else:
                break
        
        return result.strip() if result else content[:max_length] + "..."
    
    def generate_hr_response(self, query: str, employee, relevant_docs: List[Dict], intent_classification: Dict = None) -> Dict:
        """Enhanced HR response generation with leave management support"""
        
        # Get employee context for intent classification
        employee_context = {
            "name": employee.name,
            "department": employee.department,
            "role": employee.role,
            "user_role": employee.user_role.value
        }
        
        # Check if this is a leave-related query using enhanced classification
        intent = self.classify_query_intent(query, employee_context)
        
        if intent.startswith('leave_') or intent == 'manager_query':
            # Delegate to leave service for specialized handling
            return self.generate_leave_response(query, employee, intent_classification, intent)
        
        # Handle non-leave queries with existing logic
        return self.generate_standard_hr_response(query, employee, relevant_docs)
    
    def generate_leave_response(self, query: str, employee, intent_classification: Dict = None, detected_intent: str = None) -> Dict:
        """Generate response for leave-related queries"""
        
        if intent_classification and "response" in intent_classification:
            # Use the response from the leave service
            return {
                "response": intent_classification["response"],
                "confidence": intent_classification.get("confidence", 0.8),
                "source_documents": [],
                "intent": intent_classification.get("primary_intent", detected_intent or "leave_general")
            }
        
        # Fallback for leave queries when leave service is not available
        if detected_intent == 'manager_query':
            return {
                "response": f"Hi {employee.name}! As a manager, I can help you with team leave management. Please ask about pending approvals, team leave overview, or specific leave requests.",
                "confidence": 0.7,
                "source_documents": [],
                "intent": "manager_query"
            }
        else:
            return {
                "response": f"Hi {employee.name}! I can help you with leave management. Please ask me about your leave balance, applying for leave, or checking application status.",
                "confidence": 0.7,
                "source_documents": [],
                "intent": detected_intent or "leave_general"
            }
    
    def generate_standard_hr_response(self, query: str, employee, relevant_docs: List[Dict]) -> Dict:
        """Generate AI response using Groq API with HR context"""
        
        # Build context from relevant documents
        context = ""
        source_docs = []
        
        for doc_info in relevant_docs:
            doc = doc_info['document']
            content = doc_info['relevant_content']
            context += f"\n--- {doc.title} ---\n{content}\n"
            source_docs.append(doc.id)
        
        # Create HR-specific prompt
        prompt = self.build_hr_prompt(query, employee, context)
        
        try:
            # Check if Groq client is available
            if not self.groq_client:
                return {
                    "response": "I apologize, but the AI service is currently unavailable. Please check the API configuration and try again.",
                    "confidence": 0.0,
                    "source_documents": source_docs,
                    "intent": self.classify_query_intent(query)
                }
            
            # Call Groq API
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful HR assistant. Provide accurate, professional, and empathetic responses to employee questions based on company policies and documents."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Calculate confidence score (simple heuristic)
            confidence = self.calculate_confidence_score(query, relevant_docs, ai_response)
            
            return {
                "response": ai_response,
                "confidence": confidence,
                "source_documents": source_docs,
                "intent": self.classify_query_intent(query)
            }
            
        except Exception as e:
            # Fallback response based on intent and context
            fallback_response = self.generate_fallback_response(query, employee, relevant_docs)
            
            return {
                "response": fallback_response,
                "confidence": 0.7,
                "source_documents": source_docs,
                "intent": self.classify_query_intent(query)
            }
    
    def generate_fallback_response(self, query: str, employee, relevant_docs: List[Dict]) -> str:
        """Generate fallback response when Groq API is unavailable"""
        intent = self.classify_query_intent(query)
        
        # Use relevant documents to create response
        if relevant_docs:
            doc_info = relevant_docs[0]
            content = doc_info['relevant_content']
            doc_title = doc_info['document'].title
            
            response = f"Based on our {doc_title}, here's what I found:\n\n{content}\n\n"
            response += "For more detailed information, please refer to the complete policy document or contact HR directly."
        else:
            # Intent-based fallback responses
            responses = {
                'leave_balance': f"Hi {employee.name}! I can help you check your leave balance. Please contact HR or check your employee portal for current balance information.",
                'leave_application': f"Hi {employee.name}! I can help you apply for leave. Please provide the dates you need and the type of leave (vacation, sick, personal, etc.).",
                'leave_status': f"Hi {employee.name}! I can help you check your leave application status. Please provide your application number or tell me about the leave you applied for.",
                'manager_query': f"Hi {employee.name}! As a manager, I can help you with team leave management, pending approvals, and team schedules.",
                'benefits': f"Hello {employee.name}! For benefits information, please check our Benefits Guide or contact HR. We offer health insurance, retirement benefits, professional development opportunities, and other employee benefits.",
                'policy': f"Hi {employee.name}! For policy-related questions, please refer to our policy documents or contact HR directly. All company policies are available in the employee handbook.",
                'conduct': f"Hello {employee.name}! For questions about conduct and workplace guidelines, please refer to our Code of Conduct or contact HR for clarification.",
                'general': f"Hi {employee.name}! I'm here to help with HR-related questions. You can ask me about leave policies, benefits, procedures, or any other HR topics. For specific issues, please contact HR directly."
            }
            
            response = responses.get(intent, responses['general'])
        
        return response
    
    def build_hr_prompt(self, query: str, employee, context: str) -> str:
        """Build context-aware prompt for HR queries"""
        
        employee_context = f"""
        Employee Information:
        - Name: {employee.name}
        - Department: {employee.department}
        - Role: {employee.role}
        - Employee ID: {employee.employee_id}
        """
        
        prompt = f"""
        You are an AI HR assistant helping an employee with their question.
        
        {employee_context}
        
        Employee Question: {query}
        
        Relevant Company Information:
        {context}
        
        Instructions:
        1. Answer the employee's question professionally and helpfully
        2. Base your response on the provided company information
        3. If the information is not available in the context, say so clearly
        4. Be empathetic and supportive in your tone
        5. Provide actionable steps when appropriate
        6. Keep the response concise but comprehensive
        7. For leave-related queries, be specific about policies and procedures
        
        Response:
        """
        
        return prompt
    
    def calculate_confidence_score(self, query: str, relevant_docs: List[Dict], response: str) -> float:
        """Calculate confidence score for the response"""
        # Simple confidence calculation based on:
        # 1. Number of relevant documents found
        # 2. Average relevance score of documents
        # 3. Response length (longer responses might be more detailed)
        
        if not relevant_docs:
            return 0.3
        
        doc_score = min(len(relevant_docs) / 3.0, 1.0)  # Max score if 3+ docs found
        avg_relevance = sum(doc['score'] for doc in relevant_docs) / len(relevant_docs)
        relevance_score = min(avg_relevance / 5.0, 1.0)  # Normalize to 0-1
        
        response_score = min(len(response) / 300.0, 1.0)  # Normalize response length
        
        # Weighted average
        confidence = (doc_score * 0.4 + relevance_score * 0.4 + response_score * 0.2)
        return round(confidence, 2)