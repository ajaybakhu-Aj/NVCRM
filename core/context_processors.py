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
    pending_procurements = ProcurementRequest.objects.exclude(status__in=['Completed', 'Closed'])
    if active_role == 'HR':
        pending_procurements = pending_procurements.filter(status='Pending_HR_COO', track='Local')
    elif active_role == 'CTO':
        pending_procurements = pending_procurements.filter(status='Pending_CTO', track='International')
    elif active_role == 'COO':
        pending_procurements = pending_procurements.filter(status='Pending_HR_COO', track='Local')
    else:
        pending_procurements = pending_procurements.none()
        
    procurement_count = pending_procurements.count()
    total_count = pending_leaves + procurement_count
    
    # Fetch notifications for this user
    recent_notifications = []
    unread_count = 0
    if system_user:
        recent_notifications = SystemNotification.objects.filter(recipient=system_user).order_by('-created_at')[:7]
        unread_count = SystemNotification.objects.filter(recipient=system_user, is_read=False).count()

    return {
        'pending_approvals_count': total_count,
        'pending_leaves_count': pending_leaves,
        'pending_procurements_count': procurement_count,
        'system_user': system_user,
        'active_role_upper': active_role.upper() if active_role else '',
        'recent_notifications': recent_notifications,
        'unread_notifications_count': unread_count
    }
