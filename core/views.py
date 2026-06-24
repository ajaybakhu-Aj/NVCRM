from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib import messages
import calendar
from datetime import date, datetime
from .models import CalendarEvent

class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        now = datetime.now()
        import nepali_datetime
        from .nepali_calendar import get_nepali_monthdatescalendar
        
        today_np = nepali_datetime.date.today()
        year = int(request.GET.get('year', today_np.year))
        month = int(request.GET.get('month', today_np.month))

        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1

        # Check for initial deployment events
        if not CalendarEvent.objects.exists():
            CalendarEvent.objects.create(title="[HOLIDAY] Republic Day", date=date(2026, 5, 28), description="National Holiday")
            CalendarEvent.objects.create(title="[HOLIDAY] Dashain", date=date(2026, 10, 15), description="Festival Holiday")
            CalendarEvent.objects.create(title="CTO Review", date=date(2026, 6, 3), description="Quarterly tech audit")
            CalendarEvent.objects.create(title="Inventory Audit", date=date(2026, 6, 10), description="HQ Stock Verification")
            CalendarEvent.objects.create(title="Payroll Sync", date=date(2026, 6, 19), description="June salaries sign-off")
            CalendarEvent.objects.create(title="System Patch", date=date(2026, 6, 25), description="Core ERP upgrade")

        weeks = get_nepali_monthdatescalendar(year, month)

        start_date = weeks[0][0]
        end_date = weeks[-1][-1]
        events = CalendarEvent.objects.filter(date__range=(start_date, end_date))

        events_by_date = {}
        for event in events:
            events_by_date.setdefault(event.date, []).append(event)

        formatted_weeks = []
        for week in weeks:
            formatted_week = []
            for day in week:
                day_np = nepali_datetime.date.from_datetime_date(day)
                is_current_month = (day_np.month == month)
                is_today = (day == now.date())
                day_events = events_by_date.get(day, [])
                is_holiday = any('[HOLIDAY]' in e.title for e in day_events)
                formatted_week.append({
                    'date': day,
                    'day_num': day_np.day, # Use Nepali day for rendering
                    'is_current_month': is_current_month,
                    'is_today': is_today,
                    'events': day_events,
                    'is_holiday': is_holiday
                })
            formatted_weeks.append(formatted_week)

        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1

        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        # Nepali month names
        np_months = ["Baisakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin", "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"]
        month_name = np_months[month - 1]
        
        # Calculate Dashboard Activity (Leaves & Missing Attendance)
        from .models import LeaveRequest, AttendanceRecord, SystemUserProfile
        today = now.date()
        
        on_leave_today = LeaveRequest.objects.filter(
            status='Approved',
            start_date__lte=today,
            end_date__gte=today
        )
        
        attended_names = AttendanceRecord.objects.filter(date=today).values_list('employee_name', flat=True)
        on_leave_names = on_leave_today.values_list('employee_name', flat=True)
        
        all_users = SystemUserProfile.objects.exclude(full_name__in=list(on_leave_names))
        attendance_status = []
        for user in all_users:
            has_checked_in = user.full_name in list(attended_names)
            attendance_status.append({
                'user': user,
                'has_checked_in': has_checked_in
            })

        active_role = request.session.get('active_role', '')
        is_remote_allowed = active_role.upper() in ['SALES', 'IT', 'IT TEAM']

        logged_in_name = request.session.get('logged_in_name', 'John Doe')
        today_record = AttendanceRecord.objects.filter(employee_name=logged_in_name, date=today).first()
        is_checked_in = False
        is_checked_out = False
        if today_record:
            if today_record.check_in_time:
                is_checked_in = True
            if today_record.check_out_time:
                is_checked_out = True

        context = {
            'weeks': formatted_weeks,
            'year': year,
            'month': month,
            'month_name': month_name,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'on_leave_today': on_leave_today,
            'attendance_status': attendance_status,
            'is_remote_allowed': is_remote_allowed,
            'is_checked_in': is_checked_in,
            'is_checked_out': is_checked_out,
            'today_record': today_record,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'delete_event':
            active_role = request.session.get('active_role', '')
            if active_role in ['CEO', 'COO', 'HR', 'Operation Head', 'CITO']:
                event_id = request.POST.get('event_id')
                if event_id:
                    CalendarEvent.objects.filter(id=event_id).delete()
            year = request.POST.get('year', request.GET.get('year', ''))
            month = request.POST.get('month', request.GET.get('month', ''))
            url = '/'
            if year and month:
                url += f'?year={year}&month={month}'
            return redirect(url)

        title = request.POST.get('title')
        description = request.POST.get('description', '')
        date_str = request.POST.get('date')
        is_holiday = request.POST.get('is_holiday') == 'on'
        
        if title and is_holiday:
            title = f"[HOLIDAY] {title}"

        if title and date_str:
            try:
                import nepali_datetime
                # Parse the incoming Nepali date (YYYY-MM-DD)
                year_part, month_part, day_part = map(int, date_str.split('-'))
                np_date = nepali_datetime.date(year_part, month_part, day_part)
                # Convert to standard Gregorian date for database storage
                event_date = np_date.to_datetime_date()
                
                CalendarEvent.objects.create(
                    title=title,
                    description=description,
                    date=event_date
                )
            except (ValueError, TypeError):
                pass

        if action == 'check_in_out':
            from .models import AttendanceRecord
            from datetime import date, datetime, time
            logged_in_name = request.session.get('logged_in_name', 'John Doe')
            lat_str = request.POST.get('latitude')
            lng_str = request.POST.get('longitude')
            today = date.today()
            now = datetime.now()
            current_time = now.time()

            lat = None
            lng = None
            if lat_str and lng_str:
                try:
                    lat = float(lat_str)
                    lng = float(lng_str)
                except ValueError:
                    pass

            cutoff_time = time(9, 30, 0)
            status = 'Present'
            if current_time > cutoff_time:
                status = 'Late'

            record, created = AttendanceRecord.objects.get_or_create(
                employee_name=logged_in_name,
                date=today,
                defaults={
                    'check_in_time': current_time,
                    'status': status,
                    'latitude': lat,
                    'longitude': lng
                }
            )

            if not created and not record.check_out_time:
                record.check_out_time = current_time
                record.save()

            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'checked_in': record.check_in_time is not None,
                'checked_out': record.check_out_time is not None,
                'check_in_time': record.check_in_time.strftime('%I:%M %p') if record.check_in_time else '',
                'check_out_time': record.check_out_time.strftime('%I:%M %p') if record.check_out_time else '',
                'status': record.status
            })

        year = request.POST.get('year', '')
        month = request.POST.get('month', '')
        url = '/'
        if year and month:
            url += f'?year={year}&month={month}'
        return redirect(url)

from .models import LeaveRequest, AttendanceRecord
import calendar
from datetime import date, datetime, time

class AttendanceCheckinView(TemplateView):
    template_name = "attendance_checkin.html"

    def get(self, request, *args, **kwargs):
        # Pre-populate simulated attendance history for the user for the current month if empty
        logged_in_name = request.session.get('logged_in_name', 'John Doe')
        today = date.today()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))

        if not AttendanceRecord.objects.filter(employee_name=logged_in_name).exists():
            # Populate some days in June 2026 (or current month)
            for d in range(1, 19):
                day_date = date(2026, 6, d)
                weekday = day_date.weekday()
                if weekday != 5: # Sunday - Friday (Saturday is weekend)
                    # Randomize a bit: Present or Late
                    if d == 12:
                        AttendanceRecord.objects.create(
                            employee_name=logged_in_name,
                            date=day_date,
                            check_in_time=time(9, 45, 0),
                            check_out_time=time(17, 30, 0),
                            status="Late",
                            latitude=27.6773098,
                            longitude=85.3979076
                        )
                    elif d == 15:
                        AttendanceRecord.objects.create(
                            employee_name=logged_in_name,
                            date=day_date,
                            status="Leave"
                        )
                    else:
                        AttendanceRecord.objects.create(
                            employee_name=logged_in_name,
                            date=day_date,
                            check_in_time=time(8, 55, 0),
                            check_out_time=time(17, 0, 0),
                            status="Present",
                            latitude=27.6773098,
                            longitude=85.3979076
                        )

        # Generate month grid
        cal = calendar.Calendar(firstweekday=6) # starts on Sunday
        month_days = list(cal.itermonthdays2(year, month))

        # Fetch records for selected month
        records = AttendanceRecord.objects.filter(
            employee_name=logged_in_name,
            date__year=year,
            date__month=month
        )
        records_by_day = {r.date.day: r for r in records}

        # Calculate statistics
        total_present = records.filter(status='Present').count()
        total_late = records.filter(status='Late').count()
        total_leave = records.filter(status='Leave').count()
        total_absent = records.filter(status='Absent').count()

        # Build grid list
        formatted_weeks = []
        current_week = []
        for day, col in month_days:
            if day == 0:
                current_week.append({
                    'day': '',
                    'record': None,
                    'is_today': False,
                    'is_weekend': False
                })
            else:
                day_date = date(year, month, day)
                is_weekend = col == 5 # Saturday=5 only
                record = records_by_day.get(day)
                is_today = (day_date == today)

                current_week.append({
                    'day': day,
                    'record': record,
                    'is_today': is_today,
                    'is_weekend': is_weekend
                })

            if len(current_week) == 7:
                formatted_weeks.append(current_week)
                current_week = []
        if current_week:
            while len(current_week) < 7:
                current_week.append({
                    'day': '',
                    'record': None,
                    'is_today': False,
                    'is_weekend': False
                })
            formatted_weeks.append(current_week)

        # Date Nav variables
        month_name = calendar.month_name[month]
        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        next_month = month + 1
        next_year = year
        if next_month == 13:
            next_month = 1
            next_year -= 1

        active_role = request.session.get('active_role', '')
        is_remote_allowed = active_role.upper() in ['SALES', 'IT', 'IT TEAM']

        # Determine check-in/out status for today
        today_record = AttendanceRecord.objects.filter(employee_name=logged_in_name, date=today).first()
        is_checked_in = False
        is_checked_out = False
        if today_record:
            if today_record.check_in_time:
                is_checked_in = True
            if today_record.check_out_time:
                is_checked_out = True

        context = {
            'weeks': formatted_weeks,
            'year': year,
            'month': month,
            'month_name': month_name,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'total_present': total_present,
            'total_late': total_late,
            'total_leave': total_leave,
            'total_absent': total_absent,
            'today': today,
            'is_remote_allowed': is_remote_allowed,
            'is_checked_in': is_checked_in,
            'is_checked_out': is_checked_out,
            'today_record': today_record,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        logged_in_name = request.session.get('logged_in_name', 'John Doe')
        lat_str = request.POST.get('latitude')
        lng_str = request.POST.get('longitude')
        today = date.today()
        now = datetime.now()
        current_time = now.time()

        lat = None
        lng = None
        if lat_str and lng_str:
            try:
                lat = float(lat_str)
                lng = float(lng_str)
            except ValueError:
                pass

        cutoff_time = time(9, 30, 0)
        status = 'Present'
        if current_time > cutoff_time:
            status = 'Late'

        record, created = AttendanceRecord.objects.get_or_create(
            employee_name=logged_in_name,
            date=today,
            defaults={
                'check_in_time': current_time,
                'status': status,
                'latitude': lat,
                'longitude': lng
            }
        )

        if not created and not record.check_out_time:
            record.check_out_time = current_time
            record.save()

        from django.http import JsonResponse
        return JsonResponse({
            'success': True,
            'checked_in': record.check_in_time is not None,
            'checked_out': record.check_out_time is not None,
            'check_in_time': record.check_in_time.strftime('%I:%M %p') if record.check_in_time else '',
            'check_out_time': record.check_out_time.strftime('%I:%M %p') if record.check_out_time else '',
            'status': record.status
        })

class InventoryListView(TemplateView):
    template_name = "inventory_list.html"
    
    def get(self, request, *args, **kwargs):
        from .models import InventoryLedger, AccountsReceivable
        inventory = InventoryLedger.objects.all().order_by('-created_at')
        accounts = AccountsReceivable.objects.all().order_by('-created_at')[:5]
        return render(request, self.template_name, {
            'inventory': inventory,
            'accounts': accounts
        })
        
    def post(self, request, *args, **kwargs):
        from .models import InventoryLedger, OrgNode
        action = request.POST.get('action')
        
        if action == 'add_stock':
            sku_id = request.POST.get('sku_id')
            product_name = request.POST.get('product_name')
            price = request.POST.get('price')
            quantity = request.POST.get('quantity')
            bin_status = request.POST.get('locator_bin_status', 'Fresh')
            product_image = request.FILES.get('product_image')
            
            hq_node = OrgNode.objects.filter(node_type='HQ').first()
            if not hq_node:
                hq_node = OrgNode.objects.create(name="HQ-NEPAL", node_type="HQ")
                
            InventoryLedger.objects.create(
                sku_id=sku_id,
                product_name=product_name,
                price=price,
                quantity_on_hand=quantity,
                locator_bin_status=bin_status,
                node_id=hq_node,
                product_image=product_image
            )
            from django.contrib import messages
            messages.success(request, f"Successfully added {quantity} units of {product_name} to inventory.")
            
        return redirect('inventory_list')

from .models import SystemUserProfile

class UserCreateView(TemplateView):
    template_name = "user_create.html"

    def get(self, request, *args, **kwargs):
        # Auto pre-populate the 4 roles if empty
        if not SystemUserProfile.objects.exists():
            SystemUserProfile.objects.create(
                full_name="Rojil Thapa",
                position="CEO",
                profile_image="https://lh3.googleusercontent.com/aida-public/AB6AXuAxRwBqcBsIwhl8UfYuUmsQHvIz1o1r9OuPPywbOtlGXWlCR_nVlogNz1dWjHxbbR8D4JRp6xcnJNC-9wb-yTw4b0zCNhB4X2AYyTeqO9RSpOO2DlQq6-bWMWXr3BYnulb9WcLu3g_1_7WBjKHzPfS1wtbtw9TNLG4uNGiafbzvLA8kbIQtntZeSPb1stxr6gciJC4rA8CwhZUk9JLERRW8332qacALyXCTp9poQmehlr-eWspkIhqdUrJlvlr45Z3nBmWrNROkitA",
                node="HQ-NEPAL",
                pan_number="601122334",
                citizenship_number="27-01-72-99881",
                contact_number="+977-9851011223",
                email="rojil@nightvision.com.np",
                address="Kathmandu, Nepal",
                global_telemetry=True,
                ledger_override=True,
                api_key_gen=True,
                audit_log_purge=True,
                hr_matrix_view=True,
                fleet_command=True,
                can_access_profiles=True,
                can_access_lead_pipeline=True,
                can_access_inventory=True,
                can_access_accounts_receivable=True,
                can_access_pos=True,
                can_access_procurement=True
            )
            SystemUserProfile.objects.create(
                full_name="Ajay Bakhunchhe",
                position="CITO",
                profile_image="https://lh3.googleusercontent.com/aida-public/AB6AXuBs4lExNu2CzthZ9OvocXvEmbE3wXd1duo2qcQxQWFi1H3SjSgQPj1DiBb_Ct1nt7uQQsYoaMn2hteSpaPGXY83PKQXkfY-MHerms63L1zc8b71EJDM68-NCxLo33P2OaJ-MZBD_UhONo8mArPudj7a4QCtUIDrwjg2tFJothkcyey2MH2npu5ak2u5DowyJ-Qopkd6HlZ02nU7VZc1NzQCvruFJSoJyKS617KiHgPaiM20GWpTzw4wjI6Ry7pWM_1XE8ojwjonNyU",
                node="HQ-NEPAL",
                pan_number="602233445",
                citizenship_number="27-01-74-88772",
                contact_number="+977-9851022334",
                email="ajay@nightvision.com.np",
                address="Lalitpur, Nepal",
                global_telemetry=True,
                ledger_override=False,
                api_key_gen=True,
                audit_log_purge=True,
                hr_matrix_view=False,
                fleet_command=True,
                can_access_profiles=True,
                can_access_lead_pipeline=True,
                can_access_inventory=True,
                can_access_accounts_receivable=True,
                can_access_pos=True,
                can_access_procurement=True
            )
            SystemUserProfile.objects.create(
                full_name="Manjil Deuja",
                position="COO",
                profile_image="https://lh3.googleusercontent.com/aida-public/AB6AXuDWIAfodMQAXvKiYJy0D3dKaJM90Y83Tr-GC7hDuyN3qCB0yTqKnLuDstAPHjM0wwVSGazyg8CcsFcQ1hHACzcemG4TZ9uolATIn0Dn9j0Ua4hPmEwCljlUW6MQcop18cIyvYknO0jevfZHPeoS2Ax32DYkBi8-fdaKBtjVZq8FbvG2pbYcgIis8PDZI4LkiQkC01y56-3BhHabvA8mA5NoIElPYdRJs8lgQjNJg9CsRoDuKtYIesv8UOyJUfTfzFskb5ia0Z_dMHU",
                node="HQ-NEPAL",
                pan_number="603344556",
                citizenship_number="27-01-76-77663",
                contact_number="+977-9851033445",
                email="manjil@nightvision.com.np",
                address="Bhaktapur, Nepal",
                global_telemetry=True,
                ledger_override=True,
                api_key_gen=False,
                audit_log_purge=False,
                hr_matrix_view=True,
                fleet_command=True,
                can_access_profiles=True,
                can_access_lead_pipeline=True,
                can_access_inventory=True,
                can_access_accounts_receivable=True,
                can_access_pos=True,
                can_access_procurement=True
            )
            SystemUserProfile.objects.create(
                full_name="Hemanta Mahato",
                position="HR and Operation Head",
                profile_image="https://lh3.googleusercontent.com/aida-public/AB6AXuAVDI2iFpujCL_v3DHDuqdNMFY7p4wtgmzwORSUfv0PapsXSmFDOi4AUHB2lVdjX-JUWZaSbslLRCw-6ClmiJyxgMxcPwSfu2dLNPoCEiN2ouO5wsu9qOwgI5RljBwvQvtFoEjWRfrh_zJixxJaDH3D2AB4fEOi9_cvcfq4ybvBoRjgIBwnjIkWsKEr-NAalgRTBpnbgNgWocmp8qJKR5YrjjUHAhmcclkDIT4pETOpZalJP8DC2UYsqoi0rLPSjkkhA6squGCp88k",
                node="HQ-NEPAL",
                pan_number="604455667",
                citizenship_number="27-01-78-66554",
                contact_number="+977-9851044556",
                email="hemanta@nightvision.com.np",
                address="Kirtipur, Nepal",
                global_telemetry=True,
                ledger_override=False,
                api_key_gen=False,
                audit_log_purge=False,
                hr_matrix_view=True,
                fleet_command=True,
                can_access_profiles=True,
                can_access_lead_pipeline=True,
                can_access_inventory=True,
                can_access_accounts_receivable=True,
                can_access_pos=True,
                can_access_procurement=True
            )

        users = SystemUserProfile.objects.all().order_by('created_at')
        selected_uid = request.GET.get('uid')
        
        # Restriction for Staff
        active_role = request.session.get('active_role')
        if active_role == 'Staff':
            logged_in_uid = request.session.get('logged_in_uid')
            if selected_uid and selected_uid != logged_in_uid:
                return redirect(f'/users/create/?uid={logged_in_uid}')
            users = users.filter(uid=logged_in_uid)
            selected_uid = logged_in_uid

        selected_user = None

        if selected_uid:
            selected_user = users.filter(uid=selected_uid).first()
        if not selected_user:
            selected_user = users.first()

        context = {
            'users': users,
            'selected_user': selected_user,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        uid = request.POST.get('uid')

        active_role = request.session.get('active_role')
        if active_role == 'Staff':
            if action != 'update' or uid != request.session.get('logged_in_uid'):
                return redirect(f"/users/create/?uid={request.session.get('logged_in_uid')}&error=unauthorized")

        if action == 'create':
            full_name = request.POST.get('full_name')
            position = request.POST.get('position')
            node = request.POST.get('node', 'HQ-NEPAL')
            password = request.POST.get('password', 'Admin')
            profile_image_input = request.POST.get('profile_image')
            
            pan_number = request.POST.get('pan_number', '')
            citizenship_number = request.POST.get('citizenship_number', '')
            contact_number = request.POST.get('contact_number', '')
            email = request.POST.get('email', '')
            address = request.POST.get('address', '')
            
            gender = request.POST.get('gender', 'Male')
            educational_qualifications = request.POST.get('educational_qualifications')
            languages_known = request.POST.get('languages_known')
            proficiency_level = request.POST.get('proficiency_level')

            # Read toggles
            global_telemetry = request.POST.get('global_telemetry') == 'true'
            ledger_override = request.POST.get('ledger_override') == 'true'
            api_key_gen = request.POST.get('api_key_gen') == 'true'
            audit_log_purge = request.POST.get('audit_log_purge') == 'true'
            hr_matrix_view = request.POST.get('hr_matrix_view') == 'true'
            fleet_command = request.POST.get('fleet_command') == 'true'

            # File Upload Handling
            profile_image = None
            profile_image_file = request.FILES.get('profile_image_file')
            if profile_image_file:
                from django.core.files.storage import FileSystemStorage
                fs = FileSystemStorage()
                filename = fs.save('avatars/' + profile_image_file.name, profile_image_file)
                profile_image = fs.url(filename)
            elif profile_image_input:
                profile_image = profile_image_input
            else:
                avatars = [
                    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80",
                    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
                    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&q=80",
                    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&q=80"
                ]
                import random
                profile_image = random.choice(avatars)

            # Assign all page accesses by default to high-level roles
            is_senior = position.upper() in ['CEO', 'CITO', 'COO', 'HR AND OPERATION HEAD', 'ADMIN', 'SYSTEM ADMIN', 'HR', 'OPERATION HEAD']

            user = SystemUserProfile.objects.create(
                full_name=full_name,
                position=position,
                node=node,
                password=password,
                profile_image=profile_image,
                pan_number=pan_number,
                citizenship_number=citizenship_number,
                contact_number=contact_number,
                email=email,
                address=address,
                gender=gender,
                educational_qualifications=educational_qualifications,
                languages_known=languages_known,
                proficiency_level=proficiency_level,
                global_telemetry=global_telemetry,
                ledger_override=ledger_override,
                api_key_gen=api_key_gen,
                audit_log_purge=audit_log_purge,
                hr_matrix_view=hr_matrix_view,
                fleet_command=fleet_command,
                can_access_dashboard=request.POST.get('can_access_dashboard') == 'true' if 'can_access_dashboard' in request.POST else True,
                can_access_notice_board=request.POST.get('can_access_notice_board') == 'true' if 'can_access_notice_board' in request.POST else True,
                can_access_time_attendance=request.POST.get('can_access_time_attendance') == 'true' if 'can_access_time_attendance' in request.POST else True,
                can_access_leave=request.POST.get('can_access_leave') == 'true' if 'can_access_leave' in request.POST else True,
                can_access_profiles=request.POST.get('can_access_profiles') == 'true' if 'can_access_profiles' in request.POST else is_senior,
                can_access_lead_pipeline=request.POST.get('can_access_lead_pipeline') == 'true' if 'can_access_lead_pipeline' in request.POST else is_senior,
                can_access_inventory=request.POST.get('can_access_inventory') == 'true' if 'can_access_inventory' in request.POST else is_senior,
                can_access_accounts_receivable=request.POST.get('can_access_accounts_receivable') == 'true' if 'can_access_accounts_receivable' in request.POST else is_senior,
                can_access_pos=request.POST.get('can_access_pos') == 'true' if 'can_access_pos' in request.POST else is_senior,
                can_access_procurement=request.POST.get('can_access_procurement') == 'true' if 'can_access_procurement' in request.POST else is_senior,
            )
            
            if user.gender == 'Female':
                from .models import CalendarEvent, LeaveRequest
                female_holidays = CalendarEvent.objects.filter(is_female_holiday=True)
                for fh in female_holidays:
                    LeaveRequest.objects.get_or_create(
                        employee_name=user.full_name,
                        leave_type='Casual',
                        start_date=fh.date,
                        end_date=fh.date,
                        defaults={
                            'reason': f'Female Holiday: {fh.title}',
                            'status': 'Approved'
                        }
                    )
            
            return redirect(f'/users/create/?uid={user.uid}')

        elif action == 'update':
            import os
            from django.conf import settings
            from django.core.files.storage import FileSystemStorage
            uid = request.POST.get('uid')
            user = SystemUserProfile.objects.filter(uid=uid).first()
            if user:
                old_name = user.full_name
                user.full_name = request.POST.get('full_name', user.full_name)
                user.position = request.POST.get('position', user.position)
                user.node = request.POST.get('node', user.node)
                
                password = request.POST.get('password', '').strip()
                if password:
                    user.password = password
                    
                profile_image_file = request.FILES.get('profile_image_file')
                if profile_image_file:
                    fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'profiles'))
                    filename = fs.save(profile_image_file.name, profile_image_file)
                    user.profile_image = fs.url(filename)
                else:
                    user.profile_image = request.POST.get('profile_image', user.profile_image)
                
                user.pan_number = request.POST.get('pan_number', user.pan_number)
                user.citizenship_number = request.POST.get('citizenship_number', user.citizenship_number)
                user.contact_number = request.POST.get('contact_number', user.contact_number)
                user.email = request.POST.get('email', user.email)
                user.address = request.POST.get('address', user.address)
                
                user.gender = request.POST.get('gender', user.gender)
                user.educational_qualifications = request.POST.get('educational_qualifications', user.educational_qualifications)
                user.languages_known = request.POST.get('languages_known', user.languages_known)
                user.proficiency_level = request.POST.get('proficiency_level', user.proficiency_level)
                
                # Update permissions
                user.global_telemetry = request.POST.get('global_telemetry') == 'true'
                user.ledger_override = request.POST.get('ledger_override') == 'true'
                user.api_key_gen = request.POST.get('api_key_gen') == 'true'
                user.audit_log_purge = request.POST.get('audit_log_purge') == 'true'
                user.hr_matrix_view = request.POST.get('hr_matrix_view') == 'true'
                user.fleet_command = request.POST.get('fleet_command') == 'true'
                
                # Page Access Permissions - Restricted to Admin
                active_role_upper = request.session.get('active_role', '').upper()
                if active_role_upper in ['ADMIN', 'SYSTEM ADMIN', 'CEO', 'COO', 'CITO', 'HR AND OPERATION HEAD', 'HR', 'OPERATION HEAD']:
                    if 'can_access_dashboard' in request.POST:
                        user.can_access_dashboard = request.POST.get('can_access_dashboard') == 'true'
                    if 'can_access_notice_board' in request.POST:
                        user.can_access_notice_board = request.POST.get('can_access_notice_board') == 'true'
                    if 'can_access_time_attendance' in request.POST:
                        user.can_access_time_attendance = request.POST.get('can_access_time_attendance') == 'true'
                    if 'can_access_leave' in request.POST:
                        user.can_access_leave = request.POST.get('can_access_leave') == 'true'
                    if 'can_access_profiles' in request.POST:
                        user.can_access_profiles = request.POST.get('can_access_profiles') == 'true'
                    if 'can_access_lead_pipeline' in request.POST:
                        user.can_access_lead_pipeline = request.POST.get('can_access_lead_pipeline') == 'true'
                    if 'can_access_inventory' in request.POST:
                        user.can_access_inventory = request.POST.get('can_access_inventory') == 'true'
                    if 'can_access_accounts_receivable' in request.POST:
                        user.can_access_accounts_receivable = request.POST.get('can_access_accounts_receivable') == 'true'
                    if 'can_access_pos' in request.POST:
                        user.can_access_pos = request.POST.get('can_access_pos') == 'true'
                    if 'can_access_procurement' in request.POST:
                        user.can_access_procurement = request.POST.get('can_access_procurement') == 'true'
                
                user.save()
                
                if user.gender == 'Female':
                    from .models import CalendarEvent, LeaveRequest
                    female_holidays = CalendarEvent.objects.filter(is_female_holiday=True)
                    for fh in female_holidays:
                        LeaveRequest.objects.get_or_create(
                            employee_name=user.full_name,
                            leave_type='Casual',
                            start_date=fh.date,
                            end_date=fh.date,
                            defaults={
                                'reason': f'Female Holiday: {fh.title}',
                                'status': 'Approved'
                            }
                        )
                
                if request.session.get('logged_in_uid') == str(user.uid) or request.session.get('logged_in_name') == old_name:
                    request.session['logged_in_name'] = user.full_name
                    request.session['active_role'] = user.position
                    
                if old_name != user.full_name:
                    AttendanceRecord.objects.filter(employee_name=old_name).update(employee_name=user.full_name)
                    LeaveRequest.objects.filter(employee_name=old_name).update(employee_name=user.full_name)
                    
            return redirect(f'/users/create/?uid={uid}')

        elif action == 'delete':
            active_role = request.session.get('active_role', 'Operations Lead').upper()
            if active_role in ['COO', 'CEO', 'HR AND OPERATION HEAD', 'CITO', 'ADMIN', 'SYSTEM ADMIN', 'HR', 'OPERATION HEAD']:
                SystemUserProfile.objects.filter(uid=uid).delete()
                return redirect('/users/create/')
            else:
                return redirect(f'/users/create/?uid={uid}&error=unauthorized')

        elif action == 'quick_provision':
            SystemUserProfile.objects.all().delete()
            return redirect('/users/create/')

        return redirect('/users/create/')

from .models import Notice, LeaveRequest

class NoticeBoardView(TemplateView):
    template_name = "notice_board.html"

    def get(self, request, *args, **kwargs):
        notices = Notice.objects.all().order_by('-created_at')
        active_role = request.session.get('active_role', '')
        # Allow these roles to create notices
        can_create = active_role in ['CEO', 'COO', 'HR', 'Operation Head', 'CITO']
        return render(request, self.template_name, {
            'notices': notices,
            'can_create': can_create
        })

    def post(self, request, *args, **kwargs):
        active_role = request.session.get('active_role', '')
        if active_role in ['CEO', 'COO', 'HR', 'Operation Head', 'CITO']:
            title = request.POST.get('title')
            content = request.POST.get('content')
            priority = request.POST.get('priority', 'Standard')
            department = request.POST.get('department', 'HQ')
            author_name = request.session.get('active_role', 'System Admin') # Or could be actual name
            
            if title and content:
                Notice.objects.create(
                    title=title,
                    content=content,
                    priority=priority,
                    department=department,
                    author_name=author_name
                )
        return redirect('notice_board')


class LeaveListView(TemplateView):
    template_name = "leave.html"

    def get(self, request, *args, **kwargs):
        # Pre-populate default leave requests if none exist in database
        if not LeaveRequest.objects.exists():
            LeaveRequest.objects.create(
                employee_name="Hari Prasad",
                leave_type="Casual",
                start_date=date(2026, 6, 10),
                end_date=date(2026, 6, 12),
                reason="Family gathering in Pokhara",
                status="Approved"
            )
            LeaveRequest.objects.create(
                employee_name="John Doe",
                leave_type="Sick",
                start_date=date(2026, 6, 15),
                end_date=date(2026, 6, 15),
                reason="Dental checkup",
                status="Approved"
            )
            LeaveRequest.objects.create(
                employee_name="Sita Thapa",
                leave_type="Annual",
                start_date=date(2026, 6, 20),
                end_date=date(2026, 6, 25),
                reason="Visiting relatives abroad",
                status="Pending"
            )

        requests_list = LeaveRequest.objects.all().order_by('-created_at')

        # Allowances
        allowances = {
            'Casual': 8,
            'Sick': 12,
            'Annual': 15,
            'Maternity': 30
        }
        
        # Calculate used days for approved leaves for John Doe (current operator)
        used = {k: 0 for k in allowances}
        for req in LeaveRequest.objects.filter(employee_name="John Doe", status="Approved"):
            duration = (req.end_date - req.start_date).days + 1
            if req.leave_type in used:
                used[req.leave_type] += duration

        balances = []
        for ltype, limit in allowances.items():
            used_days = used[ltype]
            remaining = max(0, limit - used_days)
            balances.append({
                'type': ltype,
                'name': dict(LeaveRequest.LEAVE_TYPES).get(ltype),
                'limit': limit,
                'used': used_days,
                'remaining': remaining,
                'percent': int((remaining / limit) * 100) if limit > 0 else 0
            })

        active_role = request.session.get('active_role', '')
        can_approve = active_role.upper() in ['COO', 'HR', 'OPERATION HEAD', 'HR AND OPERATION HEAD', 'CEO', 'ADMIN', 'SYSTEM ADMIN', 'CITO']

        context = {
            'leave_requests': requests_list,
            'balances': balances,
            'leave_types': LeaveRequest.LEAVE_TYPES,
            'can_approve': can_approve
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')

        if action in ['approve', 'reject'] and request_id:
            active_role = request.session.get('active_role', '')
            if active_role.upper() in ['COO', 'HR', 'OPERATION HEAD', 'HR AND OPERATION HEAD', 'CEO', 'ADMIN', 'SYSTEM ADMIN', 'CITO']:
                try:
                    req = LeaveRequest.objects.get(id=request_id)
                    req.status = 'Approved' if action == 'approve' else 'Rejected'
                    req.save()
                    messages.success(request, f"Leave {req.status.lower()} for {req.employee_name}. Notification & Email sent to COO, HR, Operation Head, and Applicant.")
                except LeaveRequest.DoesNotExist:
                    pass
            else:
                messages.error(request, "Access Denied: Only COO, HR, and Operation Head can approve leaves.")
        else:
            employee_name = request.session.get('logged_in_name') or request.POST.get('employee_name', 'John Doe')
            leave_type = request.POST.get('leave_type')
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            reason = request.POST.get('reason', '')

            if leave_type and start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    LeaveRequest.objects.create(
                        employee_name=employee_name,
                        leave_type=leave_type,
                        start_date=start_date,
                        end_date=end_date,
                        reason=reason,
                        status='Pending'
                    )
                    messages.success(request, f"Leave requested! Notification & Email sent to COO, HR, and Operation Head.")
                except ValueError:
                    pass

        return redirect('leave_list')


from .models import LeadCRM, OrgNode

class LeadPipelineView(TemplateView):
    template_name = "leads.html"

    def get(self, request, *args, **kwargs):
        # Ensure default nodes exist
        if not OrgNode.objects.exists():
            hq = OrgNode.objects.create(name="HQ-NEPAL", node_type="HQ")
            dist = OrgNode.objects.create(name="DISTRIBUTOR-BAGMATI", node_type="CAT_A", parent=hq)
            OrgNode.objects.create(name="DEALER-KATHMANDU", node_type="CAT_B", parent=dist)

        default_node = OrgNode.objects.first()

        # Ensure default leads exist
        if not LeadCRM.objects.exists():
            LeadCRM.objects.create(lead_name="Ncell Axiata", node=default_node, pipeline_state="Proposal", phone="+977-9801200000", address="Lalitpur, Nepal", deal_value=250000.0, product_inquiry="Cisco ISR 4321 Router")
            LeadCRM.objects.create(lead_name="Nepal Telecom", node=default_node, pipeline_state="Identified", phone="+977-1-4210000", address="Bhadrakali, Kathmandu", deal_value=450000.0, product_inquiry="Hikvision PTZ Cameras")
            LeadCRM.objects.create(lead_name="WorldLink Communications", node=default_node, pipeline_state="Converted_To_Project", phone="+977-1-5970050", address="Jawalakhel, Lalitpur", deal_value=600000.0, product_inquiry="Ubiquiti UniFi APs")
            LeadCRM.objects.create(lead_name="Subisu Cablenet", node=default_node, pipeline_state="Dead", phone="+977-1-4429616", address="Baluwatar, Kathmandu", deal_value=120000.0, product_inquiry="Dahua DVR 16-ch")
            LeadCRM.objects.create(lead_name="DishHome Cable", node=default_node, pipeline_state="Proposal", phone="+977-1-5970000", address="Chabahil, Kathmandu", deal_value=180000.0, product_inquiry="Fiber Optic Spools 10km")
            LeadCRM.objects.create(lead_name="Vianet Communications", node=default_node, pipeline_state="Identified", phone="+977-1-5970555", address="Jawalakhel, Lalitpur", deal_value=320000.0, product_inquiry="MikroTik Cloud Core Router")

        leads = LeadCRM.objects.all().order_by('-created_at')
        nodes = OrgNode.objects.all()

        # Calculate metrics dynamically
        total_leads = leads.count()
        converted_leads = leads.filter(pipeline_state="Converted_To_Project").count()
        dead_leads = leads.filter(pipeline_state="Dead").count()

        win_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0.0
        dead_ratio = (dead_leads / total_leads * 100) if total_leads > 0 else 0.0

        from django.db.models import Sum
        total_value = leads.aggregate(total=Sum('deal_value'))['total'] or 0.0

        stages = {
            'Identified': [],
            'Proposal': [],
            'Converted_To_Project': [],
            'Dead': []
        }
        for lead in leads:
            if lead.pipeline_state in stages:
                stages[lead.pipeline_state].append(lead)

        context = {
            'stages': stages,
            'nodes': nodes,
            'total_leads': total_leads,
            'win_rate': round(win_rate, 1),
            'dead_ratio': round(dead_ratio, 1),
            'total_value': total_value,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        lead_id = request.POST.get('lead_id')

        if action == 'create':
            lead_name = request.POST.get('lead_name')
            node_id = request.POST.get('node_id')
            pipeline_state = request.POST.get('pipeline_state', 'Identified')
            phone = request.POST.get('phone', '')
            address = request.POST.get('address', '')
            deal_value_str = request.POST.get('deal_value', '0')
            product_inquiry = request.POST.get('product_inquiry', '')
            try:
                deal_value = float(deal_value_str)
            except ValueError:
                deal_value = 0.0

            if lead_name and node_id:
                try:
                    node = OrgNode.objects.get(id=node_id)
                    LeadCRM.objects.create(
                        lead_name=lead_name,
                        node=node,
                        pipeline_state=pipeline_state,
                        phone=phone,
                        address=address,
                        deal_value=deal_value,
                        product_inquiry=product_inquiry
                    )
                except OrgNode.DoesNotExist:
                    pass

        elif action == 'update_stage':
            new_stage = request.POST.get('pipeline_state')
            if lead_id and new_stage:
                try:
                    lead = LeadCRM.objects.get(id=lead_id)
                    lead.pipeline_state = new_stage
                    lead.save()
                except LeadCRM.DoesNotExist:
                    pass

        elif action == 'delete':
            if lead_id:
                LeadCRM.objects.filter(id=lead_id).delete()

        return redirect('lead_pipeline')


from django.views import View
from .models import ProcurementRequest
from .services import ProcurementStateMachine

class ProcurementView(View):
    template_name = "procurement.html"

    def get(self, request, *args, **kwargs):
        # Ensure default procurement requests exist for testing
        if not ProcurementRequest.objects.exists():
            ProcurementRequest.objects.create(title="Purchase 15x CCTV Cameras (Hikvision)", track="Local", hr_approved=True, coo_approved=False)
            ProcurementRequest.objects.create(title="Import Server Rack Infrastructure", track="International", hr_approved=True, cto_approved=True, coo_approved=False)
            ProcurementRequest.objects.create(title="Office Chairs & Desks Refurbishment", track="Local", hr_approved=False, coo_approved=False)
            ProcurementRequest.objects.create(title="Nightvision AI Drone Prototype Import", track="International", hr_approved=True, cto_approved=True, coo_approved=True, ceo_approved=True, is_terminal=True)

        requests = ProcurementRequest.objects.all().order_by('-id')

        # Dynamically enrich each request in python with the "next_signer" role
        for req in requests:
            if req.is_terminal:
                req.next_signer = None
            elif req.track == 'International':
                if not req.hr_approved:
                    req.next_signer = 'HR'
                elif not req.cto_approved:
                    req.next_signer = 'CTO'
                elif not req.coo_approved:
                    req.next_signer = 'COO'
                elif not req.ceo_approved:
                    req.next_signer = 'CEO'
                else:
                    req.next_signer = None
            elif req.track == 'Local':
                if not req.hr_approved:
                    req.next_signer = 'HR'
                elif not req.coo_approved:
                    req.next_signer = 'COO'
                else:
                    req.next_signer = None

        # Statistics
        total_count = requests.count()
        completed_count = requests.filter(is_terminal=True).count()
        pending_local = requests.filter(track='Local', is_terminal=False).count()
        pending_intl = requests.filter(track='International', is_terminal=False).count()

        context = {
            'requests': requests,
            'total_count': total_count,
            'completed_count': completed_count,
            'pending_local': pending_local,
            'pending_intl': pending_intl,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        req_id = request.POST.get('procurement_id')

        if action == 'create':
            title = request.POST.get('title')
            track = request.POST.get('track', 'Local')
            supporting_document = request.FILES.get('supporting_document')
            landing_cost_management = request.POST.get('landing_cost_management', '0.00')
            goods_receive_notes = request.POST.get('goods_receive_notes')
            if title:
                lcm = 0.00
                if landing_cost_management:
                    try:
                        lcm = float(landing_cost_management)
                    except ValueError:
                        pass
                ProcurementRequest.objects.create(
                    title=title, track=track, supporting_document=supporting_document,
                    landing_cost_management=lcm, goods_receive_notes=goods_receive_notes
                )
        
        elif action == 'approve':
            role = request.POST.get('role')
            if req_id and role:
                success, msg = ProcurementStateMachine.approve_step(req_id, role)
        
        elif action == 'delete':
            if req_id:
                ProcurementRequest.objects.filter(id=req_id).delete()

        return redirect('procurement_list')


from .models import AccountsReceivable, OrgNode
from datetime import date, datetime, timedelta

class AccountsReceivableView(View):
    template_name = "accounts_receivable.html"

    def get(self, request, *args, **kwargs):
        # Pre-populate default accounts receivable if none exist in database
        if not AccountsReceivable.objects.exists():
            # Get default nodes
            hq = OrgNode.objects.filter(name="HQ-NEPAL").first()
            if not hq:
                hq = OrgNode.objects.create(name="HQ-NEPAL", node_type="HQ")
            dist = OrgNode.objects.filter(name="DISTRIBUTOR-BAGMATI").first() or OrgNode.objects.create(name="DISTRIBUTOR-BAGMATI", node_type="CAT_A", parent=hq)
            dealer = OrgNode.objects.filter(name="DEALER-KATHMANDU").first() or OrgNode.objects.create(name="DEALER-KATHMANDU", node_type="CAT_B", parent=dist)
            
            AccountsReceivable.objects.create(
                invoice_number="INV-2026-001",
                node=hq,
                amount_due=24500.00,
                amount_paid=0.0,
                state="Unpaid",
                due_date=date.today() + timedelta(days=15)
            )
            AccountsReceivable.objects.create(
                invoice_number="INV-2026-002",
                node=dist,
                amount_due=112000.00,
                amount_paid=112000.00,
                state="Settled",
                due_date=date.today() - timedelta(days=5)
            )
            AccountsReceivable.objects.create(
                invoice_number="INV-2026-003",
                node=dealer,
                amount_due=4120.50,
                amount_paid=2000.00,
                state="Partially_Paid",
                due_date=date.today() + timedelta(days=30)
            )
            AccountsReceivable.objects.create(
                invoice_number="INV-2026-004",
                node=dist,
                amount_due=67900.00,
                amount_paid=0.0,
                state="Disputed",
                due_date=date.today() + timedelta(days=2)
            )

        invoices = AccountsReceivable.objects.all().order_by('-created_at')
        nodes = OrgNode.objects.all()

        # Calculate metrics dynamically
        total_invoiced = 0.0
        total_settled = 0.0
        total_receivables = 0.0
        critical_past_due = 0.0

        today = date.today()

        for inv in invoices:
            due = float(inv.amount_due)
            paid = float(inv.amount_paid)
            outstanding = max(0.0, due - paid)

            total_invoiced += due
            total_settled += paid
            total_receivables += outstanding
                
            # Critical Past Due is defined as Unpaid/Disputed/Partially Paid invoices past due date
            if inv.state in ['Unpaid', 'Disputed', 'Partially_Paid'] and inv.due_date and inv.due_date < today:
                critical_past_due += outstanding

        active_role = request.session.get('active_role', '')
        is_admin = active_role in ['CEO', 'COO', 'HR', 'Operation Head', 'CITO']
        
        context = {
            'invoices': invoices,
            'nodes': nodes,
            'total_invoiced': total_invoiced,
            'total_settled': total_settled,
            'total_receivables': total_receivables,
            'critical_past_due': critical_past_due,
            'is_admin': is_admin,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        active_role = request.session.get('active_role', '')
        is_admin = active_role in ['CEO', 'COO', 'HR', 'Operation Head', 'CITO']
        
        action = request.POST.get('action')
        invoice_id = request.POST.get('invoice_id')
        
        if action == 'delete' and invoice_id and is_admin:
            AccountsReceivable.objects.filter(id=invoice_id).delete()
            return redirect('accounts_receivable')

        if action == 'create':
            invoice_number = request.POST.get('invoice_number')
            node_id = request.POST.get('node_id')
            amount_due_str = request.POST.get('amount_due', '0')
            amount_paid_str = request.POST.get('amount_paid', '0')
            state = request.POST.get('state', 'Unpaid')
            due_date_str = request.POST.get('due_date')

            try:
                amount_due = float(amount_due_str)
            except ValueError:
                amount_due = 0.0

            try:
                amount_paid = float(amount_paid_str)
            except ValueError:
                amount_paid = 0.0

            if state == 'Settled':
                amount_paid = amount_due
            elif state in ['Unpaid', 'Disputed'] and not amount_paid_str:
                amount_paid = 0.0

            due_date_val = None
            if due_date_str:
                try:
                    due_date_val = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            if invoice_number and node_id:
                try:
                    node = OrgNode.objects.get(id=node_id)
                    AccountsReceivable.objects.create(
                        invoice_number=invoice_number,
                        node=node,
                        amount_due=amount_due,
                        amount_paid=amount_paid,
                        state=state,
                        due_date=due_date_val
                    )
                except OrgNode.DoesNotExist:
                    pass

        elif action == 'update':
            if invoice_id:
                try:
                    inv = AccountsReceivable.objects.get(id=invoice_id)
                    invoice_number = request.POST.get('invoice_number')
                    node_id = request.POST.get('node_id')
                    amount_due_str = request.POST.get('amount_due')
                    amount_paid_str = request.POST.get('amount_paid')
                    state = request.POST.get('state')
                    due_date_str = request.POST.get('due_date')

                    if invoice_number:
                        inv.invoice_number = invoice_number
                    if node_id:
                        try:
                            inv.node = OrgNode.objects.get(id=node_id)
                        except OrgNode.DoesNotExist:
                            pass
                    if amount_due_str is not None:
                        try:
                            inv.amount_due = float(amount_due_str)
                        except ValueError:
                            pass
                    
                    if state:
                        inv.state = state

                    if amount_paid_str is not None:
                        try:
                            inv.amount_paid = float(amount_paid_str)
                        except ValueError:
                            pass

                    # Auto correction logic based on state changes
                    if inv.state == 'Settled':
                        inv.amount_paid = inv.amount_due
                    elif inv.state in ['Unpaid', 'Disputed'] and amount_paid_str is None:
                        inv.amount_paid = 0.0

                    if due_date_str:
                        try:
                            inv.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    inv.save()
                except AccountsReceivable.DoesNotExist:
                    pass

        elif action == 'delete':
            if invoice_id:
                AccountsReceivable.objects.filter(id=invoice_id).delete()

        return redirect('accounts_receivable')


class SwitchRoleView(View):
    def post(self, request, *args, **kwargs):
        active_role = request.POST.get('active_role', 'Operations Lead')
        request.session['active_role'] = active_role
        return redirect(request.META.get('HTTP_REFERER', '/'))

from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

@method_decorator(never_cache, name='dispatch')
class LoginView(View):
    def get(self, request, *args, **kwargs):
        if request.session.get('logged_in_uid'):
            return redirect('dashboard')
        return render(request, 'login.html')

    def post(self, request, *args, **kwargs):
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')
        
        user = SystemUserProfile.objects.filter(Q(uid__iexact=login_id) | Q(full_name__iexact=login_id)).first()
        
        if user and user.password == password:
            request.session['logged_in_uid'] = user.uid
            request.session['logged_in_name'] = user.full_name
            request.session['active_role'] = user.position
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid Identity Token or Access Key.'})

@method_decorator(never_cache, name='dispatch')
class LogoutView(View):
    def get(self, request, *args, **kwargs):
        request.session.flush()
        return redirect('login')

import json
import uuid
from django.contrib import messages
from django.views.generic import View

class POSView(TemplateView):
    template_name = "pos.html"

    def get(self, request, *args, **kwargs):
        from .models import InventoryLedger
        inventory_items = []
        for item in InventoryLedger.objects.all():
            inventory_items.append({
                'stock_record_id': str(item.stock_record_id),
                'sku_id': item.sku_id,
                'product_name': item.product_name,
                'product_image': item.product_image.url if item.product_image else None,
                'quantity_on_hand': item.quantity_on_hand,
                'price': float(item.price)
            })
        
        return render(request, self.template_name, {'inventory': inventory_items})

class POSCheckoutView(View):
    def post(self, request, *args, **kwargs):
        from .models import InventoryLedger, AccountsReceivable, OrgNode
        cart_data_str = request.POST.get('cart_data', '{}')
        total_amount = request.POST.get('total_amount', '0.00')
        discount = request.POST.get('discount', '0')
        customer_name = request.POST.get('customer_name', 'WALK-IN CUSTOMER')
        customer_pan = request.POST.get('customer_pan', '')
        customer_phone = request.POST.get('customer_phone', '')
        customer_address = request.POST.get('customer_address', '')
        payment_method = request.POST.get('payment_method', 'Cash')
        
        try:
            cart = json.loads(cart_data_str)
            
            hq_node = OrgNode.objects.filter(node_type='HQ').first()
            if not hq_node:
                hq_node = OrgNode.objects.create(name="HQ-NEPAL-POS", node_type="HQ")
                
            invoice_num = f"POS-{str(uuid.uuid4())[:8].upper()}"
            purchased_items = []

            # 1. Deduct Inventory
            for record_id, item_data in cart.items():
                qty = item_data.get('qty', 0)
                inv_item = InventoryLedger.objects.get(stock_record_id=record_id)
                if inv_item.quantity_on_hand >= qty:
                    inv_item.quantity_on_hand -= qty
                    inv_item.save()
                    purchased_items.append({
                        'sku_id': inv_item.sku_id,
                        'product_name': inv_item.product_name,
                        'quantity': qty,
                        'price': float(inv_item.price),
                        'total': qty * float(inv_item.price)
                    })
            
            # 2. Record in Accounts Receivable
            paid_amount = total_amount if payment_method in ['Cash', 'Cheque'] else 0.0
            ar_state = 'Settled' if payment_method in ['Cash', 'Cheque'] else 'Unpaid'
            
            AccountsReceivable.objects.create(
                invoice_number=invoice_num,
                customer_name=customer_name,
                customer_pan=customer_pan,
                customer_phone=customer_phone,
                customer_address=customer_address,
                node=hq_node,
                amount_due=total_amount,
                amount_paid=paid_amount,
                state=ar_state,
                payment_method=payment_method
            )
            
            # Save invoice to session for printable page
            request.session['last_invoice'] = {
                'invoice_id': invoice_num,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'customer_name': customer_name,
                'customer_pan': customer_pan,
                'customer_phone': customer_phone,
                'customer_address': customer_address,
                'payment_method': payment_method,
                'items': purchased_items,
                'subtotal': sum(i['total'] for i in purchased_items),
                'discount': float(discount),
                'total_amount': float(total_amount)
            }
            
            messages.success(request, f"Checkout complete! Invoice {invoice_num} generated.")
            return redirect('pos_invoice')
            
        except Exception as e:
            messages.error(request, f"Checkout failed: {str(e)}")
            return redirect('pos')

class POSInvoiceView(TemplateView):
    template_name = "pos_invoice.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.request.session.get('last_invoice', None)
        return context

class StaffPayrollReportView(TemplateView):
    template_name = "attendance_payroll_report.html"

    def get(self, request, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        from .models import EmployeeProfile, AttendanceRecord, SystemUserProfile
        
        active_role = request.session.get('active_role', '').upper()
        allowed_roles = ['CEO', 'COO', 'HR', 'OPERATION HEAD', 'HR AND OPERATION HEAD', 'CITO', 'ADMIN']
        
        if active_role not in allowed_roles:
            messages.error(request, "Access Denied: You do not have permission to view the Payroll Report.")
            return redirect('dashboard')
            
        # 1. Fetch Attendance Records for Display
        attendance_records = AttendanceRecord.objects.all().order_by('-date', '-created_at')
        
        # 2. Fetch all Staff/System Users
        users = SystemUserProfile.objects.all()
        
        # 3. Calculate Payroll per User
        payroll_data = []
        for u in users:
            # Let's try to find an EmployeeProfile for their gross salary, otherwise default to 50000
            emp = EmployeeProfile.objects.filter(first_name__icontains=u.full_name.split(' ')[0]).first()
            base_salary = float(emp.base_gross_salary) if emp else 50000.0
            
            # Assuming standard 160 hours per month
            hourly_rate = base_salary / 160.0
            
            # Sum up hours worked
            emp_records = AttendanceRecord.objects.filter(employee_name=u.full_name, status__in=['Present', 'Late'])
            total_hours = 0.0
            
            for record in emp_records:
                # If they checked in but haven't checked out, we can't reliably calculate. We'll skip or assume 8 hrs.
                if record.check_in_time and record.check_out_time:
                    check_in = datetime.combine(date.today(), record.check_in_time)
                    check_out = datetime.combine(date.today(), record.check_out_time)
                    hours = (check_out - check_in).total_seconds() / 3600.0
                    if hours < 0:
                        hours += 24 # overnight shift handle
                    total_hours += hours
                else:
                    # If just present but missing times, assume 8 hours
                    total_hours += 8.0
                    
            total_pay = total_hours * hourly_rate
            
            payroll_data.append({
                'employee_name': u.full_name,
                'position': u.position,
                'total_hours': round(total_hours, 2),
                'hourly_rate': round(hourly_rate, 2),
                'total_pay': round(total_pay, 2),
                'base_salary': round(base_salary, 2),
            })
            
        # Additional default stats for John Doe if the users table doesn't match him
        if not any(pd['employee_name'] == 'John Doe' for pd in payroll_data):
            john_records = AttendanceRecord.objects.filter(employee_name='John Doe', status='Present')
            if john_records.exists():
                john_hours = 0.0
                for record in john_records:
                    if record.check_in_time and record.check_out_time:
                        check_in = datetime.combine(date.today(), record.check_in_time)
                        check_out = datetime.combine(date.today(), record.check_out_time)
                        hours = (check_out - check_in).total_seconds() / 3600.0
                        if hours < 0:
                            hours += 24
                        john_hours += hours
                    else:
                        john_hours += 8.0
                hourly_rate = 50000.0 / 160.0
                payroll_data.append({
                    'employee_name': 'John Doe',
                    'position': 'Staff',
                    'total_hours': round(john_hours, 2),
                    'hourly_rate': round(hourly_rate, 2),
                    'total_pay': round(john_hours * hourly_rate, 2),
                    'base_salary': 50000.0,
                })

        context = {
            'attendance_records': attendance_records,
            'payroll_data': payroll_data
        }
        return render(request, self.template_name, context)

class ProjectTaskBoardView(TemplateView):
    template_name = "task_board.html"

    def get(self, request, *args, **kwargs):
        from .models import ProjectTask, SystemUserProfile
        
        # Get all tasks
        tasks = ProjectTask.objects.all().order_by('-created_at')
        total_tasks = tasks.count()
        
        # Group tasks by status
        kanban_data = {
            'TODO': tasks.filter(status='TODO'),
            'IN_PROGRESS': tasks.filter(status='IN_PROGRESS'),
            'REVIEW': tasks.filter(status='REVIEW'),
            'DONE': tasks.filter(status='DONE'),
        }
        
        metrics = {
            'todo_pct': 0,
            'in_progress_pct': 0,
            'review_pct': 0,
            'done_pct': 0,
            'total': total_tasks
        }
        
        if total_tasks > 0:
            metrics['todo_pct'] = round((kanban_data['TODO'].count() / total_tasks) * 100)
            metrics['in_progress_pct'] = round((kanban_data['IN_PROGRESS'].count() / total_tasks) * 100)
            metrics['review_pct'] = round((kanban_data['REVIEW'].count() / total_tasks) * 100)
            metrics['done_pct'] = round((kanban_data['DONE'].count() / total_tasks) * 100)
        
        # Get all users for the assignment dropdown
        users = SystemUserProfile.objects.all()
        
        context = {
            'kanban_data': kanban_data,
            'metrics': metrics,
            'users': users,
            'today': date.today().strftime('%Y-%m-%d')
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        from .models import ProjectTask, SystemUserProfile, SystemNotification
        
        action = request.POST.get('action')
        logged_in_name = request.session.get('logged_in_name')
        
        if action == 'create_task':
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            priority = request.POST.get('priority', 'MEDIUM')
            assigned_to_id = request.POST.get('assigned_to')
            due_date = request.POST.get('due_date')
            
            assigned_to = None
            if assigned_to_id:
                assigned_to = SystemUserProfile.objects.filter(id=assigned_to_id).first()
                
            assigned_by = None
            if logged_in_name:
                assigned_by = SystemUserProfile.objects.filter(full_name=logged_in_name).first()
                
            task = ProjectTask.objects.create(
                title=title,
                description=description,
                priority=priority,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
                due_date=due_date if due_date else None
            )
            
            # Send Notification to Assignee
            if assigned_to and assigned_by and assigned_to.id != assigned_by.id:
                SystemNotification.objects.create(
                    recipient=assigned_to,
                    message=f"{assigned_by.full_name} assigned you a new task: '{title}'",
                    link="/task-board/"
                )
                
            messages.success(request, 'Task created successfully.')
            
        elif action == 'update_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('new_status')
            
            if task_id and new_status:
                task = ProjectTask.objects.filter(id=task_id).first()
                if task:
                    task.status = new_status
                    task.save()
                    
                    # Send Notification to Creator
                    if task.assigned_by and task.assigned_by.full_name != logged_in_name:
                        # Get friendly status name
                        status_display = dict(ProjectTask.STATUS_CHOICES).get(new_status, new_status)
                        SystemNotification.objects.create(
                            recipient=task.assigned_by,
                            message=f"{logged_in_name} moved '{task.title}' to {status_display}",
                            link="/task-board/"
                        )
                        
                    from django.http import JsonResponse
                    return JsonResponse({'success': True})
                    
        return redirect('task_board')
