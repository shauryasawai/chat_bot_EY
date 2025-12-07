from openai import OpenAI
import json
from django.conf import settings
from decimal import Decimal
import re
import base64

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class BaseAgent:
    def __init__(self, name, role):
        self.name = name
        self.role = role
    
    def call_openai(self, messages, temperature=0.7):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",  # or gpt-4.1, gpt-3.5-turbo style model
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error: {str(e)}"

class MasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Master Agent", "Orchestrator")
    
    def greet_user(self, session):
        messages = [
            {"role": "system", "content": """You are a Master Agent for a loan processing system. 
            Greet the user warmly and ask for their full name to check their customer status.
            Keep it brief and professional."""},
            {"role": "user", "content": "Start the conversation"}
        ]
        return self.call_openai(messages)
    
    def extract_name(self, conversation_history):
        messages = [
            {"role": "system", "content": """Extract the full name from the conversation.
            Return ONLY the name as plain text, nothing else.
            If no clear name is found, return 'NOT_FOUND'."""}
        ]
        
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        messages.append({"role": "user", "content": conversation_text})
        
        response = self.call_openai(messages, temperature=0.3)
        return response.strip()
    
    def extract_pan_number(self, conversation_history):
        """Extract PAN number from conversation"""
        messages = [
            {"role": "system", "content": """Extract the PAN number from the conversation.
            PAN format is: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
            Return ONLY the PAN number in uppercase, nothing else.
            If no valid PAN is found, return 'NOT_FOUND'."""}
        ]
        
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        messages.append({"role": "user", "content": conversation_text})
        
        response = self.call_openai(messages, temperature=0.3)
        pan = response.strip().upper()
        
        # Validate PAN format
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
            return pan
        return 'NOT_FOUND'
    
    def request_pan_number(self, customer_name):
        """Ask for PAN number from existing customer"""
        messages = [
            {"role": "system", "content": f"""You are a Master Agent. 
            Tell the customer '{customer_name}' that we found their record.
            Ask them to provide their PAN number for verification.
            Mention the PAN format (e.g., ABCDE1234F).
            Keep it professional and reassuring."""},
            {"role": "user", "content": "Request PAN number"}
        ]
        return self.call_openai(messages)
    
    def request_pan_upload(self, customer_name):
        """Request PAN card image upload after PAN number verification"""
        messages = [
            {"role": "system", "content": f"""You are a Master Agent. 
            Tell the customer '{customer_name}' that their PAN number has been verified.
            Now ask them to upload a clear photo or scan of their PAN card for KYC verification.
            Mention that this is for their security and identity verification.
            Keep it professional and reassuring."""},
            {"role": "user", "content": "Request PAN card upload"}
        ]
        return self.call_openai(messages)
    
    def request_new_customer_pan(self):
        """Ask new customer for their PAN number"""
        messages = [
            {"role": "system", "content": """You are a Master Agent.
            The user is a new customer. Ask them to provide their PAN number.
            Explain that PAN is mandatory for loan processing.
            Mention the format (e.g., ABCDE1234F - 5 letters, 4 digits, 1 letter).
            Keep it welcoming and professional."""},
            {"role": "user", "content": "Request PAN from new customer"}
        ]
        return self.call_openai(messages)
    
    def inform_new_customer(self):
        messages = [
            {"role": "system", "content": """You are a Master Agent.
            Politely inform the user that they are a new customer and we'll need to collect their details.
            Keep it welcoming and professional."""},
            {"role": "user", "content": "Inform new customer"}
        ]
        return self.call_openai(messages)
    
    def thank_and_close(self, session):
        messages = [
            {"role": "system", "content": """You are a Master Agent. 
            Thank the customer for their time and close the conversation professionally."""},
            {"role": "user", "content": "Close the conversation"}
        ]
        return self.call_openai(messages)


class FaceMatchAgent(BaseAgent):
    """Agent for face matching between selfie and PAN card"""
    
    def __init__(self):
        super().__init__("Face Match Agent", "Biometric Validator")
    
    def encode_image(self, image_file):
        """Convert uploaded image to base64"""
        try:
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
                image_file.seek(0)
            else:
                image_data = image_file
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            return base64_image
        except Exception as e:
            raise Exception(f"Error encoding image: {str(e)}")
    
    def match_faces(self, selfie_image, pan_card_image):
        """
        Compare selfie with PAN card photo using AI vision
        Returns: dict with match result and confidence score
        """
        try:
            selfie_base64 = self.encode_image(selfie_image)
            pan_base64 = self.encode_image(pan_card_image)
            
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert biometric verification agent specializing in face matching.
                    Compare the two images provided:
                    1. First image: Customer's live selfie
                    2. Second image: PAN card photo
                    
                    Analyze and determine:
                    - Do both images show the same person?
                    - What is the confidence level of the match?
                    - Consider factors like age difference, image quality, angles
                    - Be lenient - even 20-30% similarity should pass if facial features match
                    
                    Return your response as a JSON object:
                    {
                        "faces_match": true/false,
                        "confidence_score": 0-100,
                        "match_quality": "excellent/good/fair/poor",
                        "facial_features_matched": ["eyes", "nose", "face_shape", etc.],
                        "verification_notes": "detailed observations",
                        "recommendation": "approve/reject/manual_review"
                    }
                    
                    Note: If confidence is 20% or above and key facial features match, set faces_match to true."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Compare these two images. First is the live selfie, second is the PAN card photo. Do they show the same person?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{selfie_base64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{pan_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            response = self.call_openai(messages, temperature=0.2)
            
            # Parse JSON response
            result = self._parse_match_response(response)
            return result
            
        except Exception as e:
            return {
                'faces_match': False,
                'confidence_score': 0,
                'error': str(e),
                'verification_notes': 'Error during face matching'
            }
    
    def _parse_match_response(self, response):
        """Parse and clean the JSON response"""
        try:
            cleaned_response = response.strip()
            
            # Remove markdown code blocks
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            return json.loads(cleaned_response.strip())
        except json.JSONDecodeError:
            return {
                'faces_match': False,
                'confidence_score': 0,
                'verification_notes': 'Failed to parse face match response',
                'raw_response': response
            }
    
    def generate_match_report(self, match_result):
        """Generate human-readable face match report"""
        messages = [
            {
                "role": "system",
                "content": """You are a biometric verification officer. Generate a brief, 
                professional message about the face matching result. Be clear and reassuring."""
            },
            {
                "role": "user",
                "content": f"Generate verification message for: {json.dumps(match_result)}"
            }
        ]
        
        return self.call_openai(messages, temperature=0.5)


class PANVerificationAgent(BaseAgent):
    """Agent for PAN card image verification"""
    
    def __init__(self):
        super().__init__("PAN Verification Agent", "Document Validator")
    
    def encode_image(self, image_file):
        """Convert uploaded image to base64"""
        try:
            # If it's a Django UploadedFile
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
                image_file.seek(0)  # Reset file pointer
            else:
                image_data = image_file
            
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            return base64_image
        except Exception as e:
            raise Exception(f"Error encoding image: {str(e)}")
    
    def verify_pan_card(self, image_file, expected_name, expected_pan=None):
        """
        Verify PAN card using OpenAI Vision API
        Returns: dict with verification status, extracted details, and confidence score
        """
        try:
            base64_image = self.encode_image(image_file)
            
            verification_instructions = f"""You are an expert document verification agent specializing in Indian PAN cards.
                    Analyze the uploaded image and extract the following information:
                    1. PAN Number (format: 5 letters, 4 digits, 1 letter - e.g., ABCDE1234F)
                    2. Name on PAN card
                    3. Father's Name (if visible)
                    4. Date of Birth (if visible)
                    
                    Also verify:
                    - Is this a genuine PAN card?
                    - Is the image clear and readable?
                    - Are there any signs of tampering?
                    
                    Expected details:
                    - Customer Name: {expected_name}"""
            
            if expected_pan:
                verification_instructions += f"\n- PAN Number: {expected_pan}"
            
            verification_instructions += """
                    
                    Return your response as a JSON object with the following structure:
                    {
                        "is_valid_pan_card": true/false,
                        "pan_number": "extracted PAN",
                        "name_on_card": "extracted name",
                        "fathers_name": "extracted father's name or null",
                        "date_of_birth": "extracted DOB or null",
                        "image_quality": "good/poor/unclear",
                        "tampering_detected": true/false,
                        "confidence_score": 0-100,
                        "verification_notes": "any observations"
                    }
                    
                    Be strict in verification. If anything seems suspicious, set is_valid_pan_card to false."""
            
            messages = [
                {
                    "role": "system",
                    "content": verification_instructions
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please verify this PAN card image. Check if the details match the expected information."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            response = self.call_openai(messages, temperature=0.2)
            
            # Parse JSON response
            verification_result = self._parse_verification_response(response)
            
            # Additional verification checks
            if verification_result.get('is_valid_pan_card'):
                # Verify name match
                name_match = self._verify_name_match(
                    expected_name, 
                    verification_result.get('name_on_card', '')
                )
                verification_result['name_match'] = name_match
                
                if not name_match['matches']:
                    verification_result['is_valid_pan_card'] = False
                    verification_result['verification_notes'] += f" | Name mismatch: {name_match['reason']}"
                
                # Verify PAN number if provided
                if expected_pan:
                    extracted_pan = verification_result.get('pan_number', '')
                    if extracted_pan.upper() != expected_pan.upper():
                        verification_result['is_valid_pan_card'] = False
                        verification_result['pan_match'] = False
                        verification_result['verification_notes'] += f" | PAN number mismatch"
                    else:
                        verification_result['pan_match'] = True
            
            return verification_result
            
        except Exception as e:
            return {
                'is_valid_pan_card': False,
                'error': str(e),
                'verification_notes': 'Error during verification process'
            }
    
    def _parse_verification_response(self, response):
        """Parse and clean the JSON response from OpenAI"""
        try:
            cleaned_response = response.strip()
            
            # Remove markdown code blocks if present
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            return json.loads(cleaned_response.strip())
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract key information
            return {
                'is_valid_pan_card': False,
                'verification_notes': 'Failed to parse verification response',
                'raw_response': response
            }
    
    def _verify_name_match(self, provided_name, extracted_name):
        """
        Verify if the provided name matches the extracted name
        Uses fuzzy matching to account for minor variations
        """
        # Normalize names
        provided_clean = re.sub(r'[^a-zA-Z\s]', '', provided_name.upper()).strip()
        extracted_clean = re.sub(r'[^a-zA-Z\s]', '', extracted_name.upper()).strip()
        
        # Exact match
        if provided_clean == extracted_clean:
            return {'matches': True, 'confidence': 100, 'reason': 'Exact match'}
        
        # Check if all words in provided name are in extracted name
        provided_words = set(provided_clean.split())
        extracted_words = set(extracted_clean.split())
        
        # Calculate word overlap
        common_words = provided_words.intersection(extracted_words)
        
        if len(common_words) >= len(provided_words) * 0.8:  # 80% words match
            return {
                'matches': True, 
                'confidence': 85,
                'reason': 'Substantial word match'
            }
        
        # Use OpenAI for semantic name matching
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a name matching expert. Compare two names and determine if they refer to the same person.
                    Consider variations like:
                    - Middle names present/absent
                    - Initials vs full names
                    - Common nicknames
                    - Spelling variations
                    
                    Return JSON: {"matches": true/false, "confidence": 0-100, "reason": "explanation"}"""
                },
                {
                    "role": "user",
                    "content": f"Provided name: '{provided_name}'\nPAN card name: '{extracted_name}'\n\nDo these names match?"
                }
            ]
            
            response = self.call_openai(messages, temperature=0.2)
            result = json.loads(response.strip().replace('```json', '').replace('```', '').strip())
            return result
            
        except:
            return {
                'matches': False,
                'confidence': 0,
                'reason': 'Names do not match and verification failed'
            }
    
    def generate_verification_report(self, verification_result):
        """Generate a human-readable verification report"""
        messages = [
            {
                "role": "system",
                "content": """You are a KYC officer. Generate a brief, professional message 
                about the PAN card verification result. Be clear about whether verification 
                passed or failed and mention key reasons."""
            },
            {
                "role": "user",
                "content": f"Generate verification message for this result: {json.dumps(verification_result)}"
            }
        ]
        
        return self.call_openai(messages, temperature=0.5)


class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__("Sales Agent", "Lead Qualification")
    
    def engage_customer(self, session, conversation_history):
        messages = [
            {"role": "system", "content": """You are a Sales Agent for personal loans.
            Ask the customer about:
            1. Loan amount needed
            2. Purpose of the loan
            3. Preferred tenure (in months)
            
            Be conversational and helpful. Extract this information naturally."""}
        ]
        
        for msg in conversation_history:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        return self.call_openai(messages)
    
    def extract_loan_details(self, conversation_history):
        messages = [
            {"role": "system", "content": """Extract loan details from the conversation.
            Return ONLY a JSON object with: loan_amount (number), purpose (string), tenure_months (number).
            If any information is missing, return null for that field."""}
        ]
        
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        messages.append({"role": "user", "content": conversation_text})
        
        response = self.call_openai(messages, temperature=0.3)
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            return json.loads(cleaned_response.strip())
        except:
            return None


class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Verification Agent", "KYC Validator")
    
    def request_kyc_details(self, session):
        messages = [
            {"role": "system", "content": """You are a Verification Agent.
            Ask the customer to upload their Aadhar card image and provide their phone number.
            Explain this is for identity verification and their data security is our priority.
            Be professional and reassuring."""},
            {"role": "user", "content": "Request remaining KYC documents"}
        ]
        return self.call_openai(messages)
    
    def validate_kyc(self, customer_data):
        """Validate KYC details after document verification"""
        if (customer_data.get('pan_verified', False) and 
            len(customer_data.get('phone', '')) >= 10):
            return True, "KYC validated successfully"
        return False, "Invalid or incomplete KYC details"


class UnderwritingAgent(BaseAgent):
    def __init__(self):
        super().__init__("Underwriting Agent", "Credit Assessment")
    
    def assess_loan(self, customer, loan_amount, tenure):
        loan_amount = Decimal(str(loan_amount))
        credit_score = customer.credit_score
        pre_approved_limit = customer.pre_approved_limit
        
        # Rule 1: Credit score check
        if credit_score < 700:
            return {
                'approved': False,
                'reason': 'Credit score below minimum threshold of 700'
            }
        
        # Rule 2: Instant approval if within pre-approved limit
        if loan_amount <= pre_approved_limit:
            return {
                'approved': True,
                'instant': True,
                'reason': 'Within pre-approved limit'
            }
        
        # Rule 3: Request salary slip if ≤ 2× pre-approved limit
        if loan_amount <= (pre_approved_limit * 2):
            return {
                'approved': 'pending_salary_slip',
                'reason': 'Requires salary slip verification'
            }
        
        # Rule 4: Reject if > 2× pre-approved limit
        return {
            'approved': False,
            'reason': 'Loan amount exceeds 2× pre-approved limit'
        }
    
    def validate_salary_emi(self, salary, loan_amount, tenure_months):
        monthly_emi = Decimal(str(loan_amount)) / tenure_months
        salary_decimal = Decimal(str(salary))
        
        if monthly_emi <= (salary_decimal * Decimal('0.50')):
            return True, "EMI within 50% of salary"
        return False, "EMI exceeds 50% of monthly salary"


class SanctionLetterGenerator:
    @staticmethod
    def generate_letter(loan_application):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            import io
            from django.core.files.base import ContentFile
            from datetime import datetime
            
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Header with background
            p.setFillColorRGB(0.2, 0.3, 0.6)
            p.rect(0, height - 100, width, 100, fill=1)
            
            # Title
            p.setFillColorRGB(1, 1, 1)
            p.setFont("Helvetica-Bold", 24)
            p.drawCentredString(width/2, height - 60, "LOAN SANCTION LETTER")
            
            # Company name
            p.setFont("Helvetica", 12)
            p.drawCentredString(width/2, height - 85, "Multi-Agent Loan Processing System")
            
            # Reset to black for content
            p.setFillColorRGB(0, 0, 0)
            
            # Date
            p.setFont("Helvetica", 10)
            current_date = datetime.now().strftime("%B %d, %Y")
            p.drawString(inch, height - 130, f"Date: {current_date}")
            
            # Customer details section
            y = height - 180
            p.setFont("Helvetica-Bold", 14)
            p.drawString(inch, y, "Customer Details:")
            
            y -= 30
            p.setFont("Helvetica", 11)
            p.drawString(inch, y, f"Name: {loan_application.customer.name}")
            y -= 20
            p.drawString(inch, y, f"Application ID: LA-{loan_application.id:06d}")
            y -= 20
            p.drawString(inch, y, f"PAN: {loan_application.customer.pan}")
            y -= 20
            p.setFont("Helvetica-Bold", 10)
            p.setFillColorRGB(0, 0.5, 0)
            p.drawString(inch, y, "✓ KYC Verified with Document Authentication")
            p.setFillColorRGB(0, 0, 0)
            
            # Loan details section
            y -= 40
            p.setFont("Helvetica-Bold", 14)
            p.drawString(inch, y, "Loan Details:")
            
            y -= 30
            p.setFont("Helvetica", 11)
            p.drawString(inch, y, f"Sanctioned Amount: ₹{loan_application.loan_amount:,.2f}")
            y -= 20
            p.drawString(inch, y, f"Tenure: {loan_application.tenure_months} months")
            y -= 20
            p.drawString(inch, y, f"Purpose: {loan_application.purpose}")
            
            # EMI Calculation
            monthly_emi = float(loan_application.loan_amount) / loan_application.tenure_months
            y -= 20
            p.drawString(inch, y, f"Estimated Monthly EMI: ₹{monthly_emi:,.2f}")
            
            # Approval message
            y -= 50
            p.setFont("Helvetica-Bold", 13)
            p.setFillColorRGB(0, 0.5, 0)
            p.drawString(inch, y, "✓ LOAN APPROVED")
            
            # Terms and conditions
            y -= 40
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Helvetica-Bold", 12)
            p.drawString(inch, y, "Terms & Conditions:")
            
            y -= 25
            p.setFont("Helvetica", 9)
            terms = [
                "1. This sanction letter is valid for 30 days from the date of issue.",
                "2. Interest rate will be communicated separately as per prevailing rates.",
                "3. Processing fee and other charges apply as per bank policy.",
                "4. Complete documentation must be submitted within 15 days.",
                "5. The bank reserves the right to cancel this sanction at any time.",
                "6. All documents have been verified using secure AI-powered verification."
            ]
            
            for term in terms:
                p.drawString(inch, y, term)
                y -= 15
            
            # Footer
            y = inch
            p.drawCentredString(width/2, y, "This is a system generated document. No signature required.")
            p.drawCentredString(width/2, y - 12, "For queries, contact: support@loanprocessing.com | Phone: 1800-XXX-XXXX")
            
            # Draw a border
            p.setStrokeColorRGB(0.2, 0.3, 0.6)
            p.setLineWidth(2)
            p.rect(0.5*inch, 0.5*inch, width - inch, height - inch, fill=0)
            
            p.showPage()
            p.save()
            
            buffer.seek(0)
            return ContentFile(buffer.read(), name=f'sanction_letter_{loan_application.id}.pdf')
        
        except Exception as e:
            print(f"Error generating sanction letter: {str(e)}")
            raise