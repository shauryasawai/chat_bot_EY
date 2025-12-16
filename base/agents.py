from openai import OpenAI
import json
from django.conf import settings
from decimal import Decimal
import re
import base64
from datetime import datetime

client = OpenAI(api_key=settings.OPENAI_API_KEY)

from openai import OpenAI
import json
from django.conf import settings
from decimal import Decimal
import re
import base64
from datetime import datetime

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Language translations dictionary
TRANSLATIONS = {
    'en': {
        'greeting': "Hello! Welcome to Tata Capital's loan service. I'll help you with your loan application.",
        'ask_name_dob': "To get started, could you please provide your full name and date of birth (DD/MM/YYYY or YYYY-MM-DD)?",
        'dob_purpose': "Your date of birth helps us verify your age and provide personalized loan options.",
        'found_record': "Great! I found your record in our system.",
        'ask_pan': "For verification, please provide your PAN number (format: ABCDE1234F).",
        'ask_pan_upload': "Thank you! Now please upload a clear photo or scan of your PAN card for KYC verification.",
        'security_note': "This is for your security and identity verification.",
        'new_customer': "You're a new customer. Welcome! We'll collect some details to process your application.",
        'pan_mandatory': "PAN is mandatory for loan processing.",
        'thank_you': "Thank you for your time! Have a great day.",
        'kyc_request': "Please upload your Aadhar card image and provide your phone number.",
        'data_security': "Your data security is our priority.",
        'loan_questions': {
            'amount': "What loan amount do you need?",
            'purpose': "What is the purpose of this loan?",
            'tenure': "What is your preferred loan tenure (in months)?",
            'employment': "What is your employment type?",
            'income': "What is your monthly income?"
        }
    },
    'hi': {
        'greeting': "नमस्ते! टाटा कैपिटल की ऋण सेवा में आपका स्वागत है। मैं आपके ऋण आवेदन में मदद करूंगा।",
        'ask_name_dob': "शुरू करने के लिए, कृपया अपना पूरा नाम और जन्म तिथि (DD/MM/YYYY या YYYY-MM-DD) बताएं?",
        'dob_purpose': "आपकी जन्म तिथि हमें आपकी उम्र सत्यापित करने और व्यक्तिगत ऋण विकल्प प्रदान करने में मदद करती है।",
        'found_record': "बहुत बढ़िया! हमने आपका रिकॉर्ड हमारे सिस्टम में पाया।",
        'ask_pan': "सत्यापन के लिए, कृपया अपना PAN नंबर प्रदान करें (प्रारूप: ABCDE1234F)।",
        'ask_pan_upload': "धन्यवाद! अब कृपया KYC सत्यापन के लिए अपने PAN कार्ड की स्पष्ट फोटो या स्कैन अपलोड करें।",
        'security_note': "यह आपकी सुरक्षा और पहचान सत्यापन के लिए है।",
        'new_customer': "आप एक नए ग्राहक हैं। स्वागत है! हम आपके आवेदन को प्रोसेस करने के लिए कुछ विवरण एकत्र करेंगे।",
        'pan_mandatory': "ऋण प्रोसेसिंग के लिए PAN अनिवार्य है।",
        'thank_you': "आपके समय के लिए धन्यवाद! आपका दिन शुभ हो।",
        'kyc_request': "कृपया अपने आधार कार्ड की छवि अपलोड करें और अपना फोन नंबर प्रदान करें।",
        'data_security': "आपका डेटा सुरक्षा हमारी प्राथमिकता है।",
        'loan_questions': {
            'amount': "आपको कितनी ऋण राशि चाहिए?",
            'purpose': "इस ऋण का उद्देश्य क्या है?",
            'tenure': "आपकी पसंदीदा ऋण अवधि क्या है (महीनों में)?",
            'employment': "आपका रोजगार प्रकार क्या है?",
            'income': "आपकी मासिक आय क्या है?"
        }
    }
}
class CustomerSegmentation:
    """Helper class to determine customer segment based on age and profile"""
    
    @staticmethod
    def get_age_from_dob(date_of_birth):
        """Calculate age from date of birth"""
        if isinstance(date_of_birth, str):
            try:
                dob = datetime.strptime(date_of_birth, "%Y-%m-%d")
            except:
                try:
                    dob = datetime.strptime(date_of_birth, "%d/%m/%Y")
                except:
                    return None
        else:
            dob = date_of_birth
        
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    
    @staticmethod
    def determine_segment(age, employment_type=None, income=None):
        """
        Determine customer segment based on age, employment, and income
        Returns: dict with segment info
        """
        if age is None:
            return {
                'segment': 'Unknown',
                'description': 'Unable to determine segment',
                'questions_focus': []
            }
        
        # Young Salaried Professional (23-30)
        if 23 <= age <= 30:
            return {
                'segment': 'Young Salaried Professional',
                'age_group': '23-30',
                'description': 'Entry to mid-level IT/private sector employee',
                'typical_income': '₹25,000-60,000',
                'needs': ['Funding gadgets', 'travel', 'education', 'emergencies', 'Quick paperless loans'],
                'behaviour': ['Digital-first', 'prefers easy/chatbot', 'Wants quick EMI simulation', 'eligibility clarity'],
                'questions_focus': [
                    'employment_details',
                    'monthly_income',
                    'purpose',
                    'gadget_preference',
                    'digital_transactions'
                ]
            }
        
        # Mid-Career Salaried with Family (30-45)
        elif 30 <= age <= 45:
            return {
                'segment': 'Mid-Career Salaried with Family',
                'age_group': '30-45',
                'description': 'Profile: Middle management class or manufacturing',
                'typical_income': '₹40,000-1,00,000+',
                'needs': ['Higher-ticket loans', "children's education", 'medical needs', 'home renovation', 'weddings', 'debt consolidation'],
                'behaviour': ['More cautious', 'wants clear interest rate', 'clarity on EMI/affordability', 'expect budget impact'],
                'questions_focus': [
                    'family_size',
                    'existing_obligations',
                    'children_education',
                    'home_ownership',
                    'debt_consolidation',
                    'medical_needs'
                ]
            }
        
        # Self-Employed Professional/Small Business Owner (28-50)
        elif 28 <= age <= 50 and employment_type in ['self_employed', 'business_owner', 'freelancer']:
            return {
                'segment': 'Self-Employed Professional/Small Business Owner',
                'age_group': '28-50',
                'description': 'Doctor, CA, freelancer, consultant, trader, shop owner',
                'typical_income': 'Irregular business income',
                'needs': ['Working-capital top-up', 'Business expansion', 'Equipment purchase', 'Personal emergencies'],
                'behaviour': ['Documentation waries', 'ITR/GST/bank statements', 'Flexible terms', 'stable document requirements'],
                'questions_focus': [
                    'business_type',
                    'business_vintage',
                    'turnover',
                    'gst_registration',
                    'itr_filing',
                    'bank_statements',
                    'business_expansion_plans'
                ]
            }
        
        # Low-Income or New-to-Credit Applicant (21-35)
        elif 21 <= age <= 35 and (income is None or income < 30000):
            return {
                'segment': 'Low-Income or New-to-Credit Applicant',
                'age_group': '21-35',
                'description': 'Gig workers, entry-level employee, first-job candidate',
                'typical_income': '₹15,000-30,000',
                'needs': ['Small-ticket loans', 'emergency', 'education', 'first vehicle', 'settling in a new city'],
                'behaviour': ['Thin/no credit history', 'Very sensitive to EMI amount', 'Worried about rejection'],
                'questions_focus': [
                    'first_time_borrower',
                    'employment_stability',
                    'small_loan_amount',
                    'emergency_purpose',
                    'guarantor_availability'
                ]
            }
        
        # Existing Kite Capital Customer (25-55)
        elif 25 <= age <= 55:
            return {
                'segment': 'Existing Kite Capital Customer',
                'age_group': '25-55',
                'description': 'Existing customer with loan history',
                'typical_income': 'Any salaried or self-employed range',
                'needs': ['Quick top-up loan', 'Pre-approved personal loan', 'Minimal documentation'],
                'behaviour': ['Expects ultra-fast flow', 'Wants personalized offers', 'minimal repeating details'],
                'questions_focus': [
                    'previous_loan_experience',
                    'repayment_history',
                    'top_up_requirement',
                    'pre_approved_offers'
                ]
            }
        
        # Default segment
        else:
            return {
                'segment': 'General Applicant',
                'age_group': f'{age}',
                'description': 'General loan applicant',
                'questions_focus': [
                    'employment_details',
                    'monthly_income',
                    'purpose',
                    'existing_loans'
                ]
            }


class BaseAgent:
    def __init__(self, name, role):
        self.name = name
        self.role = role
    
    def call_openai(self, messages, temperature=0.7):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
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
            Greet the user warmly and ask for their full name and date of birth to check their customer status.
            Explain that date of birth is needed for age verification and to provide personalized loan options.
            Keep it brief and professional."""},
            {"role": "user", "content": "Start the conversation"}
        ]
        return self.call_openai(messages)
    
    def extract_name_and_dob(self, conversation_history):
        """Extract both name and date of birth from conversation"""
        messages = [
            {"role": "system", "content": """Extract the full name and date of birth from the conversation.
            Return ONLY a JSON object with format:
            {
                "name": "full name",
                "date_of_birth": "YYYY-MM-DD or DD/MM/YYYY format"
            }
            
            If name is not found, set name to 'NOT_FOUND'.
            If DOB is not found, set date_of_birth to 'NOT_FOUND'.
            Be flexible with date formats."""}
        ]
        
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        messages.append({"role": "user", "content": conversation_text})
        
        response = self.call_openai(messages, temperature=0.3)
        try:
            cleaned = response.strip().replace('```json', '').replace('```', '').strip()
            return json.loads(cleaned.strip())
        except:
            return {"name": "NOT_FOUND", "date_of_birth": "NOT_FOUND"}
    
    def extract_name(self, conversation_history):
        """Extract name only (backward compatibility)"""
        result = self.extract_name_and_dob(conversation_history)
        return result.get('name', 'NOT_FOUND')
    
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
        
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
            return pan
        return 'NOT_FOUND'
    
    def request_pan_number(self, customer_name, age_segment=None):
        """Ask for PAN number from existing customer with age-aware messaging"""
        segment_context = ""
        if age_segment:
            if age_segment['segment'] == 'Young Salaried Professional':
                segment_context = " This will be quick and paperless - just like you prefer!"
            elif age_segment['segment'] == 'Existing Kite Capital Customer':
                segment_context = " As an existing customer, this will be ultra-fast!"
        
        messages = [
            {"role": "system", "content": f"""You are a Master Agent. 
            Tell the customer '{customer_name}' that we found their record.
            Ask them to provide their PAN number for verification.
            Mention the PAN format (e.g., ABCDE1234F).{segment_context}
            Keep it professional and reassuring."""},
            {"role": "user", "content": "Request PAN number"}
        ]
        return self.call_openai(messages)
    
    def request_pan_upload(self, customer_name, age_segment=None):
        """Request PAN card image upload after PAN number verification"""
        segment_context = ""
        if age_segment:
            if age_segment['segment'] == 'Young Salaried Professional':
                segment_context = " You can simply click a photo with your phone - easy and instant!"
            elif age_segment['segment'] == 'Self-Employed Professional/Small Business Owner':
                segment_context = " A clear scan or photo will work - part of standard documentation."
        
        messages = [
            {"role": "system", "content": f"""You are a Master Agent. 
            Tell the customer '{customer_name}' that their PAN number has been verified.
            Now ask them to upload a clear photo or scan of their PAN card for KYC verification.
            Mention that this is for their security and identity verification.{segment_context}
            Keep it professional and reassuring."""},
            {"role": "user", "content": "Request PAN card upload"}
        ]
        return self.call_openai(messages)
    
    def request_new_customer_pan(self, age_segment=None):
        """Ask new customer for their PAN number with age-aware messaging"""
        segment_context = ""
        if age_segment:
            if age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                segment_context = " Don't worry - this is standard for all loan applications and helps us serve you better."
            elif age_segment['segment'] == 'Young Salaried Professional':
                segment_context = " Quick and digital process ahead!"
        
        messages = [
            {"role": "system", "content": f"""You are a Master Agent.
            The user is a new customer. Ask them to provide their PAN number.
            Explain that PAN is mandatory for loan processing.
            Mention the format (e.g., ABCDE1234F - 5 letters, 4 digits, 1 letter).{segment_context}
            Keep it welcoming and professional."""},
            {"role": "user", "content": "Request PAN from new customer"}
        ]
        return self.call_openai(messages)
    
    def inform_new_customer(self, age_segment=None):
        """Inform about new customer status with age-aware messaging"""
        segment_context = ""
        if age_segment:
            segment_info = f"Based on your profile ({age_segment['segment']}), we'll tailor the process to your needs. "
            segment_context = segment_info
        
        messages = [
            {"role": "system", "content": f"""You are a Master Agent.
            Politely inform the user that they are a new customer and we'll need to collect their details.
            {segment_context}
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


class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Verification Agent", "KYC Validator")
    
    def request_kyc_details(self, session, age_segment=None):
        """Request KYC with age-aware messaging"""
        segment_context = ""
        if age_segment:
            if age_segment['segment'] == 'Young Salaried Professional':
                segment_context = " Quick digital upload from your phone works perfectly!"
            elif age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                segment_context = " Don't worry, this is a simple and secure process. We'll guide you through it."
        
        messages = [
            {"role": "system", "content": f"""You are a Verification Agent.
            Ask the customer to upload their Aadhar card image and provide their phone number.
            Explain this is for identity verification and their data security is our priority.{segment_context}
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
    
    def assess_loan(self, customer, loan_amount, tenure, age_segment=None):
        """Age-aware loan assessment"""
        loan_amount = Decimal(str(loan_amount))
        credit_score = customer.credit_score
        pre_approved_limit = customer.pre_approved_limit
        
        # Age-based risk adjustment
        age = CustomerSegmentation.get_age_from_dob(customer.date_of_birth) if hasattr(customer, 'date_of_birth') else None
        
        # Adjusted credit score threshold based on age segment
        min_credit_score = 700
        if age_segment:
            if age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                min_credit_score = 650  # More lenient for first-time borrowers
            elif age_segment['segment'] == 'Young Salaried Professional':
                min_credit_score = 680
            elif age_segment['segment'] == 'Mid-Career Salaried with Family':
                min_credit_score = 720  # Higher due to more obligations
        
        # Rule 1: Credit score check with age adjustment
        if credit_score < min_credit_score:
            return {
                'approved': False,
                'reason': f'Credit score below minimum threshold of {min_credit_score} for your profile'
            }
        
        # Rule 2: Instant approval if within pre-approved limit
        if loan_amount <= pre_approved_limit:
            return {
                'approved': True,
                'instant': True,
                'reason': 'Within pre-approved limit',
                'segment_note': f"Fast-tracked for {age_segment['segment']}" if age_segment else ""
            }
        
        # Rule 3: Age-segment specific evaluation
        if age_segment:
            if age_segment['segment'] == 'Self-Employed Professional/Small Business Owner':
                # Request business documents
                return {
                    'approved': 'pending_business_docs',
                    'reason': 'Requires ITR, GST, and bank statements',
                    'documents_needed': ['ITR (last 2 years)', 'GST returns', 'Bank statements (6 months)']
                }
            
            elif age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                # More documentation needed
                if loan_amount <= (pre_approved_limit * 1.5):
                    return {
                        'approved': 'pending_guarantor',
                        'reason': 'Requires guarantor or co-applicant for new-to-credit customers'
                    }
        
        # Rule 4: Request salary slip if ≤ 2× pre-approved limit
        if loan_amount <= (pre_approved_limit * 2):
            return {
                'approved': 'pending_salary_slip',
                'reason': 'Requires salary slip verification'
            }
        
        # Rule 5: Reject if > 2× pre-approved limit
        return {
            'approved': False,
            'reason': 'Loan amount exceeds 2× pre-approved limit'
        }
    
    def validate_salary_emi(self, salary, loan_amount, tenure_months, age_segment=None):
        """Validate EMI affordability with age-aware limits"""
        monthly_emi = Decimal(str(loan_amount)) / tenure_months
        salary_decimal = Decimal(str(salary))
        
        # Age-based EMI ratio
        max_emi_ratio = Decimal('0.50')  # Default 50%
        
        if age_segment:
            if age_segment['segment'] == 'Mid-Career Salaried with Family':
                max_emi_ratio = Decimal('0.40')  # More conservative for family obligations
            elif age_segment['segment'] == 'Young Salaried Professional':
                max_emi_ratio = Decimal('0.50')  # Standard
            elif age_segment['segment'] == 'Low-Income or New-to-Credit Applicant':
                max_emi_ratio = Decimal('0.35')  # More conservative
        
        if monthly_emi <= (salary_decimal * max_emi_ratio):
            return True, f"EMI within {max_emi_ratio*100}% of salary"
        return False, f"EMI exceeds {max_emi_ratio*100}% of monthly salary"


class SanctionLetterGenerator:
    @staticmethod
    def generate_letter(loan_application, age_segment=None):
        """Generate sanction letter with segment info"""
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
            
            # Add segment info if available
            if age_segment:
                p.setFont("Helvetica", 10)
                p.setFillColorRGB(0.2, 0.3, 0.6)
                p.drawString(inch, y, f"Customer Profile: {age_segment['segment']} (Age: {age_segment['age_group']})")
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
                "6. All documents have been verified using secure AI-powered verification.",
                "7. Loan terms customized based on customer profile and creditworthiness."
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
            raise(e)
        except:
            return {"name": "NOT_FOUND", "date_of_birth": "NOT_FOUND"}


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
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
                image_file.seek(0)
            else:
                image_data = image_file
            
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
            verification_result = self._parse_verification_response(response)
            
            if verification_result.get('is_valid_pan_card'):
                name_match = self._verify_name_match(
                    expected_name, 
                    verification_result.get('name_on_card', '')
                )
                verification_result['name_match'] = name_match
                
                if not name_match['matches']:
                    verification_result['is_valid_pan_card'] = False
                    verification_result['verification_notes'] += f" | Name mismatch: {name_match['reason']}"
                
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
            
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            return json.loads(cleaned_response.strip())
        except json.JSONDecodeError:
            return {
                'is_valid_pan_card': False,
                'verification_notes': 'Failed to parse verification response',
                'raw_response': response
            }
    
    def _verify_name_match(self, provided_name, extracted_name):
        """Verify if the provided name matches the extracted name"""
        provided_clean = re.sub(r'[^a-zA-Z\s]', '', provided_name.upper()).strip()
        extracted_clean = re.sub(r'[^a-zA-Z\s]', '', extracted_name.upper()).strip()
        
        if provided_clean == extracted_clean:
            return {'matches': True, 'confidence': 100, 'reason': 'Exact match'}
        
        provided_words = set(provided_clean.split())
        extracted_words = set(extracted_clean.split())
        common_words = provided_words.intersection(extracted_words)
        
        if len(common_words) >= len(provided_words) * 0.8:
            return {
                'matches': True, 
                'confidence': 85,
                'reason': 'Substantial word match'
            }
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a name matching expert. Compare two names and determine if they refer to the same person.
                    Consider variations like middle names, initials, nicknames, spelling variations.
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
    
    def engage_customer(self, session, conversation_history, age_segment=None):
        """Engage customer with age-segment-aware questions"""
        
        # Build segment-specific context
        segment_context = ""
        questions_focus = []
        
        if age_segment:
            segment_context = f"""
Customer Profile:
- Segment: {age_segment['segment']}
- Age Group: {age_segment['age_group']}
- Typical Needs: {', '.join(age_segment.get('needs', []))}
- Behavior: {', '.join(age_segment.get('behaviour', []))}

Tailor your questions based on this profile. """
            
            questions_focus = age_segment.get('questions_focus', [])
            
            # Add segment-specific question guidance
            if 'Young Salaried Professional' in age_segment['segment']:
                segment_context += """
Ask about:
- Employment details (company type, designation)
- Monthly take-home salary
- Loan purpose (gadgets, travel, education, emergency)
- Preferred digital payment methods
- Quick EMI affordability check"""
            
            elif 'Mid-Career Salaried with Family' in age_segment['segment']:
                segment_context += """
Ask about:
- Family size and dependents
- Monthly income and existing EMI obligations
- Purpose (children's education, medical, home renovation, wedding, debt consolidation)
- Home ownership status
- Preferred loan tenure for budget planning"""
            
            elif 'Self-Employed' in age_segment['segment']:
                segment_context += """
Ask about:
- Type of business/profession
- Business vintage (years in operation)
- Monthly/Annual turnover
- Purpose (working capital, expansion, equipment, personal emergency)
- GST registration and ITR filing status
- Business documentation availability"""
            
            elif 'Low-Income or New-to-Credit' in age_segment['segment']:
                segment_context += """
Ask about:
- Current employment (gig work, entry-level, first job)
- Monthly income
- Loan amount needed (keep it realistic for their profile)
- Purpose (education, vehicle, emergency, settling in new city)
- Any guarantor availability
- Reassure them about the process"""
            
            elif 'Existing Kite Capital Customer' in age_segment['segment']:
                segment_context += """
Ask about:
- Previous loan experience with us
- Top-up requirement or new loan
- Quick verification of pre-approved limit
- Purpose (should be brief)
- Preferred fast-track options"""
        
        system_prompt = f"""You are a Sales Agent for personal loans.{segment_context}

Ask the customer about:
1. Loan amount needed
2. Purpose of the loan  
3. Preferred tenure (in months)
4. Any other relevant details based on their profile

Be conversational, empathetic, and helpful. Extract information naturally.
Make them feel comfortable and understood."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation_history:
            messages.append({"role": msg['role'], "content": msg['content']})
        
        return self.call_openai(messages)
    
    def extract_loan_details(self, conversation_history, age_segment=None):
        """Extract loan details with segment-aware parsing"""
        
        segment_hint = ""
        if age_segment:
            segment_hint = f"\nCustomer segment: {age_segment['segment']}"
            segment_hint += f"\nTypical needs: {', '.join(age_segment.get('needs', []))}"
        
        messages = [
            {"role": "system", "content": f"""Extract loan details from the conversation.{segment_hint}
            Return ONLY a JSON object with: 
            {{
                "loan_amount": number,
                "purpose": string,
                "tenure_months": number,
                "employment_type": "salaried/self_employed/business/gig_worker/other",
                "monthly_income": number (if mentioned),
                "existing_obligations": number (if mentioned),
                "segment_specific_data": {{}} (any additional relevant info)
            }}
            
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
        except Exception as e:
            return {
                "loan_amount": None,
                "purpose": None,
                "tenure_months": None,
                "employment_type": None,
                "monthly_income": None,
                "existing_obligations": None,
                "segment_specific_data": {},
                "error": str(e)
            }