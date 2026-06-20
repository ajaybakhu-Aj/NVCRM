from decimal import Decimal
import calendar
from datetime import date
from .models import ProcurementRequest, EmployeeProfile

class ProcurementStateMachine:
    @staticmethod
    def approve_step(procurement_id, role):
        try:
            req = ProcurementRequest.objects.get(id=procurement_id)
        except ProcurementRequest.DoesNotExist:
            return False, "Request not found"

        if req.is_terminal:
            return False, "Request has reached terminal state"

        if req.track == 'International':
            # Strict linear verification for International Track
            if role == 'HR':
                req.hr_approved = True
            elif role == 'CTO':
                if not req.hr_approved: return False, "HR approval required first"
                req.cto_approved = True
            elif role == 'COO':
                if not req.cto_approved: return False, "CTO approval required first"
                req.coo_approved = True
            elif role == 'CEO':
                if not req.coo_approved: return False, "COO approval required first"
                req.ceo_approved = True
                req.is_terminal = True # Terminal switch
            else:
                return False, "Invalid role"
                
        elif req.track == 'Local':
            # Simpler flow for Local track
            if role == 'HR':
                req.hr_approved = True
            elif role == 'COO':
                if not req.hr_approved: return False, "HR approval required first"
                req.coo_approved = True
                req.is_terminal = True
            else:
                return False, "Role not applicable or invalid for Local track"

        req.save()
        return True, "Approved successfully"

class PayrollComputationEngine:
    @staticmethod
    def compute_payroll(employee_id, year, month):
        try:
            emp = EmployeeProfile.objects.get(id=employee_id)
        except EmployeeProfile.DoesNotExist:
            return None

        # Basic = Gross * 0.60
        basic_salary = emp.base_gross_salary * Decimal('0.60')
        # DA = Gross * 0.40
        da_component = emp.base_gross_salary * Decimal('0.40')
        
        # Dynamic days in month
        _, days_in_month = calendar.monthrange(year, month)
        
        per_day_basic = basic_salary / days_in_month
        per_day_da = da_component / days_in_month
        
        # Here we could implement multi-tier tax bracket based on `marital_status`
        # Simple representation:
        tax_rate = Decimal('0.01') if emp.marital_status else Decimal('0.02')
        tax_deduction = emp.base_gross_salary * tax_rate

        return {
            'gross_salary': emp.base_gross_salary,
            'basic_salary': basic_salary,
            'da_component': da_component,
            'days_in_month': days_in_month,
            'per_day_basic': per_day_basic,
            'per_day_da': per_day_da,
            'tax_deduction': tax_deduction,
            'net_salary': emp.base_gross_salary - tax_deduction
        }
