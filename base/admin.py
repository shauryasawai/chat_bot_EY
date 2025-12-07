from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Customer, ChatSession, LoanApplication, DocumentVerification


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'name', 
        'pan', 
        'pan_verified_badge',
        'credit_score',
        'pre_approved_limit',
        'created_at'
    ]
    list_filter = [
        'pan_verified',
        'created_at',
        'credit_score'
    ]
    search_fields = [
        'name', 
        'pan',
        'phone'
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'pan_verification_date',
        'pan_card_preview'
    ]
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'name',
                'phone'
            )
        }),
        ('KYC Documents', {
            'fields': (
                'pan',
                'aadhar',
                'pan_card_image',
                'pan_card_preview'
            )
        }),
        ('Verification Status', {
            'fields': (
                'pan_verified',
                'pan_verification_date',
                'pan_verification_confidence'
            )
        }),
        ('Credit Information', {
            'fields': (
                'credit_score',
                'pre_approved_limit'
            )
        }),
        ('Timestamps', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def pan_verified_badge(self, obj):
        """Display PAN verification status badge"""
        if not obj:
            return '-'
        
        if obj.pan_verified:
            html_content = (
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✓ Verified</span>'
            )
        else:
            html_content = (
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✗ Not Verified</span>'
            )
        return mark_safe(html_content)
    
    pan_verified_badge.short_description = 'PAN Status'
    
    def pan_card_preview(self, obj):
        """Display PAN card image preview"""
        if not obj:
            return "No data"
        
        if obj.pan_card_image:
            try:
                img_url = obj.pan_card_image.url
                html_content = (
                    f'<img src="{img_url}" style="max-width: 300px; max-height: 200px; '
                    f'border: 2px solid #ddd; border-radius: 5px;"/>'
                    f'<br><a href="{img_url}" target="_blank">View Full Size</a>'
                )
                return mark_safe(html_content)
            except Exception as e:
                return f"Error loading image: {str(e)}"
        return "No PAN card image uploaded"
    
    pan_card_preview.short_description = 'PAN Card Image'
    
    actions = ['mark_as_verified', 'reset_verification']
    
    def mark_as_verified(self, request, queryset):
        """Mark selected customers as verified"""
        from django.utils import timezone
        updated = queryset.update(
            pan_verified=True,
            pan_verification_date=timezone.now()
        )
        self.message_user(request, f'{updated} customer(s) marked as verified.')
    
    mark_as_verified.short_description = 'Mark selected customers as verified'
    
    def reset_verification(self, request, queryset):
        """Reset verification status"""
        updated = queryset.update(
            pan_verified=False,
            pan_verification_date=None,
            pan_verification_confidence=None
        )
        self.message_user(request, f'{updated} customer(s) verification reset.')
    
    reset_verification.short_description = 'Reset verification status'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'customer_link',
        'stage',
        'message_count',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'stage',
        'created_at'
    ]
    search_fields = [
        'customer__name',
        'customer__pan',
        'customer_name'
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'conversation_display'
    ]
    fieldsets = (
        ('Session Information', {
            'fields': (
                'id',
                'customer',
                'customer_name',
                'stage'
            )
        }),
        ('Conversation Data', {
            'fields': (
                'conversation_display',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def customer_link(self, obj):
        """Display customer link"""
        if not obj or not obj.customer:
            if obj and obj.customer_name:
                return obj.customer_name
            return mark_safe('<span style="color: #999;">No customer</span>')
        
        try:
            url = reverse('admin:base_customer_change', args=[obj.customer.id])
            return mark_safe(f'<a href="{url}">{obj.customer.name}</a>')
        except Exception as e:
            return str(obj.customer.name)
    
    customer_link.short_description = 'Customer'
    
    def message_count(self, obj):
        """Count messages in conversation"""
        if not obj:
            return 0
        
        try:
            conversation = obj.get_conversation_history()
            return len(conversation) if conversation else 0
        except:
            return 0
    
    message_count.short_description = 'Messages'
    
    def conversation_display(self, obj):
        """Display conversation history"""
        if not obj:
            return "No conversation yet"
        
        try:
            conversation = obj.get_conversation_history()
            if not conversation:
                return "No conversation yet"
            
            html = '<div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">'
            for i, msg in enumerate(conversation):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                agent = msg.get('agent', '')
                
                if role == 'user':
                    color = '#007bff'
                    icon = '👤'
                else:
                    color = '#28a745'
                    icon = '🤖'
                
                html += f'''
                    <div style="margin-bottom: 15px; padding: 10px; background: white; border-left: 3px solid {color}; border-radius: 3px;">
                        <div style="font-weight: bold; color: {color}; margin-bottom: 5px;">
                            {icon} {role.upper()} {f"({agent})" if agent else ""}
                        </div>
                        <div style="color: #333;">{content}</div>
                    </div>
                '''
            html += '</div>'
            return mark_safe(html)
        except Exception as e:
            return f"Error displaying conversation: {str(e)}"
    
    conversation_display.short_description = 'Conversation History'


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'application_id',
        'customer_link',
        'loan_amount_formatted',
        'tenure_months',
        'status_badge',
        'applied_at'
    ]
    list_filter = [
        'status',
        'applied_at',
        'tenure_months'
    ]
    search_fields = [
        'customer__name',
        'customer__pan',
        'purpose'
    ]
    readonly_fields = [
        'id',
        'applied_at',
        'approved_at',
        'rejected_at',
        'updated_at',
        'sanction_letter_preview'
    ]
    fieldsets = (
        ('Application Details', {
            'fields': (
                'id',
                'customer',
                'loan_amount',
                'purpose',
                'tenure_months'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'assessment_notes',
                'approval_reason',
                'rejection_reason'
            )
        }),
        ('Documents', {
            'fields': (
                'sanction_letter',
                'sanction_letter_preview'
            )
        }),
        ('Timestamps', {
            'fields': (
                'applied_at',
                'approved_at',
                'rejected_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def application_id(self, obj):
        """Display formatted application ID"""
        if not obj:
            return '-'
        return f"LA-{obj.id:06d}"
    
    application_id.short_description = 'Application ID'
    
    def customer_link(self, obj):
        """Display customer link"""
        if not obj or not obj.customer:
            return '-'
        
        try:
            url = reverse('admin:base_customer_change', args=[obj.customer.id])
            return mark_safe(f'<a href="{url}">{obj.customer.name}</a>')
        except Exception as e:
            return str(obj.customer.name)
    
    customer_link.short_description = 'Customer'
    
    def loan_amount_formatted(self, obj):
        """Display formatted loan amount"""
        if not obj:
            return '-'
        
        html_content = f'<strong style="color: #28a745;">₹{obj.loan_amount:,.2f}</strong>'
        return mark_safe(html_content)
    
    loan_amount_formatted.short_description = 'Loan Amount'
    
    def status_badge(self, obj):
        """Display status badge"""
        if not obj:
            return '-'
        
        colors = {
            'pending': '#ffc107',
            'under_review': '#17a2b8',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'disbursed': '#007bff'
        }
        color = colors.get(obj.status, '#6c757d')
        html_content = (
            f'<span style="background-color: {color}; color: white; padding: 5px 12px; '
            f'border-radius: 3px; font-weight: bold; text-transform: uppercase;">{obj.status}</span>'
        )
        return mark_safe(html_content)
    
    status_badge.short_description = 'Status'
    
    def sanction_letter_preview(self, obj):
        """Display sanction letter download link"""
        if not obj:
            return "No data"
        
        if obj.sanction_letter:
            html_content = f'📄 <a href="{obj.sanction_letter.url}" target="_blank">Download Sanction Letter</a>'
            return mark_safe(html_content)
        return "No sanction letter generated"
    
    sanction_letter_preview.short_description = 'Sanction Letter'
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        """Approve selected applications"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} application(s) approved.')
    
    approve_applications.short_description = 'Approve selected applications'
    
    def reject_applications(self, request, queryset):
        """Reject selected applications"""
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            rejected_at=timezone.now(),
            rejection_reason='Manually rejected by admin'
        )
        self.message_user(request, f'{updated} application(s) rejected.')
    
    reject_applications.short_description = 'Reject selected applications'


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'customer_link',
        'document_type',
        'verification_badge',
        'confidence_display',
        'ai_model_used',
        'verification_timestamp'
    ]
    list_filter = [
        'document_type',
        'is_verified',
        'verification_timestamp',
        'ai_model_used'
    ]
    search_fields = [
        'customer__name',
        'customer__pan',
        'verification_notes'
    ]
    readonly_fields = [
        'verification_timestamp',
        'document_preview',
        'extracted_data_display'
    ]
    fieldsets = (
        ('Document Information', {
            'fields': (
                'customer',
                'document_type',
                'document_file',
                'document_preview'
            )
        }),
        ('Verification Results', {
            'fields': (
                'is_verified',
                'confidence_score',
                'verification_notes'
            )
        }),
        ('Extracted Data', {
            'fields': (
                'extracted_data_display',
            )
        }),
        ('AI Model Details', {
            'fields': (
                'ai_model_used',
                'verification_timestamp'
            )
        })
    )
    
    def customer_link(self, obj):
        """Display customer link"""
        if not obj or not obj.customer:
            return '-'
        
        try:
            url = reverse('admin:base_customer_change', args=[obj.customer.id])
            return mark_safe(f'<a href="{url}">{obj.customer.name}</a>')
        except Exception as e:
            return str(obj.customer.name)
    
    customer_link.short_description = 'Customer'
    
    def verification_badge(self, obj):
        """Display verification status badge"""
        if not obj:
            return '-'
        
        if obj.is_verified:
            html_content = (
                '<span style="background-color: #28a745; color: white; padding: 5px 12px; '
                'border-radius: 3px; font-weight: bold;">✓ VERIFIED</span>'
            )
        else:
            html_content = (
                '<span style="background-color: #dc3545; color: white; padding: 5px 12px; '
                'border-radius: 3px; font-weight: bold;">✗ FAILED</span>'
            )
        return mark_safe(html_content)
    
    verification_badge.short_description = 'Status'
    
    def confidence_display(self, obj):
        """Display confidence score"""
        if not obj or obj.confidence_score is None:
            return "-"
        
        if obj.confidence_score >= 80:
            color = '#28a745'
        elif obj.confidence_score >= 60:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        html_content = f'<span style="color: {color}; font-weight: bold; font-size: 16px;">{obj.confidence_score}%</span>'
        return mark_safe(html_content)
    
    confidence_display.short_description = 'Confidence'
    
    def document_preview(self, obj):
        """Display document preview or download link"""
        if not obj or not obj.document_file:
            return "No document"
        
        if obj.document_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            html_content = (
                f'<img src="{obj.document_file.url}" style="max-width: 400px; max-height: 300px; '
                f'border: 2px solid #ddd; border-radius: 5px;"/>'
            )
            return mark_safe(html_content)
        
        html_content = f'📄 <a href="{obj.document_file.url}" target="_blank">Download Document</a>'
        return mark_safe(html_content)
    
    document_preview.short_description = 'Document'
    
    def extracted_data_display(self, obj):
        """Display extracted data from document"""
        if not obj or not obj.extracted_data:
            return "No extracted data"
        
        import json
        formatted = json.dumps(obj.extracted_data, indent=2)
        html_content = (
            f'<pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; '
            f'max-height: 300px; overflow-y: auto; border: 1px solid #ddd;">{formatted}</pre>'
        )
        return mark_safe(html_content)
    
    extracted_data_display.short_description = 'Extracted Data'


# Customize admin site header and title
admin.site.site_header = "AI Loan Processing Admin"
admin.site.site_title = "Loan Admin Portal"
admin.site.index_title = "Welcome to AI Loan Processing System"