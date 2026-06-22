from core.models import LeaveRequest, ProcurementRequest, SystemUserProfile, SystemNotification

def pending_approvals(request):
    uid = request.session.get('logged_in_uid')
    if not uid:
        return {'pending_approvals_count': 0, 'pending_leaves_count': 0, 'pending_procurements_count': 0, 'system_user': None, 'unread_notifications': []}
    
    system_user = SystemUserProfile.objects.filter(uid=uid).first()
    active_role = request.session.get('active_role', '')
    
    # Calculate pending leaves (All managers can see pending leaves)
    if active_role != 'Staff':
        pending_leaves = LeaveRequest.objects.filter(status='Pending').count()
    else:
        pending_leaves = 0
    
    # Calculate pending procurements based on specific approval tracks
    pending_procurements = ProcurementRequest.objects.filter(is_terminal=False)
    if active_role == 'HR':
        pending_procurements = pending_procurements.filter(hr_approved=False)
    elif active_role == 'CTO':
        pending_procurements = pending_procurements.filter(hr_approved=True, cto_approved=False)
    elif active_role == 'COO':
        pending_procurements = pending_procurements.filter(cto_approved=True, coo_approved=False)
    elif active_role == 'CEO':
        pending_procurements = pending_procurements.filter(coo_approved=True, ceo_approved=False)
    else:
        pending_procurements = pending_procurements.none()
        
    procurement_count = pending_procurements.count()
    total_count = pending_leaves + procurement_count
    
    # Fetch notifications for this user
    unread_notifications = []
    if system_user:
        unread_notifications = SystemNotification.objects.filter(recipient=system_user, is_read=False).order_by('-created_at')

    return {
        'pending_approvals_count': total_count,
        'pending_leaves_count': pending_leaves,
        'pending_procurements_count': procurement_count,
        'system_user': system_user,
        'unread_notifications': unread_notifications,
        'unread_notifications_count': len(unread_notifications) if system_user else 0
    }
