from django.db import models
from django.utils import timezone
import json


class Customer(models.Model):
    EMPLOYMENT_CHOICES = [
        ('salaried', 'Salaried'),
        ('self_employed', 'Self Employed'),
        ('business_owner', 'Business Owner'),
        ('freelancer', 'Freelancer'),
        ('gig_worker', 'Gig Worker'),
        ('government', 'Government'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200)
    pan = models.CharField(max_length=10, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Contact Information
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Documents
    pan_card_image = models.FileField(upload_to='pan_cards/', null=True, blank=True)
    selfie_image = models.FileField(upload_to='selfies/', null=True, blank=True)
    aadhar = models.CharField(max_length=12, null=True, blank=True)
    
    # Financial Information - UPDATED FOR DYNAMIC CREDIT SCORE
    credit_score = models.IntegerField(default=0, help_text="Dynamically calculated credit score (300-900)")
    score_category = models.CharField(max_length=20, null=True, blank=True, help_text="Excellent/Good/Fair/Poor")
    pre_approved_limit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Dynamically calculated maximum loan amount"
    )
    
    # Employment & Income Details - EXPANDED
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, null=True, blank=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    company_name = models.CharField(max_length=200, null=True, blank=True)
    
    # NEW: Additional employment details for credit scoring
    designation = models.CharField(
        max_length=200, 
        null=True, 
        blank=True,
        help_text="Job title/position (e.g., Senior Software Engineer, Manager)"
    )
    employment_duration_months = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Duration with current employer in months"
    )
    existing_obligations = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        null=True,
        blank=True,
        help_text="Total monthly EMI of existing loans"
    )
    
    # Customer Segmentation
    customer_segment = models.CharField(max_length=100, null=True, blank=True)
    segment_calculated_at = models.DateTimeField(null=True, blank=True)
    
    # KYC verification fields
    pan_verified = models.BooleanField(default=False)
    pan_verification_date = models.DateTimeField(null=True, blank=True)
    pan_verification_confidence = models.IntegerField(null=True, blank=True)
    face_match_verified = models.BooleanField(default=False)
    face_match_confidence = models.IntegerField(null=True, blank=True)
    selfie_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_age(self):
        """Calculate customer's age from date of birth"""
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        return age
    
    def get_segment(self):
        """Get customer segment based on age, employment, and income"""
        from .agents import CustomerSegmentation
        age = self.calculate_age()
        if age is None:
            return None
        return CustomerSegmentation.determine_segment(age, self.employment_type, self.monthly_income)
    
    def update_segment(self):
        """Update and save customer segment"""
        segment_info = self.get_segment()
        if segment_info:
            self.customer_segment = segment_info['segment']
            self.segment_calculated_at = timezone.now()
            self.save(update_fields=['customer_segment', 'segment_calculated_at'])
    
    def calculate_credit_score(self):
        """
        Calculate dynamic credit score based on employment and income details
        Returns dict with credit_score, score_category, and max_eligible_amount
        """
        from .agents import CreditScoreCalculator
        
        # Prepare loan details for scoring
        loan_details = {
            'company_name': self.company_name,
            'designation': self.designation,
            'monthly_income': float(self.monthly_income) if self.monthly_income else None,
            'employment_duration_months': self.employment_duration_months,
            'employment_type': self.employment_type,
            'existing_obligations': float(self.existing_obligations) if self.existing_obligations else 0,
            # For initial scoring, use average loan parameters
            'loan_amount': float(self.monthly_income * 10) if self.monthly_income else 100000,
            'tenure_months': 24
        }
        
        return CreditScoreCalculator.calculate_credit_score(loan_details)
    
    def update_credit_score(self):
        """Update credit score and pre-approved limit based on current data"""
        from .agents import CreditScoreCalculator
        
        if not self.monthly_income:
            return
        
        # Calculate credit score
        credit_analysis = self.calculate_credit_score()
        self.credit_score = credit_analysis['credit_score']
        self.score_category = credit_analysis['score_category']
        
        # Calculate max loan amount (assuming 24 month tenure)
        self.pre_approved_limit = CreditScoreCalculator.calculate_max_loan_amount(
            float(self.monthly_income),
            self.credit_score,
            24,  # Default tenure
            self.employment_type
        )
        
        self.save(update_fields=['credit_score', 'score_category', 'pre_approved_limit'])
    
    def __str__(self):
        return f"{self.name} ({self.pan})"
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'


class ChatSession(models.Model):
    STAGE_CHOICES = [
        ('greeting', 'Greeting'),
        ('name_collection', 'Name Collection'),
        ('pan_collection', 'PAN Collection'),
        ('pan_verification', 'PAN Verification'),
        ('selfie_verification', 'Selfie Verification'),
        ('loan_details', 'Loan Details'),
        ('salary_verification', 'Salary Verification'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    customer_name = models.CharField(max_length=200, null=True, blank=True)
    
    temp_dob = models.CharField(max_length=20, null=True, blank=True)
    
    temp_pan_image_data = models.TextField(
        null=True, 
        blank=True,
        help_text="Temporary base64 encoded PAN image for face matching - cleared after verification"
    )
    
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='greeting')
    conversation_data = models.TextField(default='[]')  # JSON stored as text
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_conversation_history(self):
        """Parse and return conversation history"""
        try:
            return json.loads(self.conversation_data)
        except:
            return []
    
    def clear_temp_data(self):
        """Clear temporary data after verification is complete"""
        self.temp_pan_image_data = None
        self.save()
    
    def __str__(self):
        return f"Session {self.id} - {self.stage}"
    
    class Meta:
        db_table = 'chat_sessions'
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'


class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loan_applications')
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length=500)
    tenure_months = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Customer segment at time of application
    customer_segment_snapshot = models.CharField(max_length=100, null=True, blank=True)
    
    # Underwriting details
    assessment_notes = models.TextField(null=True, blank=True)
    approval_reason = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # NEW: Dynamic Credit Score Assessment Data
    credit_score = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Credit score calculated at time of application"
    )
    max_eligible_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum loan amount customer is eligible for"
    )
    score_breakdown = models.JSONField(
        null=True, 
        blank=True,
        help_text="Detailed breakdown of credit score calculation"
    )
    
    # Underwriting metrics (age-aware)
    credit_score_threshold_used = models.IntegerField(null=True, blank=True)
    emi_ratio_threshold_used = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Documents
    salary_slip = models.FileField(upload_to='salary_slips/', null=True, blank=True)
    sanction_letter = models.FileField(upload_to='sanction_letters/', null=True, blank=True)

    salary_slip_data = models.JSONField(null=True, blank=True)
    sanction_letter_data = models.JSONField(null=True, blank=True)
    
    # Additional documents for self-employed
    itr_document = models.FileField(upload_to='itr_documents/', null=True, blank=True)
    gst_document = models.FileField(upload_to='gst_documents/', null=True, blank=True)
    bank_statements = models.FileField(upload_to='bank_statements/', null=True, blank=True)
    
    # In-memory document storage (base64 encoded)
    salary_slip_name = models.CharField(max_length=255, blank=True, null=True)
    salary_slip_content = models.TextField(blank=True, null=True)  # base64 encoded
    salary_slip_content_type = models.CharField(max_length=100, blank=True, null=True)
    salary_slip_size = models.IntegerField(blank=True, null=True)
    
    sanction_letter_name = models.CharField(max_length=255, blank=True, null=True)
    sanction_letter_content = models.TextField(blank=True, null=True)  # base64 encoded
    sanction_letter_content_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Auto-populate segment snapshot on creation"""
        if not self.pk and self.customer:  # Only on creation
            segment_info = self.customer.get_segment()
            if segment_info:
                self.customer_segment_snapshot = segment_info['segment']
        super().save(*args, **kwargs)
    
    def approve(self, reason=""):
        self.status = 'approved'
        self.approval_reason = reason
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, reason=""):
        self.status = 'rejected'
        self.rejection_reason = reason
        self.rejected_at = timezone.now()
        self.save()
    
    def calculate_monthly_emi(self):
        """Calculate simple EMI (without interest for now)"""
        if self.tenure_months > 0:
            return float(self.loan_amount) / self.tenure_months
        return 0
    
    def get_emi_to_income_ratio(self):
        """Calculate EMI to income ratio"""
        if self.customer and self.customer.monthly_income:
            emi = self.calculate_monthly_emi()
            return (emi / float(self.customer.monthly_income)) * 100
        return None
    
    def __str__(self):
        return f"LA-{self.id:06d} - {self.customer.name} - ₹{self.loan_amount}"
    
    class Meta:
        db_table = 'loan_applications'
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'
        ordering = ['-applied_at']


class DocumentVerification(models.Model):
    """Store detailed verification results for audit trail"""
    DOCUMENT_TYPES = [
        ('pan_card', 'PAN Card'),
        ('aadhar_card', 'Aadhar Card'),
        ('salary_slip', 'Salary Slip'),
        ('selfie', 'Selfie'),
        ('itr', 'ITR Document'),
        ('gst', 'GST Document'),
        ('bank_statement', 'Bank Statement'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='verifications/')
    
    # Verification results
    is_verified = models.BooleanField(default=False)
    confidence_score = models.IntegerField(null=True, blank=True)
    extracted_data = models.JSONField(default=dict)  # Store extracted information
    verification_notes = models.TextField(null=True, blank=True)
    
    # AI model details
    ai_model_used = models.CharField(max_length=100, default='gpt-4o')
    verification_timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.document_type} - {self.customer.name} - {'✓' if self.is_verified else '✗'}"
    
    class Meta:
        db_table = 'document_verifications'
        verbose_name = 'Document Verification'
        verbose_name_plural = 'Document Verifications'
        ordering = ['-verification_timestamp']