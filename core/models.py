import uuid
from django.db import models
from django.core.validators import MinValueValidator

class OrgNode(models.Model):
    NODE_TYPES = [
        ('HQ', 'Root Node (HQ)'),
        ('CAT_A', 'Category A (Super-Distributor)'),
        ('CAT_B', 'Category B (Authorized Dealer)'),
    ]
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=10, choices=NODE_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    def __str__(self):
        return f"{self.name} ({self.get_node_type_display()})"

class InventoryLedger(models.Model):
    STATUS_CHOICES = [
        ('Fresh', 'Fresh'),
        ('Refurbished', 'Refurbished'),
        ('Repairable', 'Repairable'),
        ('Damaged', 'Damaged'),
    ]
    stock_record_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku_id = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255, default="NV-CCTV Dome Camera (Default)")
    category = models.CharField(max_length=100, default="Electronics")
    uom = models.CharField(max_length=50, default="Pcs")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=5000.00)
    product_image = models.FileField(upload_to='products/', null=True, blank=True)
    node_id = models.ForeignKey(OrgNode, on_delete=models.CASCADE, related_name='inventory')
    locator_bin_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    quantity_on_hand = models.IntegerField(validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sku_id} - {self.quantity_on_hand} at {self.node_id.name}"

class AccountsReceivable(models.Model):
    STATE_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Partially_Paid', 'Partially Paid'),
        ('Settled', 'Settled'),
        ('Disputed', 'Disputed'),
    ]
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Cheque', 'Cheque'),
        ('Credit', 'Credit'),
    ]
    invoice_number = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=255, default="WALK-IN CUSTOMER")
    customer_pan = models.CharField(max_length=50, null=True, blank=True)
    customer_address = models.CharField(max_length=255, null=True, blank=True)
    customer_phone = models.CharField(max_length=50, null=True, blank=True)
    node = models.ForeignKey(OrgNode, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='Unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Cash')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def remaining_balance(self):
        return float(self.amount_due) - float(self.amount_paid)

class LeadCRM(models.Model):
    PIPELINE_CHOICES = [
        ('Identified', 'Identified'),
        ('Proposal', 'Proposal'),
        ('Converted_To_Project', 'Converted To Project'),
        ('Dead', 'Dead'),
    ]
    lead_name = models.CharField(max_length=255)
    node = models.ForeignKey(OrgNode, on_delete=models.CASCADE)
    pipeline_state = models.CharField(max_length=30, choices=PIPELINE_CHOICES, default='Identified')
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    deal_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    product_inquiry = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class EmployeeProfile(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    node = models.ForeignKey(OrgNode, on_delete=models.CASCADE)
    marital_status = models.BooleanField(default=False, help_text="True=Married, False=Single")
    base_gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    dearness = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ProcurementRequest(models.Model):
    TRACK_CHOICES = [
        ('Local', 'Local'),
        ('International', 'International'),
    ]
    title = models.CharField(max_length=255)
    track = models.CharField(max_length=20, choices=TRACK_CHOICES)
    supporting_document = models.FileField(upload_to='procurement_docs/', null=True, blank=True)
    
    # New Fields
    landing_cost_management = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    goods_receive_notes = models.CharField(max_length=255, blank=True, null=True)
    
    # Signatures
    cto_approved = models.BooleanField(default=False)
    hr_approved = models.BooleanField(default=False)
    coo_approved = models.BooleanField(default=False)
    ceo_approved = models.BooleanField(default=False)

    is_terminal = models.BooleanField(default=False)

class CalendarEvent(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    is_female_holiday = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} on {self.date}"

class SystemLog(models.Model):
    user_name = models.CharField(max_length=255)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_name} - {self.action} at {self.timestamp}"

class LeaveSettings(models.Model):
    casual_leave_days = models.IntegerField(default=8)
    sick_leave_days = models.IntegerField(default=12)
    annual_leave_days = models.IntegerField(default=15)
    maternity_leave_days = models.IntegerField(default=98)
    paternity_leave_days = models.IntegerField(default=15)

    def __str__(self):
        return "Global Leave Settings"

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('Casual', 'Casual Leave'),
        ('Sick', 'Sick Leave'),
        ('Annual', 'Annual Leave'),
        ('Maternity', 'Maternity Leave'),
        ('Paternity', 'Paternity Leave'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    employee_name = models.CharField(max_length=255)
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_name} - {self.leave_type} ({self.status})"

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Late', 'Late'),
        ('Absent', 'Absent'),
        ('Leave', 'On Leave'),
    ]
    employee_name = models.CharField(max_length=255)
    date = models.DateField()
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Present')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee_name', 'date')

    def __str__(self):
        return f"{self.employee_name} - {self.date} ({self.status})"

class SystemUserProfile(models.Model):
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    uid = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255, default='Admin')
    profile_image = models.CharField(max_length=500, blank=True, null=True)
    node = models.CharField(max_length=100, default='HQ-NEPAL')
    
    # New Personal Details
    pan_number = models.CharField(max_length=50, blank=True, null=True)
    citizenship_number = models.CharField(max_length=50, blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    
    # New Fields
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='Male')
    educational_qualifications = models.TextField(blank=True, null=True)
    languages_known = models.CharField(max_length=255, blank=True, null=True)
    proficiency_level = models.CharField(max_length=50, blank=True, null=True)
    
    # Permissions
    global_telemetry = models.BooleanField(default=False)
    ledger_override = models.BooleanField(default=False)
    api_key_gen = models.BooleanField(default=False)
    audit_log_purge = models.BooleanField(default=False)
    hr_matrix_view = models.BooleanField(default=False)
    fleet_command = models.BooleanField(default=False)
    
    # Page Access Permissions
    can_access_dashboard = models.BooleanField(default=True)
    can_access_notice_board = models.BooleanField(default=True)
    can_access_time_attendance = models.BooleanField(default=True)
    can_access_leave = models.BooleanField(default=True)
    can_access_profiles = models.BooleanField(default=False)
    can_access_lead_pipeline = models.BooleanField(default=False)
    can_access_inventory = models.BooleanField(default=False)
    can_access_accounts_receivable = models.BooleanField(default=False)
    can_access_pos = models.BooleanField(default=False)
    can_access_procurement = models.BooleanField(default=False)
    can_access_task_board = models.BooleanField(default=False)
    can_access_staff_payroll = models.BooleanField(default=False)
    can_access_system_log = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.uid:
            import random
            num1 = random.randint(100, 999)
            let = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
            num2 = random.randint(10, 99)
            self.uid = f"{num1}-{let}-{num2}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.position})"

class StaffDocument(models.Model):
    user = models.ForeignKey(SystemUserProfile, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='staff_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.full_name} - {self.title}"

class Notice(models.Model):
    PRIORITY_CHOICES = [
        ('High Priority', 'High Priority'),
        ('Information', 'Information'),
        ('Standard', 'Standard'),
    ]
    title = models.CharField(max_length=255)
    content = models.TextField()
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Standard')
    author_name = models.CharField(max_length=255)
    department = models.CharField(max_length=100, default='HQ')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ProjectTask(models.Model):
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('REVIEW', 'Review'),
        ('DONE', 'Done'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    assigned_to = models.ForeignKey(SystemUserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assigned_by = models.ForeignKey(SystemUserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class SystemNotification(models.Model):
    recipient = models.ForeignKey(SystemUserProfile, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.recipient.full_name}: {self.message}"
