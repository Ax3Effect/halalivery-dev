from datetime import time

def is_open(marketplace=None, now=None):
    now_time = time(now.hour, now.minute, now.second)
    ohs = marketplace.operating_times.all()
    
    if marketplace is not None:
        for oh in ohs:
            is_open = False
            # start and end is on the same day
            if (oh.weekday == now.isoweekday() and
                    oh.from_hour <= now_time and
                    now_time <= oh.to_hour):
                
                is_open = oh

            # start and end are not on the same day and we test on the start day
            if (oh.weekday == now.isoweekday() and
                    oh.from_hour <= now_time and
                    ((oh.to_hour < oh.from_hour) and
                        (now_time < time(23, 59, 59)))):
                is_open = oh

            # If monday
            if(now.isoweekday() - 1 == 0):
                if (oh.weekday == 7 and
                    oh.from_hour >= now_time and
                    oh.to_hour >= now_time and
                    oh.to_hour < oh.from_hour):
                    is_open = oh

            # start and end are not on the same day and we test on the end day
            if (oh.weekday == (now.isoweekday() - 1) % 7 and
                    oh.from_hour >= now_time and
                    oh.to_hour >= now_time and
                    oh.to_hour < oh.from_hour):
                is_open = oh
                # print " 'Special' case after midnight", oh

            if is_open is not False:
                return oh
    return False