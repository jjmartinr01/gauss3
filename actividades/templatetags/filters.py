# -*- coding: utf-8 -*-
from django import template

register = template.Library()

@register.filter
def future_dates_only(the_date):
   if the_date > date.today():
       return True
   else:
       return False