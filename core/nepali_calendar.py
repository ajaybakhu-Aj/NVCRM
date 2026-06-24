import nepali_datetime
import datetime

def get_nepali_monthdatescalendar(np_year, np_month):
    """
    Returns a list of weeks. Each week is a list of 7 datetime.date objects.
    The grid represents a Nepali month.
    """
    # 1. Find the first day of the Nepali month
    first_day_np = nepali_datetime.date(np_year, np_month, 1)
    
    # 2. Find the total number of days in the Nepali month
    # We can do this by finding the max day, or just trying to increment until we hit the next month
    # Actually nepali_datetime.date has `max`? No, max is a class attribute.
    # Let's find the first day of next month
    next_month = np_month + 1
    next_year = np_year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    first_day_next_month_np = nepali_datetime.date(next_year, next_month, 1)
    
    # Total days in month
    # We can calculate by ordinal difference
    days_in_month = first_day_next_month_np.toordinal() - first_day_np.toordinal()
    
    # 3. Create the grid
    weeks = []
    current_week = []
    
    # Nepali weekday: 0 = Sunday, 1 = Monday ... 6 = Saturday ?
    # Let's check: first_day_np.weekday() 
    # Usually in Python datetime, 0 is Monday, 6 is Sunday.
    # Let's assume standard python weekday()
    # If firstweekday is Sunday (like standard calendars in Nepal)
    # We want Sunday=0 ... Saturday=6
    
    first_weekday_python = first_day_np.to_datetime_date().weekday() # 0 = Monday, 6 = Sunday
    # Convert to Sunday=0
    start_day_idx = (first_weekday_python + 1) % 7
    
    # Padding from previous month
    current_date = first_day_np.to_datetime_date() - datetime.timedelta(days=start_day_idx)
    
    for i in range(start_day_idx):
        current_week.append(current_date)
        current_date += datetime.timedelta(days=1)
        
    for day in range(1, days_in_month + 1):
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
        current_week.append(current_date)
        current_date += datetime.timedelta(days=1)
        
    # Pad the remaining days of the last week
    while len(current_week) < 7:
        current_week.append(current_date)
        current_date += datetime.timedelta(days=1)
        
    if current_week:
        weeks.append(current_week)
        
    return weeks
