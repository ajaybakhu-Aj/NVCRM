from django.urls import path
from .views import account_expenses, export_expenses_excel, DashboardView, AttendanceCheckinView, InventoryListView, UserCreateView, NoticeBoardView, LeaveListView, LeadPipelineView, ProcurementView, AccountsReceivableView, SwitchRoleView, LoginView, LogoutView, POSView, POSCheckoutView, POSInvoiceView, StaffPayrollReportView, ProjectTaskBoardView, SystemLogView, SystemLogExcelView, NoticePollView, LeadReportExcelView

urlpatterns = [
    path('system-log/', SystemLogView.as_view(), name='system_log'),
    path('system-log/export/', SystemLogExcelView.as_view(), name='system_log_excel'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('pos/', POSView.as_view(), name='pos'),
    path('pos/checkout/', POSCheckoutView.as_view(), name='pos_checkout'),
    path('pos/invoice/', POSInvoiceView.as_view(), name='pos_invoice'),
    path('', DashboardView.as_view(), name='dashboard'),
    path('attendance/', AttendanceCheckinView.as_view(), name='attendance_checkin'),
    path('inventory/', InventoryListView.as_view(), name='inventory_list'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('notice-board/', NoticeBoardView.as_view(), name='notice_board'),
    path('leave/', LeaveListView.as_view(), name='leave_list'),
    path('leads/', LeadPipelineView.as_view(), name='lead_pipeline'),
    path('leads/report/excel/', LeadReportExcelView.as_view(), name='lead_report_excel'),
    path('procurement/', ProcurementView.as_view(), name='procurement_list'),
    path('accounts-receivable/', AccountsReceivableView.as_view(), name='accounts_receivable'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch_role'),
    path('attendance-payroll-report/', StaffPayrollReportView.as_view(), name='attendance_payroll_report'),
    path('task-board/', ProjectTaskBoardView.as_view(), name='task_board'),
    path('api/poll-notices/', NoticePollView.as_view(), name='poll_notices'),
    path('expenses/', account_expenses, name='account_expenses'),
    path('expenses/export/excel/', export_expenses_excel, name='export_expenses_excel'),
]
