from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404, render
from django.core.files.storage import default_storage
import json
from .models import ChatSession, Customer, LoanApplication
from .agents import (
    MasterAgent, 
    PANVerificationAgent,
    FaceMatchAgent,
    SalesAgent, 
    VerificationAgent, 
    UnderwritingAgent, 
    SanctionLetterGenerator,
    CustomerSegmentation)


def index(request):
    """Main chat interface"""
    return render(request, 'chat.html')


def get_conversation(session):
    """Helper to get conversation history from session"""
    return session.get_conversation_history()


def add_message(session, role, content, agent=None):
    """Helper to add a message to conversation history"""
    conversation = get_conversation(session)
    message = {
        'role': role,
        'content': content
    }
    if agent:
        message['agent'] = agent
    conversation.append(message)
    session.conversation_data = json.dumps(conversation)
    return conversation


def get_age_segment(session):
    """Helper to get customer age segment from session"""
    if not session.customer or not session.customer.date_of_birth:
        return None
    
    age = CustomerSegmentation.get_age_from_dob(session.customer.date_of_birth)
    if age is None:
        return None
    
    employment_type = session.customer.employment_type if hasattr(session.customer, 'employment_type') else None
    monthly_income = session.customer.monthly_income if hasattr(session.customer, 'monthly_income') else None
    
    return CustomerSegmentation.determine_segment(age, employment_type, monthly_income)


@csrf_exempt
@require_http_methods(["POST"])
def upload_selfie(request):
    """Handle selfie upload and face matching with PAN card"""
    session_id = request.POST.get('session_id')
    selfie_image = request.FILES.get('selfie_image')
    
    if not selfie_image:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a selfie image'
        }, status=400)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if selfie_image.content_type not in allowed_types:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a valid image file (JPEG, PNG, or WebP)'
        }, status=400)
    
    # Validate file size (max 5MB)
    if selfie_image.size > 5 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'Image size should be less than 5MB'
        }, status=400)
    
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid session. Please refresh and try again.'
        }, status=404)
    
    # Check if customer exists and PAN is verified
    if not session.customer or not session.customer.pan_verified:
        return JsonResponse({
            'success': False,
            'message': 'PAN card verification not completed. Please complete previous steps.'
        }, status=400)
    
    # ✅ Check if we have temporary PAN image data for face matching
    if not session.temp_pan_image_data:
        return JsonResponse({
            'success': False,
            'message': 'PAN card image data not found. Please upload your PAN card again.',
            'requires_pan_reupload': True,
            'workflow_stage': 'pan_verification'
        }, status=400)
    
    try:
        customer = session.customer
        
        # Get age segment
        age_segment = get_age_segment(session)
        
        # Initialize face match agent
        face_agent = FaceMatchAgent()
        
        # Read selfie image data directly from memory
        selfie_image.seek(0)
        selfie_data = selfie_image.read()
        
        # ✅ Decode PAN card image from base64
        pan_card_data = base64.b64decode(session.temp_pan_image_data)
        
        # Perform face matching using raw bytes
        match_result = face_agent.match_faces(selfie_data, pan_card_data)
        
        # Generate human-readable report
        match_message = face_agent.generate_match_report(match_result)
        
        # Check if faces match (20% threshold)
        confidence = match_result.get('confidence_score', 0)
        faces_match = match_result.get('faces_match', False)
        
        if faces_match and confidence >= 20:
            # Face match successful
            # ✅ NO FILE STORAGE - Just save verification metadata
            customer.selfie_verified = True
            customer.face_match_verified = True
            customer.face_match_confidence = confidence
            customer.save()
            
            # ✅ Clear temporary PAN image data (no longer needed)
            session.temp_pan_image_data = None
            
            # Update session to loan details stage
            session.stage = 'loan_details'
            session.save()
            
            # Add match message to conversation
            conversation = add_message(session, 'assistant', match_message, 'verification')
            
            # Get sales agent to start loan discussion with age-aware messaging
            sales_agent = SalesAgent()
            loan_message = sales_agent.engage_customer(session, conversation, age_segment)
            
            add_message(session, 'assistant', loan_message, 'sales')
            
            return JsonResponse({
                'success': True,
                'verified': True,
                'message': match_message,
                'next_message': loan_message,
                'data': {
                    'confidence_score': confidence,
                    'match_quality': match_result.get('match_quality', 'fair'),
                    'features_matched': match_result.get('facial_features_matched', []),
                    'customer_segment': age_segment['segment'] if age_segment else None
                },
                'workflow_stage': 'loan_details',
                'requires_upload': False
            })
            
        else:
            # Face match failed - keep temp PAN data for retry
            reason = match_result.get('verification_notes', 'Faces do not match sufficiently')
            
            return JsonResponse({
                'success': True,
                'verified': False,
                'message': f"Face verification failed: {reason}. Confidence: {confidence}%. Please try again with a clearer selfie.",
                'data': {
                    'confidence_score': confidence,
                    'recommendation': match_result.get('recommendation', 'retry')
                },
                'retry': True,
                'workflow_stage': session.stage
            })
            
    except Exception as e:
        # On error, clear temp data
        session.temp_pan_image_data = None
        session.save()
        
        return JsonResponse({
            'success': False,
            'message': f'Face verification error: {str(e)}',
            'error_details': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_chat(request):
    """Initialize a new chat session"""
    # Create session
    session = ChatSession.objects.create(
        stage='greeting'
    )
    
    master_agent = MasterAgent()
    greeting = master_agent.greet_user(session)
    
    # Initialize conversation with greeting
    add_message(session, 'assistant', greeting, 'master')
    session.save()
    
    return JsonResponse({
        'session_id': str(session.id),
        'message': greeting,
        'agent': 'master',
        'workflow_stage': 'greeting'
    })


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """Handle chat messages and workflow progression"""
    data = json.loads(request.body)
    session_id = data.get('session_id')
    user_message = data.get('message')
    
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Invalid session'}, status=400)
    
    # Get current workflow stage
    workflow_stage = session.stage
    
    # Add user message to history
    conversation = add_message(session, 'user', user_message)
    
    # Initialize agents
    master_agent = MasterAgent()
    sales_agent = SalesAgent()
    verification_agent = VerificationAgent()
    underwriting_agent = UnderwritingAgent()
    
    # Get age segment if customer exists
    age_segment = get_age_segment(session)
    
    sanction_letter_url = None
    requires_upload = False
    upload_type = None
    current_agent = 'master'
    
    # Process based on workflow stage
    if workflow_stage == 'greeting' or workflow_stage == 'name_collection':
        # Extract name and DOB from conversation
        extracted_data = master_agent.extract_name_and_dob(conversation)
        
        if extracted_data:
            name = extracted_data.get('name')
            date_of_birth = extracted_data.get('date_of_birth')
            
            # Check if we have name
            if name and name != 'NOT_FOUND':
                # Store customer name temporarily
                session.customer_name = name
                
                # Check if DOB is also provided
                if date_of_birth and date_of_birth != 'NOT_FOUND':
                    # Store DOB temporarily
                    session.temp_dob = date_of_birth
                    
                    # Calculate age and determine segment
                    age = CustomerSegmentation.get_age_from_dob(date_of_birth)
                    if age:
                        temp_segment = CustomerSegmentation.determine_segment(age)
                        age_segment = temp_segment
                
                # Search for existing customer by name
                customers = Customer.objects.filter(name__icontains=name)
                
                if customers.exists():
                    # Existing customer found - request PAN number for verification
                    customer = customers.first()
                    
                    # If customer has DOB, calculate their segment
                    if customer.date_of_birth:
                        age_segment = get_age_segment(session)
                    
                    session.stage = 'pan_collection'
                    workflow_stage = 'pan_collection'
                    response = master_agent.request_pan_number(customer.name, age_segment)
                else:
                    # New customer - request PAN number
                    session.stage = 'pan_collection'
                    workflow_stage = 'pan_collection'
                    response = master_agent.request_new_customer_pan(age_segment)
            else:
                # Couldn't extract name, ask again
                response = "I didn't catch your name and date of birth. Could you please provide your full name and date of birth (DD/MM/YYYY or YYYY-MM-DD)?"
                session.stage = 'name_collection'
                workflow_stage = 'name_collection'
        else:
            # No data extracted
            response = "I didn't catch your name and date of birth. Could you please provide your full name and date of birth?"
            session.stage = 'name_collection'
            workflow_stage = 'name_collection'
    
    elif workflow_stage == 'pan_collection':
        # Extract PAN number from conversation
        pan_number = master_agent.extract_pan_number(conversation)
        
        if pan_number and pan_number != 'NOT_FOUND':
            # PAN number extracted successfully
            # Check if customer exists with this PAN
            try:
                customer = Customer.objects.get(pan=pan_number)
                # Existing customer with matching PAN
                session.customer = customer
                
                # Get age segment for existing customer
                age_segment = get_age_segment(session)
                
                session.stage = 'pan_verification'
                workflow_stage = 'pan_verification'
                response = master_agent.request_pan_upload(customer.name, age_segment)
                requires_upload = True
                upload_type = 'pan_card'
            except Customer.DoesNotExist:
                # New customer - store PAN temporarily and request upload
                session.stage = 'pan_verification'
                workflow_stage = 'pan_verification'
                response = (
                    f"Thank you! Now please upload a clear photo of your PAN card "
                    f"({pan_number}) for verification. This helps us ensure secure processing."
                )
                requires_upload = True
                upload_type = 'pan_card'
        else:
            # Couldn't extract valid PAN, ask again
            response = (
                "I couldn't find a valid PAN number in your message. "
                "Please provide your PAN number in the format: ABCDE1234F "
                "(5 letters, 4 digits, 1 letter)"
            )
    
    elif workflow_stage == 'pan_verification':
        # User is in PAN verification stage - remind them to upload
        response = "Please use the upload button above to submit your PAN card image for verification."
        requires_upload = True
        upload_type = 'pan_card'
    
    elif workflow_stage == 'selfie_verification':
        # User is in selfie verification stage - remind them to upload
        response = "Please use the upload button above to take and submit a live selfie for face verification."
        requires_upload = True
        upload_type = 'selfie'
    
    elif workflow_stage == 'loan_details':
        # Collect loan requirements with age-aware extraction
        current_agent = 'sales'
        loan_details = sales_agent.extract_loan_details(conversation, age_segment)
        
        if loan_details and all([
            loan_details.get('loan_amount'),
            loan_details.get('purpose'),
            loan_details.get('tenure_months')
        ]):
            # All loan details collected
            if not session.customer:
                # Should not happen, but handle gracefully
                response = "Please complete PAN verification first."
                session.stage = 'pan_verification'
                workflow_stage = 'pan_verification'
                requires_upload = True
                upload_type = 'pan_card'
            else:
                # Update customer with additional details
                if loan_details.get('employment_type'):
                    session.customer.employment_type = loan_details['employment_type']
                if loan_details.get('monthly_income'):
                    session.customer.monthly_income = loan_details['monthly_income']
                session.customer.save()
                
                # Refresh age segment with updated data
                age_segment = get_age_segment(session)
                
                # Create loan application
                loan_app = LoanApplication.objects.create(
                    customer=session.customer,
                    loan_amount=loan_details['loan_amount'],
                    purpose=loan_details['purpose'],
                    tenure_months=loan_details['tenure_months'],
                    status='under_review'
                )
                
                session.stage = 'salary_verification'
                workflow_stage = 'salary_verification'
                current_agent = 'underwriting'
                
                # Assess loan with age-aware underwriting
                assessment = underwriting_agent.assess_loan(
                    session.customer,
                    loan_details['loan_amount'],
                    loan_details['tenure_months'],
                    age_segment
                )
                
                if assessment['approved'] == True:
                    # Loan approved
                    loan_app.status = 'approved'
                    loan_app.save()
                    
                    # Generate sanction letter with segment info
                    try:
                        sanction_letter = SanctionLetterGenerator.generate_letter(loan_app, age_segment)
                        loan_app.sanction_letter.save(
                            f'sanction_{loan_app.id}.pdf', 
                            sanction_letter, 
                            save=True
                        )
                        
                        segment_note = f" {assessment.get('segment_note', '')}" if assessment.get('segment_note') else ""
                        response = (
                            f"🎉 Congratulations! Your loan of ₹{loan_details['loan_amount']:,.2f} "
                            f"has been approved! {assessment['reason']}.{segment_note} "
                            f"Your sanction letter is ready for download."
                        )
                    except Exception as e:
                        response = (
                            f"🎉 Congratulations! Your loan of ₹{loan_details['loan_amount']:,.2f} "
                            f"has been approved! {assessment['reason']}. "
                            f"(Note: Sanction letter generation encountered an issue: {str(e)})"
                        )
                    
                    session.stage = 'completed'
                    workflow_stage = 'completed'
                    
                elif assessment['approved'] == 'pending_salary_slip':
                    # Requires salary slip verification
                    response = (
                        f"Your loan requires additional verification. {assessment['reason']}. "
                        f"Please upload your latest salary slip to proceed."
                    )
                    requires_upload = True
                    upload_type = 'salary_slip'
                
                elif assessment['approved'] == 'pending_business_docs':
                    # Requires business documents (for self-employed)
                    docs_needed = ', '.join(assessment.get('documents_needed', []))
                    response = (
                        f"As a self-employed professional, we need additional documentation. "
                        f"{assessment['reason']}. Please prepare: {docs_needed}. "
                        f"You can upload your salary slip for now, and we'll guide you through the rest."
                    )
                    requires_upload = True
                    upload_type = 'salary_slip'
                
                elif assessment['approved'] == 'pending_guarantor':
                    # Requires guarantor (for new-to-credit)
                    response = (
                        f"{assessment['reason']}. This is standard for first-time borrowers. "
                        f"For now, please upload your salary slip, and we'll discuss guarantor details."
                    )
                    requires_upload = True
                    upload_type = 'salary_slip'
                    
                else:
                    # Loan rejected
                    loan_app.status = 'rejected'
                    loan_app.rejection_reason = assessment['reason']
                    loan_app.save()
                    response = (
                        f"I'm sorry, but your loan application cannot be approved at this time. "
                        f"Reason: {assessment['reason']}"
                    )
                    session.stage = 'rejected'
                    workflow_stage = 'rejected'
        else:
            # Continue collecting loan details with age-aware engagement
            response = sales_agent.engage_customer(session, conversation, age_segment)
    
    elif workflow_stage == 'salary_verification':
        # Waiting for salary slip upload
        response = "Please upload your salary slip using the upload button above."
        requires_upload = True
        upload_type = 'salary_slip'
        current_agent = 'underwriting'
    
    elif workflow_stage == 'completed' or workflow_stage == 'rejected':
        response = master_agent.thank_and_close(session)
    
    else:
        # Unknown stage - reset to greeting
        response = "Something went wrong. Let's start over. What's your name and date of birth?"
        session.stage = 'greeting'
        workflow_stage = 'greeting'
    
    # Add assistant response to history
    add_message(session, 'assistant', response, current_agent)
    session.save()
    
    # Prepare response
    response_data = {
        'message': response,
        'agent': current_agent,
        'workflow_stage': workflow_stage,
        'session_id': str(session.id),
        'requires_upload': requires_upload
    }
    
    if upload_type:
        response_data['upload_type'] = upload_type
    
    if sanction_letter_url:
        response_data['loan_id'] = loan_app.id
    
    if age_segment:
        response_data['customer_segment'] = {
            'segment': age_segment['segment'],
            'age_group': age_segment['age_group']
        }
    
    return JsonResponse(response_data)


import base64

@csrf_exempt
@require_http_methods(["POST"])
def upload_pan_card(request):
    """Handle PAN card image upload and AI-powered verification"""
    session_id = request.POST.get('session_id')
    pan_image = request.FILES.get('pan_card_image')
    
    if not pan_image:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a PAN card image'
        }, status=400)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if pan_image.content_type not in allowed_types:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a valid image file (JPEG, PNG, or WebP)'
        }, status=400)
    
    # Validate file size (max 5MB)
    if pan_image.size > 5 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'Image size should be less than 5MB'
        }, status=400)
    
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid session. Please refresh and try again.'
        }, status=404)
    
    # Get expected name from session
    expected_name = session.customer_name
    if not expected_name:
        return JsonResponse({
            'success': False,
            'message': 'Customer name not found. Please restart the process.'
        }, status=400)
    
    # Try to extract PAN from conversation
    conversation = get_conversation(session)
    master_agent = MasterAgent()
    expected_pan = master_agent.extract_pan_number(conversation)
    if expected_pan == 'NOT_FOUND':
        expected_pan = None
    
    try:
        # Initialize PAN verification agent
        pan_agent = PANVerificationAgent()
        
        # Read image data directly (no file storage needed)
        pan_image.seek(0)
        pan_image_data = pan_image.read()
        
        # ✅ Store PAN image as base64 in session for later face matching
        pan_base64 = base64.b64encode(pan_image_data).decode('utf-8')
        session.temp_pan_image_data = pan_base64
        
        # Verify PAN card using AI
        verification_result = pan_agent.verify_pan_card(
            pan_image_data,  # Pass bytes directly
            expected_name,
            expected_pan
        )
        
        # Generate human-readable report
        verification_message = pan_agent.generate_verification_report(verification_result)
        
        # Check if verification was successful
        if verification_result.get('is_valid_pan_card'):
            # Additional check for PAN match if expected
            if expected_pan and not verification_result.get('pan_match', True):
                return JsonResponse({
                    'success': True,
                    'verified': False,
                    'message': f"PAN number mismatch. The PAN on your card doesn't match the one you provided ({expected_pan}). Please check and try again.",
                    'retry': True,
                    'workflow_stage': session.stage
                })
            
            # Check name match
            if not verification_result.get('name_match', {}).get('matches'):
                name_match_reason = verification_result.get('name_match', {}).get('reason', 'Names do not match')
                return JsonResponse({
                    'success': True,
                    'verified': False,
                    'message': f"Name verification failed: {name_match_reason}. Please ensure the PAN card belongs to you.",
                    'retry': True,
                    'workflow_stage': session.stage
                })
            
            # Verification successful
            pan_number = verification_result.get('pan_number')
            name_on_card = verification_result.get('name_on_card')
            dob_from_pan = verification_result.get('date_of_birth')
            
            # Search for existing customer by PAN
            try:
                customer = Customer.objects.get(pan=pan_number)
                is_existing = True
                
                # Update customer verification status
                customer.pan_verified = True
                customer.pan_verification_confidence = verification_result.get('confidence_score')
                
                # Update DOB if found on PAN and not already set
                if dob_from_pan and not customer.date_of_birth:
                    try:
                        from datetime import datetime
                        customer.date_of_birth = datetime.strptime(dob_from_pan, "%d/%m/%Y").date()
                    except:
                        try:
                            customer.date_of_birth = datetime.strptime(dob_from_pan, "%Y-%m-%d").date()
                        except:
                            pass
                
            except Customer.DoesNotExist:
                # New customer - create record
                dob_obj = None
                
                # Try to get DOB from temp storage or PAN extraction
                temp_dob = getattr(session, 'temp_dob', None)
                if temp_dob:
                    try:
                        from datetime import datetime
                        dob_obj = datetime.strptime(temp_dob, "%Y-%m-%d").date()
                    except:
                        try:
                            dob_obj = datetime.strptime(temp_dob, "%d/%m/%Y").date()
                        except:
                            pass
                
                # If not in temp storage, try from PAN
                if not dob_obj and dob_from_pan:
                    try:
                        from datetime import datetime
                        dob_obj = datetime.strptime(dob_from_pan, "%d/%m/%Y").date()
                    except:
                        try:
                            dob_obj = datetime.strptime(dob_from_pan, "%Y-%m-%d").date()
                        except:
                            pass
                
                customer = Customer.objects.create(
                    name=name_on_card,
                    pan=pan_number,
                    date_of_birth=dob_obj,
                    pan_verified=True,
                    pan_verification_confidence=verification_result.get('confidence_score'),
                    credit_score=750,  # Default, should fetch from credit bureau
                    pre_approved_limit=100000  # Default limit
                )
                is_existing = False
            
            # ✅ NO FILE STORAGE - Just save verification metadata
            customer.save()
            
            # Update session
            session.customer = customer
            session.stage = 'selfie_verification'
            session.save()  # Save session with temp_pan_image_data
            
            # Get age segment now that we have customer with DOB
            age_segment = get_age_segment(session)
            
            # Add verification message to conversation
            conversation = add_message(session, 'assistant', verification_message, 'verification')
            
            # Request selfie upload with age-aware messaging
            if age_segment:
                if age_segment['segment'] == 'Young Salaried Professional':
                    selfie_message = (
                        "Excellent! Your PAN card has been verified successfully. "
                        "For final verification, please take a quick selfie using the upload button. "
                        "Super fast and secure - just like you prefer! 📸"
                    )
                elif age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                    selfie_message = (
                        "Great! Your PAN card has been verified successfully. "
                        "For final verification, please take a selfie using the upload button. "
                        "Don't worry, this is simple and helps us keep your account secure. 😊"
                    )
                else:
                    selfie_message = (
                        "Great! Your PAN card has been verified successfully. "
                        "For final verification, please take a live selfie using the upload button. "
                        "This helps us ensure the security of your account."
                    )
            else:
                selfie_message = (
                    "Great! Your PAN card has been verified successfully. "
                    "For final verification, please take a live selfie using the upload button. "
                    "This helps us ensure the security of your account."
                )
            
            add_message(session, 'assistant', selfie_message, 'verification')
            
            return JsonResponse({
                'success': True,
                'verified': True,
                'message': verification_message,
                'next_message': selfie_message,
                'data': {
                    'pan_number': pan_number,
                    'name': name_on_card,
                    'confidence_score': verification_result.get('confidence_score'),
                    'is_existing_customer': is_existing,
                    'customer_segment': age_segment['segment'] if age_segment else None,
                    'age_group': age_segment['age_group'] if age_segment else None
                },
                'workflow_stage': 'selfie_verification',
                'requires_upload': True,
                'upload_type': 'selfie'
            })
            
        else:
            # Verification failed - clear temp data
            session.temp_pan_image_data = None
            session.save()
            
            reasons = []
            if not verification_result.get('is_valid_pan_card'):
                reasons.append(
                    verification_result.get('verification_notes', 'Invalid PAN card detected')
                )
            
            return JsonResponse({
                'success': True,
                'verified': False,
                'message': verification_message,
                'reasons': reasons,
                'retry': True,
                'workflow_stage': session.stage
            })
            
    except Exception as e:
        # Clear temp data on error
        session.temp_pan_image_data = None
        session.save()
        
        return JsonResponse({
            'success': False,
            'message': f'Verification error: {str(e)}',
            'error_details': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_salary_slip(request):
    """Handle salary slip upload for loan verification"""
    session_id = request.POST.get('session_id')
    salary_slip = request.FILES.get('salary_slip')
    
    if not salary_slip:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a salary slip'
        }, status=400)
    
    # Validate file type
    allowed_types = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
        'application/pdf'
    ]
    if salary_slip.content_type not in allowed_types:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a valid file (JPEG, PNG, WebP, or PDF)'
        }, status=400)
    
    # Validate file size (max 10MB for salary slips)
    if salary_slip.size > 10 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'File size should be less than 10MB'
        }, status=400)
    
    try:
        session = ChatSession.objects.get(id=session_id)
        
        if not session.customer:
            return JsonResponse({
                'success': False,
                'message': 'No customer found'
            }, status=400)
        
        # Get age segment
        age_segment = get_age_segment(session)
        
        # Get the most recent loan application for this customer
        loan_app = LoanApplication.objects.filter(
            customer=session.customer
        ).order_by('-applied_at').first()
        
        if not loan_app:
            return JsonResponse({
                'success': False,
                'message': 'No loan application found'
            }, status=400)
        
        # Read and encode file content to base64 for storage in database
        file_content = salary_slip.read()
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        
        # Store in memory (database fields)
        loan_app.salary_slip_name = salary_slip.name
        loan_app.salary_slip_content = encoded_content
        loan_app.salary_slip_content_type = salary_slip.content_type
        loan_app.salary_slip_size = salary_slip.size
        
        # TODO: Add AI-powered salary slip verification here
        # For now, assume verification passes and approve loan
        
        loan_app.status = 'approved'
        loan_app.save()
        
        # Generate sanction letter with segment info
        try:
            sanction_letter = SanctionLetterGenerator.generate_letter(loan_app, age_segment)
            
            # Store sanction letter in memory as well
            sanction_letter_content = sanction_letter.read()
            encoded_sanction = base64.b64encode(sanction_letter_content).decode('utf-8')
            
            loan_app.sanction_letter_name = f'sanction_{loan_app.id}.pdf'
            loan_app.sanction_letter_content = encoded_sanction
            loan_app.sanction_letter_content_type = 'application/pdf'
            loan_app.save()
            
            # Age-aware approval message
            if age_segment:
                if age_segment['segment'] == 'Young Salaried Professional':
                    message = (
                        f"🎉 Awesome! After verifying your salary slip, "
                        f"your loan of ₹{loan_app.loan_amount:,.2f} has been approved! "
                        f"Fast-tracked just for you. Your sanction letter is ready for download. 📄"
                    )
                elif age_segment['segment'] == 'Existing Kite Capital Customer':
                    message = (
                        f"🎉 Welcome back! Your loan of ₹{loan_app.loan_amount:,.2f} "
                        f"has been approved with our fastest process! "
                        f"Your sanction letter is ready for download. 📄"
                    )
                else:
                    message = (
                        f"🎉 Congratulations! After verifying your salary slip, "
                        f"your loan of ₹{loan_app.loan_amount:,.2f} has been approved! "
                        f"Your sanction letter is ready for download."
                    )
            else:
                message = (
                    f"🎉 Congratulations! After verifying your salary slip, "
                    f"your loan of ₹{loan_app.loan_amount:,.2f} has been approved! "
                    f"Your sanction letter is ready for download."
                )
            
            # Update session
            session.stage = 'completed'
            add_message(session, 'assistant', message, 'underwriting')
            session.save()
            
            return JsonResponse({
                'success': True,
                'message': message,
                'loan_id': loan_app.id,
                'workflow_stage': 'completed',
                'requires_upload': False,
                'customer_segment': age_segment['segment'] if age_segment else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error generating sanction letter: {str(e)}'
            }, status=500)
            
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid session'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }, status=500)

# Add to your views.py
@csrf_exempt
def set_language(request):
    data = json.loads(request.body)
    session_id = data.get('session_id')
    language = data.get('language', 'en')
    
    # Store language in session
    session = ChatSession.objects.get(id=session_id)
    session.language = language
    session.save()
    
    # Update all agents
    for agent in [MasterAgent, VerificationAgent, SalesAgent]:
        agent.set_language(language)
    
    return JsonResponse({'success': True})

@csrf_exempt
def download_sanction_letter(request, loan_id):
    try:
        # Get loan application
        loan_application = get_object_or_404(LoanApplication, id=loan_id)
        
        # Generate PDF
        pdf_file = SanctionLetterGenerator.generate_letter(loan_application)
        
        # Return as downloadable response
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Sanction_Letter_LA{loan_id:06d}.pdf"'
        
        return response
        
    except LoanApplication.DoesNotExist:
        raise Http404("Loan application not found")
    except Exception as e:
        print(f"Error generating sanction letter: {str(e)}")
        return HttpResponse("Error generating sanction letter", status=500)