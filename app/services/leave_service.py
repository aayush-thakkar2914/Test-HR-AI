import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from groq import Groq
import re
from dateutil import parser
from decimal import Decimal

class LeaveIntentAgent:
    """Agentic AI system for sophisticated leave management intent classification"""
    
    def __init__(self):
        self.groq_client = None
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key and api_key != "your_groq_api_key_here":
                self.groq_client = Groq(api_key=api_key)
        except Exception as e:
            print(f"Groq client initialization failed: {e}")
    
    def classify_leave_intent(self, message: str, employee_context: Dict, conversation_history: List = None) -> Dict:
        """
        Advanced agentic intent classification for leave management
        """
        
        # Build context-aware prompt
        prompt = self.build_intent_classification_prompt(message, employee_context, conversation_history)
        
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert HR AI agent specializing in leave management intent classification. Analyze employee messages with high accuracy and provide structured JSON responses."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,  # Low temperature for consistent classification
                    max_tokens=800
                )
                
                # Parse AI response
                ai_response = response.choices[0].message.content
                return self.parse_intent_response(ai_response)
                
            except Exception as e:
                print(f"Groq API error in intent classification: {e}")
                return self.fallback_intent_classification(message, employee_context)
        else:
            return self.fallback_intent_classification(message, employee_context)
    
    def build_intent_classification_prompt(self, message: str, employee_context: Dict, conversation_history: List = None) -> str:
        """Build sophisticated context-aware prompt for intent classification"""
        
        history_context = ""
        if conversation_history and len(conversation_history) > 1:
            history_context = "RECENT CONVERSATION CONTEXT:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                history_context += f"- {msg['type'].upper()}: {msg['message']}\n"
            history_context += "\n"
            
            # Analyze conversation flow
            user_messages = [msg['message'] for msg in conversation_history if msg['type'] == 'user']
            assistant_messages = [msg['message'] for msg in conversation_history if msg['type'] == 'assistant']
            
            # Check if we're in a multi-turn leave application flow
            if len(assistant_messages) > 0:
                last_assistant_msg = assistant_messages[-1].lower()
                if any(phrase in last_assistant_msg for phrase in [
                    "need a bit more information", 
                    "please provide", 
                    "what type of leave",
                    "when would you like",
                    "how many days"
                ]):
                    history_context += "IMPORTANT: The assistant just requested additional information from the user. "
                    history_context += "This current message is likely providing that requested information. "
                    history_context += "Treat this as a CONTINUATION of an existing leave application process.\n\n"
        
        prompt = f"""
ROLE: You are an expert HR AI agent specializing in leave management intent classification with perfect conversation memory.

EMPLOYEE PROFILE:
- Name: {employee_context.get('name', 'Unknown')}
- Department: {employee_context.get('department', 'Unknown')}
- Role: {employee_context.get('role', 'Unknown')}
- Employee ID: {employee_context.get('employee_id', 'Unknown')}
- Current Leave Balances: {json.dumps(employee_context.get('leave_balances', {}), indent=2)}

{history_context}

CURRENT USER MESSAGE: "{message}"

CONTEXT ANALYSIS INSTRUCTIONS:
1. **ALWAYS consider the conversation history** when classifying intent
2. **If the assistant just asked for information** (dates, leave type, duration), treat the current message as providing that information
3. **Look for contextual clues** like "15th June" following a request for dates
4. **Maintain conversation continuity** - don't start over if we're mid-conversation
5. **Recognize follow-up responses** to assistant questions

ENHANCED INTENT CLASSIFICATION:
Based on conversation history and current message, determine the primary intent:

1. CHECK_BALANCE - Employee wants to know remaining leave days
2. APPLY_LEAVE - Employee wants to submit a leave application (includes follow-up responses with missing info)
3. CHECK_STATUS - Employee wants status of existing application  
4. MODIFY_LEAVE - Employee wants to change existing application
5. CANCEL_LEAVE - Employee wants to cancel pending/approved leave
6. LEAVE_POLICY - Questions about leave policies and rules
7. EMERGENCY_LEAVE - Urgent/immediate leave needed (same day/next day)
8. LEAVE_PLANNING - Future leave planning assistance
9. MANAGER_QUERY - Manager asking about team member's leave
10. GENERAL_HR - General HR query not specifically about leave
11. FOLLOW_UP_INFO - User providing requested information in a multi-turn conversation

SMART ENTITY EXTRACTION:
- **Context-Aware Date Parsing**: If previous message asked for dates, parse current message as date information
- **Conversation-Based Leave Type**: Look at conversation history for leave type context
- **Duration Inference**: Use conversation context to understand duration references
- **Follow-up Detection**: Identify when user is responding to assistant's questions

OUTPUT FORMAT (JSON):
{{
    "primary_intent": "intent_name",
    "confidence": 0.95,
    "urgency_level": "normal|urgent|emergency",
    "conversation_context": {{
        "is_continuation": true/false,
        "previous_assistant_request": "what the assistant asked for",
        "context_clues": ["relevant context from history"]
    }},
    "extracted_entities": {{
        "dates": {{
            "start_date": "2024-06-15",
            "end_date": "2024-06-15", 
            "raw_date_text": "15th June",
            "context_source": "current_message|conversation_history"
        }},
        "duration": {{
            "total_days": 1,
            "half_days": false,
            "description": "1 day"
        }},
        "leave_type": "annual|sick|personal|emergency",
        "reason": "brief reason if mentioned",
        "emergency_contact": null,
        "supporting_details": []
    }},
    "business_context": {{
        "requires_manager_approval": true,
        "affects_team_availability": true,
        "peak_period_conflict": false,
        "policy_considerations": ["standard leave policy applies"]
    }},
    "suggested_next_steps": [
        "Process leave application with provided date",
        "Confirm leave type and duration"
    ],
    "confidence_reasoning": "User provided start date '15th June' in response to assistant's request for leave application information. Clear continuation of leave application process.",
    "suggested_ai_response": "Perfect! I have your start date as June 15th. Now I need to know: 1) How many days do you need? 2) What type of leave is this (vacation, sick, personal)? 3) What's the reason for your leave?"
}}

CRITICAL CONTEXT RULES:
- If conversation shows assistant asked for information and user responds, classify as APPLY_LEAVE (continuation)
- Always extract dates even if format is informal ("15th June", "next Monday")
- Use conversation history to fill in missing context
- Maintain high confidence when context is clear from conversation flow
- Recognize that users often provide information piece by piece in conversations
"""
        
        return prompt
    
    def parse_intent_response(self, ai_response: str) -> Dict:
        """Parse and validate AI intent classification response"""
        try:
            # Extract JSON from response (handle cases where AI adds explanation)
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                intent_data = json.loads(json_str)
                
                # Validate and normalize response
                return self.validate_intent_response(intent_data)
            else:
                raise ValueError("No valid JSON found in AI response")
                
        except Exception as e:
            print(f"Error parsing intent response: {e}")
            return self.create_default_intent_response()
    
    def validate_intent_response(self, intent_data: Dict) -> Dict:
        """Validate and normalize intent response structure"""
        
        # Ensure required fields exist
        validated = {
            "primary_intent": intent_data.get("primary_intent", "GENERAL_HR"),
            "confidence": min(max(intent_data.get("confidence", 0.5), 0.0), 1.0),
            "urgency_level": intent_data.get("urgency_level", "normal"),
            "extracted_entities": intent_data.get("extracted_entities", {}),
            "business_context": intent_data.get("business_context", {}),
            "suggested_next_steps": intent_data.get("suggested_next_steps", []),
            "confidence_reasoning": intent_data.get("confidence_reasoning", ""),
            "suggested_ai_response": intent_data.get("suggested_ai_response", "")
        }
        
        # Validate and parse dates
        if "dates" in validated["extracted_entities"]:
            validated["extracted_entities"]["dates"] = self.parse_and_validate_dates(
                validated["extracted_entities"]["dates"]
            )
        
        return validated
    
    def parse_and_validate_dates(self, date_info: Dict) -> Dict:
        """Parse and validate extracted date information"""
        validated_dates = {
            "start_date": None,
            "end_date": None,
            "raw_date_text": date_info.get("raw_date_text", ""),
            "parsing_confidence": "low"
        }
        
        try:
            # Try to parse start date
            if "start_date" in date_info and date_info["start_date"]:
                start_date = parser.parse(date_info["start_date"]).date()
                validated_dates["start_date"] = start_date.isoformat()
                validated_dates["parsing_confidence"] = "high"
            
            # Try to parse end date
            if "end_date" in date_info and date_info["end_date"]:
                end_date = parser.parse(date_info["end_date"]).date()
                validated_dates["end_date"] = end_date.isoformat()
            elif validated_dates["start_date"]:
                # If only start date, assume single day
                validated_dates["end_date"] = validated_dates["start_date"]
                
        except Exception as e:
            print(f"Date parsing error: {e}")
            validated_dates["parsing_confidence"] = "failed"
        
        return validated_dates
    
    def fallback_intent_classification(self, message: str, employee_context: Dict) -> Dict:
        """Fallback intent classification when Groq API is unavailable"""
        
        message_lower = message.lower()
        
        # Simple keyword-based fallback
        if any(word in message_lower for word in ['balance', 'remaining', 'left', 'how many']):
            intent = "CHECK_BALANCE"
        elif any(word in message_lower for word in ['apply', 'request', 'take leave', 'need time off']):
            intent = "APPLY_LEAVE"
        elif any(word in message_lower for word in ['status', 'approved', 'pending', 'where is my']):
            intent = "CHECK_STATUS"
        elif any(word in message_lower for word in ['cancel', 'withdraw', 'remove']):
            intent = "CANCEL_LEAVE"
        elif any(word in message_lower for word in ['emergency', 'urgent', 'asap', 'immediately']):
            intent = "EMERGENCY_LEAVE"
        elif any(word in message_lower for word in ['policy', 'rule', 'allowed', 'maximum']):
            intent = "LEAVE_POLICY"
        else:
            intent = "GENERAL_HR"
        
        return {
            "primary_intent": intent,
            "confidence": 0.6,
            "urgency_level": "urgent" if "emergency" in message_lower else "normal",
            "extracted_entities": {},
            "business_context": {},
            "suggested_next_steps": [],
            "confidence_reasoning": "Fallback keyword-based classification",
            "suggested_ai_response": f"I'll help you with your {intent.lower().replace('_', ' ')} request."
        }
    
    def create_default_intent_response(self) -> Dict:
        """Create default response when classification fails"""
        return {
            "primary_intent": "GENERAL_HR",
            "confidence": 0.3,
            "urgency_level": "normal",
            "extracted_entities": {},
            "business_context": {},
            "suggested_next_steps": ["Ask for clarification"],
            "confidence_reasoning": "Classification failed, using default",
            "suggested_ai_response": "I'd be happy to help! Could you please clarify what you need assistance with regarding leave management?"
        }


class LeaveService:
    """Core leave management service with agentic AI integration"""
    
    def __init__(self):
        self.intent_agent = LeaveIntentAgent()
    
    def get_employee_leave_balances(self, db: Session, employee_id: int, year: int = None) -> Dict:
        """Get employee's current leave balances"""
        from ..models import LeaveBalance, LeaveType
        
        if year is None:
            year = datetime.now().year
        
        print(f"Looking for leave balances for employee_id: {employee_id}, year: {year}")
        
        balances = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == year
        ).all()
        
        print(f"Found {len(balances)} leave balance records")
        
        # If no balances found, create them
        if not balances:
            print(f"No leave balances found, creating default balances...")
            self.create_default_leave_balances(db, employee_id, year)
            # Query again after creation
            balances = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year
            ).all()
            print(f"After creation, found {len(balances)} leave balance records")
        
        # Convert to dict format
        balance_dict = {}
        for balance in balances:
            balance_dict[balance.leave_type.value] = {
                "total_allocated": float(balance.total_allocated),
                "used_days": float(balance.used_days),
                "pending_days": float(balance.pending_days),
                "remaining_days": float(balance.remaining_days),
                "carried_forward": float(balance.carried_forward)
            }
        
        return balance_dict
    
    def create_default_leave_balances(self, db: Session, employee_id: int, year: int):
        """Create default leave balances for an employee"""
        from ..models import LeaveBalance, LeaveType
        from decimal import Decimal
        
        # Standard leave allocations
        leave_allocations = {
            LeaveType.ANNUAL: 21.0,
            LeaveType.SICK: 10.0,
            LeaveType.PERSONAL: 5.0,
            LeaveType.EMERGENCY: 5.0,
            LeaveType.PATERNITY: 15.0  # Default for all, can be adjusted
        }
        
        for leave_type, allocated_days in leave_allocations.items():
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type=leave_type,
                year=year,
                total_allocated=Decimal(str(allocated_days)),
                used_days=Decimal('0.0'),
                pending_days=Decimal('0.0'),
                remaining_days=Decimal(str(allocated_days)),
                carried_forward=Decimal('0.0')
            )
            db.add(balance)
            print(f"Created balance: {leave_type.value} = {allocated_days} days")
        
        try:
            db.commit()
            print("Successfully created default leave balances")
        except Exception as e:
            print(f"Error creating default balances: {e}")
            db.rollback()
    
    def process_leave_chat_message(self, db: Session, message: str, employee, conversation_history: List = None) -> Dict:
        """Process employee chat message with agentic intent classification"""
        
        # Get employee context for AI agent
        employee_context = {
            "name": employee.name,
            "employee_id": employee.employee_id,
            "department": employee.department,
            "role": employee.role,
            "user_role": employee.user_role.value,
            "leave_balances": self.get_employee_leave_balances(db, employee.id)
        }
        
        # Classify intent using agentic AI
        intent_result = self.intent_agent.classify_leave_intent(
            message, employee_context, conversation_history
        )
        
        # Route to appropriate handler based on intent
        response = self.route_intent_to_handler(db, intent_result, employee, message)
        
        return {
            "intent_classification": intent_result,
            "response": response["response"],
            "confidence": response["confidence"],
            "actions_performed": response.get("actions_performed", []),
            "follow_up_needed": response.get("follow_up_needed", False)
        }
    
    def route_intent_to_handler(self, db: Session, intent_result: Dict, employee, original_message: str) -> Dict:
        """Route classified intent to appropriate handler"""
        
        intent = intent_result["primary_intent"]
        entities = intent_result["extracted_entities"]
        
        handlers = {
            "CHECK_BALANCE": self.handle_balance_inquiry,
            "APPLY_LEAVE": self.handle_leave_application,
            "CHECK_STATUS": self.handle_status_inquiry,
            "MODIFY_LEAVE": self.handle_leave_modification,
            "CANCEL_LEAVE": self.handle_leave_cancellation,
            "LEAVE_POLICY": self.handle_policy_inquiry,
            "EMERGENCY_LEAVE": self.handle_emergency_leave,
            "LEAVE_PLANNING": self.handle_leave_planning,
            "MANAGER_QUERY": self.handle_manager_query,
            "GENERAL_HR": self.handle_general_hr_query
        }
        
        handler = handlers.get(intent, self.handle_general_hr_query)
        
        try:
            return handler(db, intent_result, employee, original_message)
        except Exception as e:
            print(f"Error in leave handler {intent}: {e}")
            # Fallback response
            return {
                "response": f"Hi {employee.name}! I'm having trouble processing your request right now. Could you please try rephrasing your question or contact HR directly for assistance?",
                "confidence": 0.3,
                "error": str(e)
            }
    
    def handle_balance_inquiry(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave balance inquiries"""
        
        balances = self.get_employee_leave_balances(db, employee.id)
        
        if not balances:
            response = f"Hi {employee.name}! I don't see any leave balances set up for you yet. Please contact HR to initialize your leave entitlements."
            return {"response": response, "confidence": 0.9}
        
        # Format balance information
        balance_text = f"Hi {employee.name}! Here are your current leave balances:\n\n"
        
        for leave_type, balance in balances.items():
            balance_text += f"📅 **{leave_type.title()} Leave:**\n"
            balance_text += f"   • Remaining: {balance['remaining_days']} days\n"
            balance_text += f"   • Used: {balance['used_days']} days\n"
            balance_text += f"   • Total Allocated: {balance['total_allocated']} days\n"
            if balance['pending_days'] > 0:
                balance_text += f"   • Pending Approval: {balance['pending_days']} days\n"
            balance_text += "\n"
        
        balance_text += "💡 Need to apply for leave? Just ask me!"
        
        return {
            "response": balance_text,
            "confidence": 0.95,
            "actions_performed": ["balance_lookup"]
        }
    
    def handle_leave_application(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave application requests with context awareness"""
        
        entities = intent_result["extracted_entities"]
        urgency = intent_result["urgency_level"]
        conversation_context = intent_result.get("conversation_context", {})
        
        # Check if this is a continuation of a previous request
        is_continuation = conversation_context.get("is_continuation", False)
        
        # Check if we have enough information to proceed
        missing_info = []
        
        # Check dates
        dates = entities.get("dates", {})
        if not dates.get("start_date") or dates.get("parsing_confidence") == "failed":
            missing_info.append("start date")
        
        # Check leave type
        leave_type = entities.get("leave_type")
        if not leave_type:
            missing_info.append("type of leave (vacation, sick, personal, etc.)")
        
        # Check duration for multi-day leaves
        duration = entities.get("duration", {})
        if not dates.get("end_date") and not duration.get("total_days"):
            missing_info.append("duration or end date")
        
        # If this is a continuation and we have some info, be more flexible
        if is_continuation and len(missing_info) < 3:
            # Try to proceed with partial information and ask for what's still missing
            if missing_info:
                return self.request_remaining_information(missing_info, employee, intent_result, entities)
            else:
                # We have enough information, proceed with application
                return self.create_leave_application(db, intent_result, employee)
        elif missing_info:
            return self.request_missing_information(missing_info, employee, intent_result)
        
        # Proceed with application creation if we have all information
        return self.create_leave_application(db, intent_result, employee)
    
    def request_remaining_information(self, missing_info: List[str], employee, intent_result: Dict, existing_entities: Dict) -> Dict:
        """Request remaining information when we have partial details"""
        
        entities = existing_entities
        
        response = f"Great! I have some details for your leave application:\n\n"
        
        # Show what we already have
        dates = entities.get("dates", {})
        if dates.get("start_date"):
            response += f"✅ **Start Date**: {dates['start_date']}\n"
        
        duration = entities.get("duration", {})
        if duration.get("total_days"):
            response += f"✅ **Duration**: {duration['total_days']} day(s)\n"
        
        leave_type = entities.get("leave_type")
        if leave_type:
            response += f"✅ **Leave Type**: {leave_type.title()}\n"
        
        reason = entities.get("reason")
        if reason:
            response += f"✅ **Reason**: {reason}\n"
        
        response += f"\n📝 **Still need:**\n"
        for i, info in enumerate(missing_info, 1):
            response += f"{i}. {info.title()}\n"
        
        response += f"\nPlease provide the missing information so I can complete your leave application."
        
        return {
            "response": response,
            "confidence": 0.85,
            "follow_up_needed": True,
            "missing_information": missing_info,
            "partial_application_data": entities
        }
    
    def request_missing_information(self, missing_info: List[str], employee, intent_result: Dict) -> Dict:
        """Request missing information for leave application"""
        
        response = f"Hi {employee.name}! I'd be happy to help you apply for leave. "
        response += f"I need a bit more information:\n\n"
        
        for i, info in enumerate(missing_info, 1):
            response += f"{i}. {info.title()}\n"
        
        response += "\nFor example, you can say: 'I need 3 days of vacation leave from December 15-17 for a family trip'"
        
        return {
            "response": response,
            "confidence": 0.8,
            "follow_up_needed": True,
            "missing_information": missing_info
        }
    
    def create_leave_application(self, db: Session, intent_result: Dict, employee) -> Dict:
        """Create a new leave application"""
        from ..models import LeaveApplication, LeaveType, LeaveStatus
        
        try:
            entities = intent_result["extracted_entities"]
            dates = entities["dates"]
            
            # Parse dates
            start_date = parser.parse(dates["start_date"]).date()
            end_date = parser.parse(dates["end_date"]).date() if dates["end_date"] else start_date
            
            # Calculate total days
            total_days = (end_date - start_date).days + 1
            
            # Determine leave type
            leave_type_str = entities.get("leave_type", "annual")
            try:
                leave_type = LeaveType(leave_type_str.lower())
            except ValueError:
                leave_type = LeaveType.ANNUAL  # Default to annual leave
            
            # Generate application number
            app_number = self.generate_application_number(db)
            
            # Get manager ID (if available)
            manager_id = employee.manager_id if hasattr(employee, 'manager_id') else None
            
            # Create application
            application = LeaveApplication(
                application_number=app_number,
                employee_id=employee.id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                total_days=Decimal(str(total_days)),
                reason=entities.get("reason", "Personal leave"),
                manager_id=manager_id,
                created_via="chat"
            )
            
            db.add(application)
            db.flush()  # Get the ID
            
            # Update leave balance (mark as pending)
            self.update_leave_balance_pending(db, employee.id, leave_type, total_days)
            
            db.commit()
            
            # Generate confirmation response
            response = f"✅ **Leave Application Submitted Successfully!**\n\n"
            response += f"📋 **Application Details:**\n"
            response += f"   • Application Number: {app_number}\n"
            response += f"   • Leave Type: {leave_type.value.title()}\n"
            response += f"   • Dates: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}\n"
            response += f"   • Duration: {total_days} day(s)\n"
            response += f"   • Reason: {entities.get('reason', 'Personal leave')}\n\n"
            
            if manager_id:
                response += f"🔄 **Next Steps:**\n"
                response += f"   • Your application has been sent to your manager for approval\n"
                response += f"   • You'll receive notifications on status updates\n"
                response += f"   • You can check status anytime by asking me\n\n"
            else:
                response += f"⚠️ **Note:** No manager assigned. Please contact HR for approval process.\n\n"
            
            response += f"💡 **Tip:** Save your application number {app_number} for future reference!"
            
            return {
                "response": response,
                "confidence": 0.95,
                "actions_performed": ["application_created", "balance_updated"],
                "application_id": application.id,
                "application_number": app_number
            }
            
        except Exception as e:
            db.rollback()
            return {
                "response": f"I encountered an error while processing your leave application: {str(e)}. Please try again or contact HR for assistance.",
                "confidence": 0.3,
                "error": str(e)
            }
    
    def handle_status_inquiry(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave application status inquiries"""
        from ..models import LeaveApplication
        
        # Get recent applications for this employee
        applications = db.query(LeaveApplication).filter(
            LeaveApplication.employee_id == employee.id
        ).order_by(LeaveApplication.applied_date.desc()).limit(5).all()
        
        if not applications:
            response = f"Hi {employee.name}! I don't see any leave applications in our system. Would you like to apply for leave?"
            return {"response": response, "confidence": 0.9}
        
        # Format status information
        response = f"Hi {employee.name}! Here's the status of your recent leave applications:\n\n"
        
        for app in applications:
            status_emoji = {
                "pending": "⏳",
                "manager_approved": "✅",
                "approved": "✅",
                "rejected": "❌",
                "cancelled": "🚫"
            }.get(app.status.value, "❓")
            
            response += f"{status_emoji} **{app.application_number}**\n"
            response += f"   • Type: {app.leave_type.value.title()}\n"
            response += f"   • Dates: {app.start_date.strftime('%b %d')} - {app.end_date.strftime('%b %d, %Y')}\n"
            response += f"   • Status: {app.status.value.replace('_', ' ').title()}\n"
            response += f"   • Applied: {app.applied_date.strftime('%b %d, %Y')}\n"
            
            if app.manager_comments:
                response += f"   • Manager Notes: {app.manager_comments}\n"
            if app.hr_comments:
                response += f"   • HR Notes: {app.hr_comments}\n"
            
            response += "\n"
        
        response += "💡 Need help with any of these applications? Just ask!"
        
        return {
            "response": response,
            "confidence": 0.95,
            "actions_performed": ["status_lookup"]
        }
    
    def handle_leave_modification(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave modification requests"""
        response = f"Hi {employee.name}! I can help you modify an existing leave application. "
        response += f"Please provide:\n\n"
        response += f"📝 **Information Needed:**\n"
        response += f"   • Application number or dates of the leave to modify\n"
        response += f"   • What you'd like to change (dates, duration, reason)\n"
        response += f"   • New details\n\n"
        response += f"For example: 'I want to change my Dec 15-17 leave to Dec 20-22'\n\n"
        response += f"⚠️ **Note:** Only pending applications can be modified."
        
        return {
            "response": response,
            "confidence": 0.8,
            "follow_up_needed": True
        }
        """Handle leave cancellation requests"""
        # Implementation for cancellation
        response = f"Hi {employee.name}! I can help you cancel a leave application. Could you please provide the application number or tell me which leave you'd like to cancel?"
        
        return {
            "response": response,
            "confidence": 0.8,
            "follow_up_needed": True
        }
    
    def handle_policy_inquiry(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave policy questions"""
        # Basic policy information
        response = f"Hi {employee.name}! Here are some key leave policy highlights:\n\n"
        response += f"📋 **Leave Types Available:**\n"
        response += f"   • Annual Leave: 21 days per year\n"
        response += f"   • Sick Leave: 10 days per year\n"
        response += f"   • Personal Leave: 5 days per year\n"
        response += f"   • Maternity/Paternity Leave: As per policy\n\n"
        response += f"⏰ **Application Process:**\n"
        response += f"   • Submit requests at least 3 days in advance\n"
        response += f"   • Manager approval required\n"
        response += f"   • HR approval for extended leave\n\n"
        response += f"💡 Have a specific policy question? Feel free to ask!"
        
        return {
            "response": response,
            "confidence": 0.8
        }
    def handle_leave_cancellation(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave cancellation requests"""
        from ..models import LeaveApplication, LeaveStatus
        
        # Get recent applications that can be cancelled
        applications = db.query(LeaveApplication).filter(
            LeaveApplication.employee_id == employee.id,
            LeaveApplication.status.in_([LeaveStatus.PENDING, LeaveStatus.MANAGER_APPROVED])
        ).order_by(LeaveApplication.applied_date.desc()).limit(5).all()
        
        if not applications:
            response = f"Hi {employee.name}! I don't see any leave applications that can be cancelled. "
            response += f"Only pending or manager-approved applications can be cancelled."
            return {"response": response, "confidence": 0.9}
        
        response = f"Hi {employee.name}! I can help you cancel a leave application. "
        response += f"Here are your applications that can be cancelled:\n\n"
        
        for app in applications:
            status_emoji = "⏳" if app.status == LeaveStatus.PENDING else "✅"
            response += f"{status_emoji} **{app.application_number}**\n"
            response += f"   • Dates: {app.start_date.strftime('%b %d')} - {app.end_date.strftime('%b %d, %Y')}\n"
            response += f"   • Type: {app.leave_type.value.title()}\n"
            response += f"   • Status: {app.status.value.replace('_', ' ').title()}\n\n"
        
        response += f"Please tell me which application you'd like to cancel by providing:\n"
        response += f"   • Application number, or\n"
        response += f"   • The dates of the leave\n\n"
        response += f"For example: 'Cancel application LA2024-0002' or 'Cancel my Dec 20-24 leave'"
        
        return {
            "response": response,
            "confidence": 0.8,
            "follow_up_needed": True
        }
        
    def handle_emergency_leave(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle emergency leave requests"""
        response = f"Hi {employee.name}! I understand this is an emergency situation. For urgent leave requests:\n\n"
        response += f"🚨 **Immediate Actions:**\n"
        response += f"   1. I'll flag this as emergency leave\n"
        response += f"   2. Notify your manager immediately\n"
        response += f"   3. Process with expedited approval\n\n"
        response += f"Please provide:\n"
        response += f"   • How many days you need\n"
        response += f"   • Brief reason for emergency\n"
        response += f"   • Emergency contact if needed\n\n"
        response += f"I'll help you submit this right away! 🏃‍♂️"
        
        return {
            "response": response,
            "confidence": 0.9,
            "follow_up_needed": True,
            "urgency": "emergency"
        }
    
    def handle_leave_planning(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle leave planning assistance"""
        response = f"Hi {employee.name}! I'd be happy to help you plan your leave. "
        response += f"I can assist with:\n\n"
        response += f"📅 **Planning Tools:**\n"
        response += f"   • Check your remaining balance\n"
        response += f"   • Suggest optimal dates\n"
        response += f"   • Check team availability\n"
        response += f"   • Plan around holidays\n\n"
        response += f"What would you like help with?"
        
        return {
            "response": response,
            "confidence": 0.8,
            "follow_up_needed": True
        }
    
    def handle_manager_query(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle manager queries about team leave"""
        from ..models import LeaveApplication, LeaveStatus, UserRole
        
        if employee.user_role not in [UserRole.MANAGER, UserRole.HR_MANAGER, UserRole.HR_ADMIN]:
            return {
                "response": "I can only provide team leave information to managers and HR personnel.",
                "confidence": 0.9
            }
        
        message_lower = message.lower()
        
        # Check if asking for pending approvals
        if any(word in message_lower for word in ['pending', 'approval', 'approve', 'waiting']):
            return self.get_pending_approvals_for_manager(db, employee)
        
        # Check if asking for team leave overview
        elif any(word in message_lower for word in ['team', 'overview', 'calendar', 'schedule']):
            return self.get_team_leave_overview(db, employee)
        
        # General manager help
        else:
            response = f"Hi {employee.name}! As a {'HR' if 'HR' in employee.user_role.value else 'manager'}, I can help you with:\n\n"
            response += f"👥 **Team Leave Management:**\n"
            response += f"   • 'Show pending leave approvals' - Review applications waiting for approval\n"
            response += f"   • 'Team leave overview' - See upcoming team leave\n"
            response += f"   • 'Who's on leave this week?' - Check current leave status\n\n"
            
            # Show quick stats
            try:
                pending_count = self.get_pending_count(db, employee)
                if pending_count > 0:
                    response += f"⚠️ **Alert**: You have {pending_count} leave application(s) pending your approval!\n\n"
                else:
                    response += f"✅ **Status**: No pending leave approvals at the moment.\n\n"
            except:
                pass
            
            response += f"What would you like to check?"
            
            return {
                "response": response,
                "confidence": 0.8,
                "follow_up_needed": True
            }
    
    def get_pending_approvals_for_manager(self, db: Session, employee) -> Dict:
        """Get pending leave applications for manager/HR approval"""
        from ..models import LeaveApplication, LeaveStatus, UserRole
        
        try:
            # Get applications pending approval
            query = db.query(LeaveApplication).filter(
                LeaveApplication.status.in_([LeaveStatus.PENDING, LeaveStatus.MANAGER_APPROVED])
            )
            
            # If manager, only show their team's applications
            if employee.user_role == UserRole.MANAGER:
                query = query.filter(LeaveApplication.manager_id == employee.id)
            
            applications = query.order_by(LeaveApplication.applied_date.asc()).all()
            
            if not applications:
                response = f"✅ **Great news, {employee.name}!**\n\n"
                response += f"You have no pending leave applications to review at the moment.\n\n"
                response += f"💡 **Tip**: When employees submit leave requests, they'll appear here for your approval."
                
                return {
                    "response": response,
                    "confidence": 0.95,
                    "actions_performed": ["pending_approvals_check"]
                }
            
            # Format pending applications
            response = f"📋 **Pending Leave Approvals for {employee.name}**\n\n"
            response += f"You have **{len(applications)}** application(s) waiting for approval:\n\n"
            
            for i, app in enumerate(applications, 1):
                urgency_emoji = "🚨" if app.leave_type.value == "emergency" else "📅"
                status_text = "Manager Review" if app.status == LeaveStatus.PENDING else "HR Review"
                
                response += f"{urgency_emoji} **Application #{i}**\n"
                response += f"   • **Employee**: {app.employee.name} ({app.employee.department})\n"
                response += f"   • **Application**: {app.application_number}\n"
                response += f"   • **Type**: {app.leave_type.value.title()} Leave\n"
                response += f"   • **Dates**: {app.start_date.strftime('%b %d')} - {app.end_date.strftime('%b %d, %Y')}\n"
                response += f"   • **Duration**: {float(app.total_days)} day(s)\n"
                response += f"   • **Reason**: {app.reason or 'Not specified'}\n"
                response += f"   • **Applied**: {app.applied_date.strftime('%b %d, %Y')}\n"
                response += f"   • **Status**: {status_text}\n"
                
                if app.leave_type.value == "emergency":
                    response += f"   • ⚠️ **URGENT**: Emergency leave - requires immediate attention\n"
                
                response += f"\n"
            
            response += f"🔧 **Next Steps:**\n"
            response += f"   • Visit the HR Management panel to approve/reject applications\n"
            response += f"   • Or ask me 'How do I approve leave applications?'\n\n"
            response += f"💡 **Need help?** Ask me about specific applications or approval processes!"
            
            return {
                "response": response,
                "confidence": 0.95,
                "actions_performed": ["pending_approvals_retrieved"],
                "pending_count": len(applications)
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error retrieving pending approvals: {str(e)}. Please try again or check the HR Management panel.",
                "confidence": 0.3,
                "error": str(e)
            }
    
    def get_pending_count(self, db: Session, employee) -> int:
        """Get count of pending applications for quick stats"""
        from ..models import LeaveApplication, LeaveStatus, UserRole
        
        query = db.query(LeaveApplication).filter(
            LeaveApplication.status.in_([LeaveStatus.PENDING, LeaveStatus.MANAGER_APPROVED])
        )
        
        if employee.user_role == UserRole.MANAGER:
            query = query.filter(LeaveApplication.manager_id == employee.id)
        
        return query.count()
    
    def get_team_leave_overview(self, db: Session, employee) -> Dict:
        """Get team leave overview for managers"""
        from ..models import LeaveApplication, LeaveStatus
        from datetime import date, timedelta
        
        try:
            # Get approved leave for next 30 days
            start_date = date.today()
            end_date = start_date + timedelta(days=30)
            
            query = db.query(LeaveApplication).filter(
                LeaveApplication.status == LeaveStatus.HR_APPROVED,
                LeaveApplication.start_date <= end_date,
                LeaveApplication.end_date >= start_date
            )
            
            # Filter by team if manager
            if employee.user_role.value == "manager":
                query = query.filter(LeaveApplication.manager_id == employee.id)
            
            upcoming_leave = query.order_by(LeaveApplication.start_date).all()
            
            if not upcoming_leave:
                response = f"📅 **Team Leave Overview**\n\n"
                response += f"✅ No approved leave scheduled for the next 30 days.\n"
                response += f"Your team will be fully available! 🎉"
                
                return {
                    "response": response,
                    "confidence": 0.9
                }
            
            response = f"📅 **Upcoming Team Leave (Next 30 Days)**\n\n"
            
            for app in upcoming_leave:
                response += f"🏖️ **{app.employee.name}**\n"
                response += f"   • {app.start_date.strftime('%b %d')} - {app.end_date.strftime('%b %d')}\n"
                response += f"   • {app.leave_type.value.title()} Leave ({float(app.total_days)} days)\n"
                response += f"   • Reason: {app.reason or 'Personal'}\n\n"
            
            response += f"💡 **Planning tip**: Consider workload distribution during these periods."
            
            return {
                "response": response,
                "confidence": 0.9,
                "actions_performed": ["team_overview_generated"]
            }
            
        except Exception as e:
            return {
                "response": f"Error generating team overview: {str(e)}",
                "confidence": 0.3,
                "error": str(e)
            }
    
    def handle_general_hr_query(self, db: Session, intent_result: Dict, employee, message: str) -> Dict:
        """Handle general HR queries that may be leave-related"""
        # Check if the message mentions leave-related terms
        message_lower = message.lower()
        leave_keywords = ['leave', 'vacation', 'holiday', 'time off', 'pto', 'sick', 'personal', 'day off']
        
        if any(keyword in message_lower for keyword in leave_keywords):
            response = f"Hi {employee.name}! I can help you with leave management. "
            response += f"Here's what I can do:\n\n"
            response += f"🏖️ **Leave Services:**\n"
            response += f"   • Check your leave balance: 'What's my leave balance?'\n"
            response += f"   • Apply for leave: 'I need 3 days off next week'\n"
            response += f"   • Check application status: 'Where is my leave request?'\n"
            response += f"   • Leave policy questions: 'How many sick days do I get?'\n"
            response += f"   • Cancel or modify requests: 'Cancel my vacation'\n\n"
            response += f"💡 **Quick Balance Check:**\n"
            
            # Try to show current balance
            try:
                balances = self.get_employee_leave_balances(db, employee.id)
                if balances:
                    response += f"   • Annual Leave: {balances.get('annual', {}).get('remaining_days', 0)} days remaining\n"
                    response += f"   • Sick Leave: {balances.get('sick', {}).get('remaining_days', 0)} days remaining\n"
                else:
                    response += f"   • Contact HR to set up your leave balances\n"
            except:
                response += f"   • Ask me 'What's my leave balance?' for details\n"
            
            response += f"\nWhat can I help you with today?"
        else:
            response = f"Hi {employee.name}! I'm here to help with HR-related questions. "
            response += f"I specialize in leave management, but I can also help with:\n\n"
            response += f"📋 **General HR Support:**\n"
            response += f"   • Company policies and procedures\n"
            response += f"   • Benefits information\n"
            response += f"   • HR contact information\n"
            response += f"   • General workplace guidance\n\n"
            response += f"🏖️ **Leave Management (My Specialty):**\n"
            response += f"   • Check leave balances\n"
            response += f"   • Apply for time off\n"
            response += f"   • Track application status\n\n"
            response += f"How can I assist you today?"
        
        return {
            "response": response,
            "confidence": 0.7,
            "follow_up_needed": True
        }
    
    def generate_application_number(self, db: Session) -> str:
        """Generate unique application number"""
        from ..models import LeaveApplication
        
        year = datetime.now().year
        
        # Count applications this year
        count = db.query(LeaveApplication).filter(
            LeaveApplication.applied_date >= datetime(year, 1, 1)
        ).count()
        
        return f"LA{year}-{count + 1:04d}"
    
    def update_leave_balance_pending(self, db: Session, employee_id: int, leave_type, days: float):
        """Update leave balance when application is pending"""
        from ..models import LeaveBalance
        
        year = datetime.now().year
        
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type,
            LeaveBalance.year == year
        ).first()
        
        if balance:
            balance.pending_days = float(balance.pending_days) + days
            balance.remaining_days = float(balance.remaining_days) - days
            balance.last_updated = datetime.utcnow()
            db.flush()
    
    def finalize_leave_balance(self, db: Session, employee_id: int, leave_type, days: float, approved: bool):
        """Finalize leave balance when application is approved/rejected"""
        from ..models import LeaveBalance
        
        year = datetime.now().year
        
        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type,
            LeaveBalance.year == year
        ).first()
        
        if balance:
            # Remove from pending
            balance.pending_days = float(balance.pending_days) - days
            
            if approved:
                # Move to used days
                balance.used_days = float(balance.used_days) + days
                # remaining_days already reduced when application was created
            else:
                # Restore remaining days
                balance.remaining_days = float(balance.remaining_days) + days
            
            balance.last_updated = datetime.utcnow()
            db.flush()