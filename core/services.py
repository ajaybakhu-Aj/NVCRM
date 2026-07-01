from decimal import Decimal
import calendar
from datetime import date
from .models import ProcurementRequest, EmployeeProfile

class ProcurementStateMachine:
    @staticmethod
    def approve_step(procurement_id, role, user_uid, user_role=""):
        try:
            req = ProcurementRequest.objects.get(id=procurement_id)
        except ProcurementRequest.DoesNotExist:
            return False, "Request not found"

        if req.is_terminal:
            return False, "Request has reached terminal state"

        # Verify role designation
        user_role_upper = user_role.upper().strip()
        if role == 'HR' and user_role_upper not in ['HR', 'HR AND OPERATION HEAD']:
            return False, "Role validation failed: Only authorized HR personnel can sign this step."
        if role == 'CTO' and user_role_upper not in ['CTO', 'CITO']:
            return False, "Role validation failed: Only the CTO can sign this step."
        if role == 'COO' and user_role_upper != 'COO':
            return False, "Role validation failed: Only the COO can sign this step."
        if role == 'CEO' and user_role_upper != 'CEO':
            return False, "Role validation failed: Only the CEO can sign this step."

        # Check for segregation of duties violation (Sequential steps only)
        immediate_previous_actor = None
        if req.track == 'International':
            if role == 'HR': immediate_previous_actor = req.submitted_by_uid
            elif role == 'CTO': immediate_previous_actor = req.hr_approver_uid
            elif role == 'COO': immediate_previous_actor = req.cto_approver_uid
            elif role == 'CEO': immediate_previous_actor = req.coo_approver_uid
        elif req.track == 'Local':
            if role == 'HR': immediate_previous_actor = req.submitted_by_uid
            elif role == 'COO': immediate_previous_actor = req.hr_approver_uid
            
        if user_uid and user_uid == immediate_previous_actor:
            return False, "Segregation of duties violation: You cannot sign off on sequential workflow steps."

        if req.track == 'International':
            # Strict linear verification for International Track
            if role == 'HR':
                req.hr_approved = True
                req.hr_approver_uid = user_uid
            elif role == 'CTO':
                if not req.hr_approved: return False, "HR approval required first"
                req.cto_approved = True
                req.cto_approver_uid = user_uid
            elif role == 'COO':
                if not req.cto_approved: return False, "CTO approval required first"
                req.coo_approved = True
                req.coo_approver_uid = user_uid
            elif role == 'CEO':
                if not req.coo_approved: return False, "COO approval required first"
                req.ceo_approved = True
                req.ceo_approver_uid = user_uid
                req.is_terminal = True # Terminal switch
            else:
                return False, "Invalid role"
                
        elif req.track == 'Local':
            # Simpler flow for Local track
            if role == 'HR':
                req.hr_approved = True
                req.hr_approver_uid = user_uid
            elif role == 'COO':
                if not req.hr_approved: return False, "HR approval required first"
                req.coo_approved = True
                req.coo_approver_uid = user_uid
                req.is_terminal = True
            else:
                return False, "Role not applicable or invalid for Local track"

        req.save()
        return True, "Approved successfully"

import nepali_datetime
from datetime import timedelta
from .models import (
    EmployeeProfile, AttendanceRecord, LeaveRequest, 
    CalendarEvent, PayrollCycle, PayrollRecord
)

class PayrollComputationEngine:
    PAID_LEAVE_TRACKS = ['Casual', 'Sick', 'Maternity', 'Paternity', 'Mourning']

    @staticmethod
    def get_nepali_month_bounds(np_year, np_month):
        """Returns the total days, and Gregorian start/end dates for a Nepali month."""
        first_day_np = nepali_datetime.date(np_year, np_month, 1)
        next_month = np_month + 1
        next_year = np_year
        if next_month > 12:
            next_month = 1
            next_year += 1
            
        first_day_next_month_np = nepali_datetime.date(next_year, next_month, 1)
        days_in_month = first_day_next_month_np.toordinal() - first_day_np.toordinal()
        
        start_gregorian = first_day_np.to_datetime_date()
        end_gregorian = first_day_next_month_np.to_datetime_date() - timedelta(days=1)
        
        return days_in_month, start_gregorian, end_gregorian

    @staticmethod
    def count_weekends(start_date, end_date):
        """Counts Saturdays (Weekends) in the date range."""
        weekends = 0
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 5: # 5 is Saturday in Python datetime
                weekends += 1
            curr += timedelta(days=1)
        return weekends

    @classmethod
    def calculate_leaves_in_range(cls, employee_name, start_date, end_date, is_paid=True):
        """Calculates total leave days in the specific date range."""
        leaves = LeaveRequest.objects.filter(
            employee_name=employee_name,
            status='Approved',
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if is_paid:
            leaves = leaves.filter(leave_type__in=cls.PAID_LEAVE_TRACKS)
        else:
            leaves = leaves.exclude(leave_type__in=cls.PAID_LEAVE_TRACKS)
            
        total_days = 0
        for leave in leaves:
            # Clip leave dates to the current month's bounds
            overlap_start = max(start_date, leave.start_date)
            overlap_end = min(end_date, leave.end_date)
            if overlap_end >= overlap_start:
                total_days += (overlap_end - overlap_start).days + 1
        return total_days

    @classmethod
    def process_payroll_cycle(cls, np_year, np_month, users, is_final_calculation=False):
        """
        The Main Gateway Loop:
        - If is_final_calculation=False: Runs in Draft mode (Track Unpaid Leaves & Recalculate).
        - If is_final_calculation=True: Generates Records & Freezes the cycle.
        """
        # 1. Fetch Month Bounds
        days_in_month, start_greg, end_greg = cls.get_nepali_month_bounds(np_year, np_month)
        
        # 2. Weekends & Public/Emergency Holidays
        month_weekends = cls.count_weekends(start_greg, end_greg)
        month_holidays = CalendarEvent.objects.filter(date__range=[start_greg, end_greg]).count()
        
        if is_final_calculation:
            cycle, created = PayrollCycle.objects.get_or_create(np_year=np_year, np_month=np_month)
            if cycle.is_finalized:
                raise ValueError("This Payroll Cycle is already finalized and frozen.")
            # Clear old draft records if any
            PayrollRecord.objects.filter(cycle=cycle).delete()
        
        results = []
        for user in users:
            # Get Salary Info
            emp = EmployeeProfile.objects.filter(first_name__icontains=user.full_name.split(' ')[0]).first()
            base_salary = float(emp.base_gross_salary) if emp else 50000.0
            per_day_rate = base_salary / days_in_month
            
            # Present Days
            present_days = AttendanceRecord.objects.filter(
                employee_name=user.full_name,
                date__range=[start_greg, end_greg],
                status__in=['Present', 'Late']
            ).values('date').distinct().count()
            
            # Paid and Unpaid Leaves
            paid_leaves = cls.calculate_leaves_in_range(user.full_name, start_greg, end_greg, is_paid=True)
            unpaid_leaves = cls.calculate_leaves_in_range(user.full_name, start_greg, end_greg, is_paid=False)
            
            # Re-Engineered Calculation Engine
            # Total Paid Work Days = (Present Days) + (Weekends + Public Holidays + Emergency Holidays) + (Approved Paid Leaves)
            total_paid_work_days = present_days + month_weekends + month_holidays + paid_leaves
            
            # Failsafe: Cap at maximum days in month
            total_paid_work_days = min(total_paid_work_days, days_in_month)
            
            # Financial Computation
            gross_payable = total_paid_work_days * per_day_rate
            unpaid_deduction = unpaid_leaves * per_day_rate
            tax_deduction = gross_payable * 0.01  # Standard 1% SST
            net_payable = gross_payable - tax_deduction
            
            record_data = {
                'employee_name': user.full_name,
                'position': user.position,
                'present_days': present_days,
                'weekends': month_weekends,
                'holidays': month_holidays,
                'paid_leaves': paid_leaves,
                'unpaid_leaves': unpaid_leaves,
                'total_paid_work_days': total_paid_work_days,
                'base_salary': round(base_salary, 2),
                'gross_payable': round(gross_payable, 2),
                'unpaid_deduction': round(unpaid_deduction, 2),
                'tax_deduction': round(tax_deduction, 2),
                'net_payable': round(net_payable, 2),
            }
            
            if is_final_calculation:
                PayrollRecord.objects.create(
                    cycle=cycle,
                    employee=user,
                    present_days=present_days,
                    weekends=month_weekends,
                    holidays=month_holidays,
                    paid_leaves=paid_leaves,
                    unpaid_leaves=unpaid_leaves,
                    total_paid_days=total_paid_work_days,
                    gross_salary=gross_payable,
                    deductions=tax_deduction,
                    net_payable=net_payable
                )
            
            results.append(record_data)
            
        if is_final_calculation:
            cycle.is_finalized = True
            cycle.save()
            
        return results, days_in_month

from django.db import transaction
from .models import MoveOrder, InventoryLedger, OrgNode

class InventoryLogisticsEngine:
    
    @staticmethod
    def initiate_transfer(source_node, dest_node, sku_id, quantity, locator_type):
        """Step 1 & 2: Initiate Move Order and Enforce Locator Type."""
        order = MoveOrder(
            source_node=source_node,
            destination_node=dest_node,
            sku_id=sku_id,
            quantity=quantity,
            locator_type=locator_type,
            status='Draft'
        )
        # Will trigger the clean() method to validate HQ <-> Dealer rules
        order.full_clean()
        order.save()
        return order

    @staticmethod
    def dispatch_order(order_id):
        """Step 3: Dispatch & Checklist Verifications."""
        order = MoveOrder.objects.get(id=order_id)
        if not order.is_checklist_complete:
            raise ValueError("Dispatch Blocked: All checklist entities must be verified.")
            
        order.status = 'In_Transit'
        order.save()
        return order

    @staticmethod
    @transaction.atomic
    def receive_goods(order_id, goods_verified=True):
        """Step 4: Overhaul Receiving & Stock Adjustment Logic."""
        order = MoveOrder.objects.get(id=order_id)
        
        if order.status != 'In_Transit':
            raise ValueError("Order must be In-Transit to receive.")

        if not goods_verified:
            # Goods failed verification -> Route to Issue Report
            order.status = 'Issue_Report'
            order.save()
            return "Generated Issue Report. Workflow Paused."

        # Goods Verified (YES) -> Dual Stock Adjustment
        order.status = 'Goods_Verified'
        
        # 1. Deduct Stock from Sender (Stock Out)
        sender_stock = InventoryLedger.objects.select_for_update().get(
            node_id=order.source_node, 
            sku_id=order.sku_id,
            locator_bin_status=order.locator_type
        )
        if sender_stock.quantity_on_hand < order.quantity:
            raise ValueError("Insufficient stock in Source Node to complete transfer.")
        sender_stock.quantity_on_hand -= order.quantity
        sender_stock.save()

        # 2. Add Stock to Receiver (Stock In)
        receiver_stock, created = InventoryLedger.objects.select_for_update().get_or_create(
            node_id=order.destination_node,
            sku_id=order.sku_id,
            locator_bin_status=order.locator_type,
            defaults={'quantity_on_hand': 0, 'product_name': sender_stock.product_name}
        )
        receiver_stock.quantity_on_hand += order.quantity
        receiver_stock.save()

        order.status = 'Completed'
        order.save()
        return "Stock Adjustment Complete. Reached Inventory End."

class POSCheckoutService:
    
    @staticmethod
    @transaction.atomic
    def execute_sales_transaction(node, sku_id, quantity, locator_type):
        """
        Step 5: Execute Sales Transaction.
        Deducts quantity directly from the specified Locator Profile.
        """
        # 1. Validate Locator selection
        valid_locators = ['Fresh', 'Damaged', 'Refurbished', 'Repairable']
        if locator_type not in valid_locators:
            raise ValueError(f"Invalid Locator Type. Must be one of: {valid_locators}")

        # 2. Stock Deduction based on selected Locator
        try:
            stock = InventoryLedger.objects.select_for_update().get(
                node_id=node, 
                sku_id=sku_id, 
                locator_bin_status=locator_type
            )
        except InventoryLedger.DoesNotExist:
            raise ValueError(f"No stock found for {sku_id} in {locator_type} condition.")

        if stock.quantity_on_hand < quantity:
            raise ValueError(f"Insufficient {locator_type} stock for sale.")

        # Execute Deduction
        stock.quantity_on_hand -= quantity
        stock.save()
        
        # ... Proceed with creating AccountsReceivable invoice/receipt ...
        
        return "Sales Transaction Executed Successfully."


class ProcurementWorkflowEngine:
    
    @staticmethod
    def raise_requisition(user, title, track, product_sku, quantity):
        """Step 1: Branch Procurement Types & Access Roles."""
        active_role = user.position.upper()
        
        # Enforce Role Based Entry Points
        if track == 'Local' and 'FINANCE' not in active_role:
            raise ValueError("Local Procurement must be raised by the Finance Department.")
        if track == 'International' and active_role not in ['OPERATION HEAD', 'COO']:
            raise ValueError("International Procurement must be raised by Ops or COO.")
            
        from .models import ProcurementRequest
        req = ProcurementRequest.objects.create(
            title=title,
            track=track,
            product_sku=product_sku,
            requested_quantity=quantity,
            submitted_by_uid=user.uid,
            status='Pending_HR_COO' if track == 'Local' else 'Pending_CTO'
        )
        return req

    @staticmethod
    def local_review_gateway(req_id, hr_approved=False, coo_approved=False):
        """Step 2a: Dual-signoff Gateway for Local Procurement."""
        from .models import ProcurementRequest
        req = ProcurementRequest.objects.get(id=req_id)
        if req.track != 'Local':
            raise ValueError("Invalid operation for International track.")
            
        req.hr_approved = hr_approved
        req.coo_approved = coo_approved
        
        if hr_approved and coo_approved:
            req.status = 'Completed' # Forward for Local Procurement -> Process End
            # Notify Finance Dept
            # SystemNotification.objects.create(...)
        elif not hr_approved or not coo_approved:
            req.status = 'Closed' # Denied -> Requisition Closed
            
        req.save()
        return req.status

    @staticmethod
    def international_cto_review(req_id, is_approved, amend_qty=None):
        """Step 2b: CTO Review and Amend Quantity Loop."""
        from .models import ProcurementRequest
        req = ProcurementRequest.objects.get(id=req_id)
        if req.track != 'International':
            raise ValueError("Invalid operation for Local track.")
            
        if not is_approved:
            req.status = 'Closed'
            req.save()
            return "Requisition Closed"
            
        req.cto_approved = True
        if amend_qty is not None:
            req.amended_quantity = amend_qty
            
        req.status = 'Execution' # Progresses to System Integration & Execution
        req.save()
        return "Proceed to Procurement Execution"

    @staticmethod
    def integrate_lcm_post_execution(req_id, lcm_value):
        """Step 3: Integrate Landed Cost Matrix."""
        from .models import ProcurementRequest
        req = ProcurementRequest.objects.get(id=req_id)
        if req.status != 'Execution':
            raise ValueError("Must be in Execution phase to apply LCM.")
            
        req.landing_cost_management = lcm_value
        req.status = 'Pending_GRN'
        req.save()
        return "LCM Integrated. Ready for GRN Intake."

    @staticmethod
    @transaction.atomic
    def process_grn_and_serialize(req_id, hq_node, serialized_payload):
        """
        Step 4: Automate Serialized GRN Logic & Stock Locators
        serialized_payload expects a list of dicts: [{'serial': 'S001', 'locator': 'Fresh'}, ...]
        """
        from .models import ProcurementRequest, ProcurementItem, InventoryLedger
        req = ProcurementRequest.objects.get(id=req_id)
        if req.status != 'Pending_GRN':
            raise ValueError("Request is not ready for GRN Intake.")
            
        final_qty = req.amended_quantity if req.amended_quantity else req.requested_quantity
        if len(serialized_payload) != final_qty:
            raise ValueError(f"GRN mismatch. Expected {final_qty} items, received {len(serialized_payload)}.")

        # 1. Store Serialized Items
        for item_data in serialized_payload:
            ProcurementItem.objects.create(
                request=req,
                serial_number=item_data['serial'],
                locator=item_data['locator'].capitalize(), # 'Fresh', 'Damaged', 'Basiade'
                is_integrated=True
            )
            
            # 2. Final System Integration: Auto-add to InventoryLedger Locators
            ledger, created = InventoryLedger.objects.select_for_update().get_or_create(
                node_id=hq_node,
                sku_id=req.product_sku,
                locator_bin_status=item_data['locator'].capitalize(),
                defaults={'quantity_on_hand': 0, 'product_name': req.title, 'price': req.landing_cost_management}
            )
            ledger.quantity_on_hand += 1
            # If price was updated by LCM, we might average it out here. 
            # For strict mirroring, we just save the updated stock count.
            ledger.save()
            
        req.status = 'Completed' # Process End
        req.save()
        return "GRN Processed and Serially Integrated successfully."
