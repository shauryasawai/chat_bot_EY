# models.py

from django.db import models
from django.utils import timezone
import json


class Customer(models.Model):
    name = models.CharField(max_length=200)
    pan = models.CharField(max_length=10, unique=True)
    pan_card_image = models.FileField(upload_to='pan_cards/', null=True, blank=True)
    selfie_image = models.FileField(upload_to='selfies/', null=True, blank=True)
    aadhar = models.CharField(max_length=12, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    credit_score = models.IntegerField(default=0)
    pre_approved_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # KYC verification fields
    pan_verified = models.BooleanField(default=False)
    pan_verification_date = models.DateTimeField(null=True, blank=True)
    pan_verification_confidence = models.IntegerField(null=True, blank=True)
    face_match_verified = models.BooleanField(default=False)
    face_match_confidence = models.IntegerField(null=True, blank=True)
    
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
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='greeting')
    conversation_data = models.TextField(default='[]')  # JSON stored as text
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
    
    # Underwriting details
    assessment_notes = models.TextField(null=True, blank=True)
    approval_reason = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Documents
    salary_slip = models.FileField(upload_to='salary_slips/', null=True, blank=True)
    sanction_letter = models.FileField(upload_to='sanction_letters/', null=True, blank=True)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"LA-{self.id:06d} - {self.customer.name} - ₹{self.loan_amount}"
    
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