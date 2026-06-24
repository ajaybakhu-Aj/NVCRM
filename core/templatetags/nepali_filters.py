from django import template
import nepali_datetime
import datetime

register = template.Library()

@register.filter(name='to_nepali_date')
def to_nepali_date(value, fmt='%K-%n-%D'):
    if not value:
        return value
    try:
        if isinstance(value, datetime.datetime):
            value = value.date()
        if isinstance(value, datetime.date):
            nepali_date = nepali_datetime.date.from_datetime_date(value)
            return nepali_date.strftime(fmt)
    except Exception:
        return value
    return value

@register.filter(name='nepali_day')
def nepali_day(value):
    return to_nepali_date(value, '%D')

@register.filter(name='nepali_month_name')
def nepali_month_name(value):
    return to_nepali_date(value, '%N')

@register.filter(name='nepali_year')
def nepali_year(value):
    return to_nepali_date(value, '%K')
