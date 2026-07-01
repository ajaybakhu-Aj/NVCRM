import django.utils.timezone
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
        ('Local', 'Local Procurement'),
        ('International', 'International Procurement'),
    ]
    STATUS_CHOICES = [
        ('Draft', 'Procurement Start'),
        ('Pending_HR_COO', 'Review & Approve: HR & COO'),
        ('Pending_CTO', 'Review & Decide: CTO'),
        ('Pending_Amend', 'User Action: Amend Quantity'),
        ('Execution', 'Procurement Execution'),
        ('Pending_LCM', 'Post-Procurement: Integrate LCM'),
        ('Pending_GRN', 'GRN Process & Inventory Intake'),
        ('Completed', 'Process End'),
        ('Closed', 'Requisition Closed (Denied)'),
    ]
    
    title = models.CharField(max_length=255)
    track = models.CharField(max_length=20, choices=TRACK_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    supporting_document = models.FileField(upload_to='procurement_docs/', null=True, blank=True)
    
    # Requisition Details
    product_sku = models.CharField(max_length=100, default='UNKNOWN')
    requested_quantity = models.IntegerField(default=1)
    amended_quantity = models.IntegerField(null=True, blank=True)  # Populated via Amend loop
    
    # Financials & LCM
    landing_cost_management = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    goods_receive_notes = models.CharField(max_length=255, blank=True, null=True)
    
    # Signatures & Segregation of Duties
    submitted_by_uid = models.CharField(max_length=100, blank=True, null=True)
    hr_approved = models.BooleanField(default=False)
    coo_approved = models.BooleanField(default=False)
    cto_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ProcurementItem(models.Model):
    """Tracks serially integrated products mapped dynamically to specific sub-inventory slots."""
    request = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name='serialized_items')
    serial_number = models.CharField(max_length=100, unique=True)
    locator = models.CharField(max_length=50) # 'FRESH', 'DAMAGE', 'BASIADE'
    is_integrated = models.BooleanField(default=False)

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
        ('Mourning', 'Mourning Leave'),
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
        ('Pending Approval', 'Pending Approval'),
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

    @property
    def is_early_checkout(self):
        if self.check_out_time:
            from datetime import time
            return self.check_out_time < time(17, 0)
        return False

class MissedAttendanceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    employee = models.ForeignKey('SystemUserProfile', on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    check_in_time = models.TimeField()
    check_out_time = models.TimeField()
    reason = models.TextField()
    
    hr_approved = models.BooleanField(default=False)
    operation_approved = models.BooleanField(default=False)
    coo_approved = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.full_name} - Missed Attendance {self.start_date} to {self.end_date}"
    
    @property
    def is_fully_approved(self):
        return self.hr_approved and self.operation_approved and self.coo_approved

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
    can_access_account_expenses = models.BooleanField(default=False)
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

class ExpenseRecord(models.Model):
    CATEGORY_CHOICES = [
        ('Operations', 'Operations & Office'),
        ('Payroll', 'Payroll & Benefits'),
        ('Marketing', 'Marketing & Sales'),
        ('Procurement', 'Hardware Procurement (COGS)'),
        ('Utilities', 'Utilities & Internet'),
        ('Software', 'Software & IT Subscriptions'),
        ('Travel', 'Travel & Transport'),
        ('Misc', 'Miscellaneous'),
    ]
    
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    date = models.DateField(default=django.utils.timezone.now)
    description = models.TextField(blank=True, null=True)
    logged_by = models.ForeignKey(SystemUserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Rs. {self.amount}"

class PayrollCycle(models.Model):
    """Tracks the state of a monthly payroll cycle (Nepali Calendar)."""
    np_year = models.IntegerField()
    np_month = models.IntegerField()
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('np_year', 'np_month')

    def __str__(self):
        return f"Cycle: {self.np_year}-{self.np_month} ({'Frozen' if self.is_finalized else 'Draft'})"

class PayrollRecord(models.Model):
    """Stores the calculated breakdown for an employee for a specific cycle."""
    cycle = models.ForeignKey(PayrollCycle, on_delete=models.CASCADE, related_name='records')
    employee = models.ForeignKey('SystemUserProfile', on_delete=models.CASCADE)
    
    # Day Classifications
    present_days = models.IntegerField(default=0)
    weekends = models.IntegerField(default=0)
    holidays = models.IntegerField(default=0)
    paid_leaves = models.IntegerField(default=0)
    unpaid_leaves = models.IntegerField(default=0)
    total_paid_days = models.IntegerField(default=0)
    
    # Financials
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

class MoveOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('In_Transit', 'Execute Move Order: In-Transit'),
        ('Goods_Verified', 'Goods Verified'),
        ('Issue_Report', 'Issue Report Generated'),
        ('Completed', 'Completed - Stock Adjusted'),
    ]
    
    LOCATOR_CHOICES = [
        ('Fresh', 'FRESH'),
        ('Damaged', 'DAMAGE'),
        ('Refurbished', 'REFURBISHED'),
        ('Repairable', 'REPAIRABLE'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    
    # 1. Bi-directional Origin/Destination
    source_node = models.ForeignKey('OrgNode', on_delete=models.CASCADE, related_name='outbound_transfers')
    destination_node = models.ForeignKey('OrgNode', on_delete=models.CASCADE, related_name='inbound_transfers')
    
    sku_id = models.CharField(max_length=100)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    
    # 2. Enforce Required Stock Locators
    locator_type = models.CharField(max_length=20, choices=LOCATOR_CHOICES)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    
    # 3. Icon-driven Checklist Verifications
    checklist_driver_assigned = models.BooleanField(default=False)
    checklist_vehicle_secured = models.BooleanField(default=False)
    checklist_documents_printed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Enforce strict HQ <-> Dealer bi-directional logic."""
        from django.core.exceptions import ValidationError
        if self.source_node.node_type == 'HQ' and self.destination_node.node_type == 'HQ':
            raise ValidationError("Invalid Transfer: HQ cannot transfer directly to HQ.")
        if self.source_node.node_type != 'HQ' and self.destination_node.node_type != 'HQ':
            raise ValidationError("Invalid Transfer: Dealer-to-Dealer transfers are restricted. Must be HQ <-> Dealer.")
            
    @property
    def is_checklist_complete(self):
        return self.checklist_driver_assigned and self.checklist_vehicle_secured and self.checklist_documents_printed
