# models.py

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
        ('other', 'Other'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200)
    pan = models.CharField(max_length=10, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)  # NEW: Critical for age segmentation
    
    # Contact Information
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Documents
    pan_card_image = models.FileField(upload_to='pan_cards/', null=True, blank=True)
    selfie_image = models.FileField(upload_to='selfies/', null=True, blank=True)
    aadhar = models.CharField(max_length=12, null=True, blank=True)
    
    # Financial Information
    credit_score = models.IntegerField(default=0)
    pre_approved_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # NEW: Employment & Income Details (for segmentation)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, null=True, blank=True)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    company_name = models.CharField(max_length=200, null=True, blank=True)
    
    # NEW: Customer Segmentation (auto-calculated, stored for reference)
    customer_segment = models.CharField(max_length=100, null=True, blank=True)
    segment_calculated_at = models.DateTimeField(null=True, blank=True)
    
    # KYC verification fields
    pan_verified = models.BooleanField(default=False)
    pan_verification_date = models.DateTimeField(null=True, blank=True)
    pan_verification_confidence = models.IntegerField(null=True, blank=True)
    face_match_verified = models.BooleanField(default=False)
    face_match_confidence = models.IntegerField(null=True, blank=True)
    
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
    
    # NEW: Temporary storage for DOB before customer is created
    temp_dob = models.CharField(max_length=20, null=True, blank=True)
    
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
    
    # NEW: Store segment at time of application
    customer_segment_snapshot = models.CharField(max_length=100, null=True, blank=True)
    
    # Underwriting details
    assessment_notes = models.TextField(null=True, blank=True)
    approval_reason = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # NEW: Underwriting metrics (age-aware)
    credit_score_threshold_used = models.IntegerField(null=True, blank=True)
    emi_ratio_threshold_used = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Documents
    salary_slip = models.FileField(upload_to='salary_slips/', null=True, blank=True)
    sanction_letter = models.FileField(upload_to='sanction_letters/', null=True, blank=True)
    
    # NEW: Additional documents for self-employed
    itr_document = models.FileField(upload_to='itr_documents/', null=True, blank=True)
    gst_document = models.FileField(upload_to='gst_documents/', null=True, blank=True)
    bank_statements = models.FileField(upload_to='bank_statements/', null=True, blank=True)
    
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
        ('selfie', 'Selfie'),  # NEW
        ('itr', 'ITR Document'),  # NEW
        ('gst', 'GST Document'),  # NEW
        ('bank_statement', 'Bank Statement'),  # NEW
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