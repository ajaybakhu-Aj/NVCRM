from core.models import LeaveRequest, ProcurementRequest, SystemUserProfile

def pending_approvals(request):
    uid = request.session.get('logged_in_uid')
    if not uid:
        return {'pending_approvals_count': 0, 'pending_leaves_count': 0, 'pending_procurements_count': 0, 'system_user': None}
    
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

    return {
        'pending_approvals_count': total_count,
        'pending_leaves_count': pending_leaves,
        'pending_procurements_count': procurement_count,
        'system_user': system_user
    }
