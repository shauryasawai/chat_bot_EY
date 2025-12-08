# management/commands/create_dummy_data.py
# Place this file in: your_app/management/commands/create_dummy_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
import json
from decimal import Decimal

from base.models import Customer, ChatSession, LoanApplication, DocumentVerification


class Command(BaseCommand):
    help = 'Creates dummy data for testing the lending platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customers',
            type=int,
            default=10,
            help='Number of customers to create'
        )

    def handle(self, *args, **options):
        num_customers = options['customers']
        
        self.stdout.write(self.style.SUCCESS('Creating dummy data...'))
        
        # Sample data
        first_names = ['Rajesh', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anjali', 'Rahul', 'Pooja', 'Arjun', 'Kavita']
        last_names = ['Sharma', 'Patel', 'Kumar', 'Singh', 'Reddy', 'Verma', 'Gupta', 'Joshi', 'Nair', 'Mehta']
        loan_purposes = [
            'Home renovation',
            'Medical emergency',
            'Wedding expenses',
            'Education fees',
            'Business expansion',
            'Debt consolidation',
            'Vehicle purchase',
            'Travel expenses'
        ]
        
        # Clear existing data (optional)
        if self.confirm_action('Do you want to clear existing data?'):
            DocumentVerification.objects.all().delete()
            LoanApplication.objects.all().delete()
            ChatSession.objects.all().delete()
            Customer.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing data cleared.'))
        
        customers_created = []
        
        # Create Customers
        for i in range(num_customers):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            pan = f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            pan += f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            pan += f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            pan += f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            pan += f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            pan += f"{random.randint(1000, 9999)}"
            pan += f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[random.randint(0, 25)]}"
            
            aadhar = f"{random.randint(100000000000, 999999999999)}"
            phone = f"+91{random.randint(7000000000, 9999999999)}"
            credit_score = random.randint(300, 900)
            
            customer = Customer.objects.create(
                name=name,
                pan=pan,
                aadhar=aadhar,
                phone=phone,
                credit_score=credit_score,
                pre_approved_limit=Decimal(random.randint(50000, 500000)),
                pan_verified=random.choice([True, True, True, False]),  # 75% verified
                pan_verification_date=timezone.now() - timedelta(days=random.randint(1, 30)) if random.random() > 0.25 else None,
                pan_verification_confidence=random.randint(85, 99) if random.random() > 0.25 else None,
                face_match_verified=random.choice([True, True, False]),  # 66% verified
                face_match_confidence=random.randint(80, 98) if random.random() > 0.33 else None,
            )
            customers_created.append(customer)
            self.stdout.write(f"Created customer: {customer.name} ({customer.pan})")
        
        # Create Chat Sessions
        stages = ['greeting', 'name_collection', 'pan_collection', 'pan_verification', 
                  'selfie_verification', 'loan_details', 'salary_verification', 'completed']
        
        for customer in customers_created[:7]:  # Create sessions for 70% of customers
            conversation = [
                {"role": "assistant", "content": "Hello! Welcome to our lending platform. I'm here to help you with your loan application."},
                {"role": "user", "content": "Hi, I need a personal loan"},
                {"role": "assistant", "content": "Great! I'd be happy to help. May I know your full name?"},
                {"role": "user", "content": customer.name},
                {"role": "assistant", "content": f"Thank you, {customer.name}. Could you please provide your PAN number?"},
                {"role": "user", "content": customer.pan},
            ]
            
            session = ChatSession.objects.create(
                customer=customer,
                customer_name=customer.name,
                stage=random.choice(stages),
                conversation_data=json.dumps(conversation)
            )
            self.stdout.write(f"Created chat session for: {customer.name}")
        
        # Create Loan Applications
        statuses = ['pending', 'under_review', 'approved', 'rejected', 'disbursed']
        
        for customer in customers_created:
            # Create 1-3 loan applications per customer
            num_loans = random.randint(1, 3)
            for _ in range(num_loans):
                loan_amount = Decimal(random.randint(50000, 500000))
                status = random.choice(statuses)
                
                loan = LoanApplication.objects.create(
                    customer=customer,
                    loan_amount=loan_amount,
                    purpose=random.choice(loan_purposes),
                    tenure_months=random.choice([6, 12, 18, 24, 36, 48, 60]),
                    status=status,
                    assessment_notes=f"Credit score: {customer.credit_score}. Income verification completed." if status != 'pending' else None,
                    applied_at=timezone.now() - timedelta(days=random.randint(1, 60))
                )
                
                # Set approval/rejection details based on status
                if status == 'approved' or status == 'disbursed':
                    loan.approval_reason = "Good credit score and stable income verified"
                    loan.approved_at = loan.applied_at + timedelta(days=random.randint(1, 7))
                elif status == 'rejected':
                    loan.rejection_reason = random.choice([
                        "Credit score below threshold",
                        "Insufficient income documentation",
                        "High debt-to-income ratio"
                    ])
                    loan.rejected_at = loan.applied_at + timedelta(days=random.randint(1, 5))
                
                loan.save()
                self.stdout.write(f"Created loan application: LA-{loan.id:06d} for {customer.name}")
        
        # Create Document Verifications
        doc_types = ['pan_card', 'aadhar_card', 'salary_slip']
        
        for customer in customers_created:
            # Create 2-3 document verifications per customer
            num_docs = random.randint(2, 3)
            for _ in range(num_docs):
                doc_type = random.choice(doc_types)
                is_verified = random.choice([True, True, True, False])  # 75% verified
                
                extracted_data = {}
                if doc_type == 'pan_card':
                    extracted_data = {
                        "pan_number": customer.pan,
                        "name": customer.name,
                        "date_of_birth": "15/08/1985"
                    }
                elif doc_type == 'aadhar_card':
                    extracted_data = {
                        "aadhar_number": customer.aadhar,
                        "name": customer.name,
                        "address": "123 Main Street, Mumbai, Maharashtra"
                    }
                elif doc_type == 'salary_slip':
                    extracted_data = {
                        "monthly_salary": random.randint(30000, 150000),
                        "company_name": random.choice(["Tech Corp", "Finance Ltd", "Consulting Inc"]),
                        "month": "November 2024"
                    }
                
                verification = DocumentVerification.objects.create(
                    customer=customer,
                    document_type=doc_type,
                    is_verified=is_verified,
                    confidence_score=random.randint(85, 99) if is_verified else random.randint(40, 70),
                    extracted_data=extracted_data,
                    verification_notes="Document verified successfully" if is_verified else "Document quality insufficient",
                    ai_model_used=random.choice(['gpt-4o', 'gpt-4-vision', 'claude-3-opus']),
                    verification_timestamp=timezone.now() - timedelta(days=random.randint(1, 30))
                )
                self.stdout.write(f"Created document verification: {doc_type} for {customer.name}")
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Customers created: {Customer.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Chat sessions created: {ChatSession.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Loan applications created: {LoanApplication.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Document verifications created: {DocumentVerification.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('\nDummy data created successfully!'))
    
    def confirm_action(self, message):
        """Ask user for confirmation"""
        response = input(f"{message} (yes/no): ").lower()
        return response in ['yes', 'y']