# -*- coding: utf-8 -*-
from django import template
import datetime
# import timedelta

register = template.Library()

def nice_repr(timedelta, display="long", sep=", "):
    """
    Turns a datetime.timedelta object into a nice string repr.
    
    display can be "minimal", "short" or "long" [default].
    
    >>> from datetime import timedelta as td
    >>> nice_repr(td(days=1, hours=2, minutes=3, seconds=4))
    '1 day, 2 hours, 3 minutes, 4 seconds'
    >>> nice_repr(td(days=1, seconds=1), "minimal")
    '1d, 1s'
    """
    
    assert isinstance(timedelta, datetime.timedelta), "First argument must be a timedelta."
    
    result = []
    
    weeks = timedelta.days / 7
    days = timedelta.days % 7
    hours = timedelta.seconds / 3600
    minutes = (timedelta.seconds % 3600) / 60
    seconds = timedelta.seconds % 60
    
    if display == "sql":
        days += weeks * 7
        return "%i %02i:%02i:%02i" % (days, hours, minutes, seconds)
    elif display == 'minimal':
        words = ["w", "d", "h", "m", "s"]
    elif display == 'short':
        words = [" wks", " days", " hrs", " min", " sec"]
    else:
        words = [" weeks", " days", " hours", " minutes", " seconds"]
    
    values = [weeks, days, hours, minutes, seconds]
    
    for i in range(len(values)):
        if values[i]:
            if values[i] == 1 and len(words[i]) > 1:
                result.append("%i%s" % (values[i], words[i].rstrip('s')))
            else:
                result.append("%i%s" % (values[i], words[i]))
    
    return sep.join(result)


def iso8601_repr(timedelta):
    """
    Represent a timedelta as an ISO8601 duration.
    http://en.wikipedia.org/wiki/ISO_8601#Durations

    >>> from datetime import timedelta as td
    >>> iso8601_repr(td(days=1, hours=2, minutes=3, seconds=4))
    'P1DT2H3M4S'
    """
    years = timedelta.days / 365
    weeks = (timedelta.days % 365) / 7
    days = timedelta.days % 7

    hours = timedelta.seconds / 3600
    minutes = (timedelta.seconds % 3600) / 60
    seconds = timedelta.seconds % 60

    formatting = (
        ('P', (
            ('Y', years),
            ('W', weeks),
            ('D', days),
        )),
        ('T', (
            ('H', hours),
            ('M', minutes),
            ('S', seconds),
        )),
      )

    result = []
    for category, subcats in formatting:
        result += category
        for format, value in subcats:
            if value:
                result.append('%d%c' % (value, format))

    return "".join(result)

@register.filter(name='timedelta')
def timedelta(value, display="long"):
    if value is None:
        return value
    return nice_repr(value, display)

@register.filter(name='iso8601')
def iso8601(value):
    if value is None:
        return value
    return iso8601_repr(value)

