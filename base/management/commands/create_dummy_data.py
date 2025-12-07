from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
import random
from base.models import Customer, LoanApplication

class Command(BaseCommand):
    help = 'Creates dummy customer and loan data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating dummy data...')
        
        # Create dummy customers
        customers_data = [
            {
                'name': 'Rajesh Kumar',
                'email': 'rajesh.kumar@email.com',
                'phone': '9876543210',
                'pan': 'ABCDE1234F',
                'aadhar': '123456789012',
                'credit_score': 780,
                'pre_approved_limit': Decimal('500000'),
                'salary': Decimal('80000'),
                'is_existing': True
            },
            {
                'name': 'Priya Sharma',
                'email': 'priya.sharma@email.com',
                'phone': '9876543211',
                'pan': 'BCDEF2345G',
                'aadhar': '234567890123',
                'credit_score': 720,
                'pre_approved_limit': Decimal('300000'),
                'salary': Decimal('60000'),
                'is_existing': True
            },
            {
                'name': 'Amit Patel',
                'email': 'amit.patel@email.com',
                'phone': '9876543212',
                'pan': 'CDEFG3456H',
                'aadhar': '345678901234',
                'credit_score': 650,
                'pre_approved_limit': Decimal('200000'),
                'salary': Decimal('45000'),
                'is_existing': False
            },
            {
                'name': 'Sneha Reddy',
                'email': 'sneha.reddy@email.com',
                'phone': '9876543213',
                'pan': 'DEFGH4567I',
                'aadhar': '456789012345',
                'credit_score': 810,
                'pre_approved_limit': Decimal('800000'),
                'salary': Decimal('120000'),
                'is_existing': True
            },
            {
                'name': 'Vikram Singh',
                'email': 'vikram.singh@email.com',
                'phone': '9876543214',
                'pan': 'EFGHI5678J',
                'aadhar': '567890123456',
                'credit_score': 690,
                'pre_approved_limit': Decimal('250000'),
                'salary': Decimal('50000'),
                'is_existing': True
            },
            {
                'name': 'Ananya Iyer',
                'email': 'ananya.iyer@email.com',
                'phone': '9876543215',
                'pan': 'FGHIJ6789K',
                'aadhar': '678901234567',
                'credit_score': 750,
                'pre_approved_limit': Decimal('600000'),
                'salary': Decimal('95000'),
                'is_existing': False
            },
            {
                'name': 'Rahul Mehta',
                'email': 'rahul.mehta@email.com',
                'phone': '9876543216',
                'pan': 'GHIJK7890L',
                'aadhar': '789012345678',
                'credit_score': 670,
                'pre_approved_limit': Decimal('150000'),
                'salary': Decimal('40000'),
                'is_existing': True
            },
            {
                'name': 'Deepika Verma',
                'email': 'deepika.verma@email.com',
                'phone': '9876543217',
                'pan': 'HIJKL8901M',
                'aadhar': '890123456789',
                'credit_score': 790,
                'pre_approved_limit': Decimal('700000'),
                'salary': Decimal('110000'),
                'is_existing': True
            },
            {
                'name': 'Arjun Nair',
                'email': 'arjun.nair@email.com',
                'phone': '9876543218',
                'pan': 'IJKLM9012N',
                'aadhar': '901234567890',
                'credit_score': 640,
                'pre_approved_limit': Decimal('180000'),
                'salary': Decimal('42000'),
                'is_existing': False
            },
            {
                'name': 'Kavya Desai',
                'email': 'kavya.desai@email.com',
                'phone': '9876543219',
                'pan': 'JKLMN0123O',
                'aadhar': '012345678901',
                'credit_score': 820,
                'pre_approved_limit': Decimal('1000000'),
                'salary': Decimal('150000'),
                'is_existing': True
            }
        ]

        customers = []
        for data in customers_data:
            customer, created = Customer.objects.get_or_create(
                phone=data['phone'],
                defaults=data
            )
            customers.append(customer)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created customer: {customer.name}'))

        # Create dummy loan applications
        loan_purposes = [
            'Home renovation',
            'Wedding expenses',
            'Medical emergency',
            'Education fees',
            'Business expansion',
            'Debt consolidation',
            'Vehicle purchase',
            'Travel expenses',
            'Electronic gadgets',
            'Personal emergency'
        ]

        statuses = ['initiated', 'in_progress', 'approved', 'rejected']
        
        for i, customer in enumerate(customers):
            # Create 1-2 loan applications per customer
            num_loans = random.randint(1, 2)
            
            for j in range(num_loans):
                loan_amount = random.choice([
                    customer.pre_approved_limit * Decimal('0.5'),  # Within limit
                    customer.pre_approved_limit * Decimal('0.8'),  # Within limit
                    customer.pre_approved_limit * Decimal('1.5'),  # Needs salary slip
                    customer.pre_approved_limit * Decimal('2.5'),  # Will be rejected
                ])
                
                loan = LoanApplication.objects.create(
                    customer=customer,
                    loan_amount=round(loan_amount, 2),
                    purpose=random.choice(loan_purposes),
                    tenure_months=random.choice([12, 24, 36, 48, 60]),
                    status=random.choice(statuses)
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created loan application for {customer.name}: ₹{loan.loan_amount} - {loan.status}'
                    )
                )

        self.stdout.write(self.style.SUCCESS('\nDummy data creation completed!'))
        self.stdout.write(f'Total Customers: {Customer.objects.count()}')
        self.stdout.write(f'Total Loan Applications: {LoanApplication.objects.count()}')