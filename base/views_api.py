from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
from .models import ChatSession, Customer, LoanApplication
from .agents import MasterAgent, SalesAgent, VerificationAgent, UnderwritingAgent, SanctionLetterGenerator

@csrf_exempt
@require_http_methods(["POST"])
def start_chat(request):
    session_id = str(uuid.uuid4())
    session = ChatSession.objects.create(
        session_id=session_id,
        current_agent='master'
    )
    
    master_agent = MasterAgent()
    greeting = master_agent.greet_user(session)
    
    session.conversation_history.append({
        'role': 'assistant',
        'content': greeting,
        'agent': 'master'
    })
    session.save()
    
    return JsonResponse({
        'session_id': session_id,
        'message': greeting,
        'agent': 'master'
    })

@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    data = json.loads(request.body)
    session_id = data.get('session_id')
    user_message = data.get('message')
    
    try:
        session = ChatSession.objects.get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Invalid session'}, status=400)
    
    # Add user message to history
    session.conversation_history.append({
        'role': 'user',
        'content': user_message
    })
    
    # Process based on current agent
    if session.current_agent == 'master':
        master_agent = MasterAgent()
        next_agent = master_agent.determine_next_agent(user_message, session)
        
        if next_agent == 'sales':
            session.current_agent = 'sales'
            sales_agent = SalesAgent()
            response = sales_agent.engage_customer(session, session.conversation_history)
        else:
            response = "I didn't quite understand. Are you an existing customer or a new customer?"
    
    elif session.current_agent == 'sales':
        sales_agent = SalesAgent()
        loan_details = sales_agent.extract_loan_details(session.conversation_history)
        
        if loan_details and all(loan_details.values()):
            # Create loan application
            if not session.customer:
                # Need to verify customer first
                session.current_agent = 'verification'
                verification_agent = VerificationAgent()
                response = verification_agent.request_kyc_details(session)
            else:
                response = "Let me process your loan application..."
        else:
            response = sales_agent.engage_customer(session, session.conversation_history)
    
    elif session.current_agent == 'verification':
        # Extract KYC details and validate
        # Simplified for demo - in production, use proper extraction
        session.current_agent = 'underwriting'
        response = "KYC validated. Processing your loan application..."
    
    elif session.current_agent == 'underwriting':
        response = "Your loan has been processed. You will receive the sanction letter shortly."
        session.current_agent = 'closing'
    
    elif session.current_agent == 'closing':
        master_agent = MasterAgent()
        response = master_agent.thank_and_close(session)
    
    # Add assistant response to history
    session.conversation_history.append({
        'role': 'assistant',
        'content': response,
        'agent': session.current_agent
    })
    session.save()
    
    return JsonResponse({
        'message': response,
        'agent': session.current_agent,
        'session_id': session_id
    })