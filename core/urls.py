from django.urls import path
from .views import DashboardView, AttendanceCheckinView, InventoryListView, UserCreateView, NoticeBoardView, LeaveListView, LeadPipelineView, ProcurementView, AccountsReceivableView, SwitchRoleView, LoginView, LogoutView, POSView, POSCheckoutView, POSInvoiceView

urlpatterns = [
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
    path('procurement/', ProcurementView.as_view(), name='procurement_list'),
    path('accounts-receivable/', AccountsReceivableView.as_view(), name='accounts_receivable'),
    path('switch-role/', SwitchRoleView.as_view(), name='switch_role'),
]
