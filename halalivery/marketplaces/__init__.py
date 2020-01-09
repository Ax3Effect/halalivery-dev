from django.utils.translation import pgettext_lazy


class WeekDay:
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    CHOICES = [
        (MONDAY, pgettext_lazy('Day of the week', 'Monday')),
        (TUESDAY, pgettext_lazy('Day of the week', 'Tuesday')),
        (WEDNESDAY, pgettext_lazy('Day of the week', 'Wednesday')),
        (THURSDAY, pgettext_lazy('Day of the week', 'Thursday')),
        (FRIDAY, pgettext_lazy('Day of the week', 'Friday')),
        (SATURDAY, pgettext_lazy('Day of the week', 'Saturday')),
        (SUNDAY, pgettext_lazy('Day of the week', 'Sunday'))]


class Moods:
    GROCERY = 'grocery'
    MEAT = 'meat'
    LUNCHY = 'lunchy'
    NIGHT_MEAL = 'night_meal'
    MOVIE_NIGHT = 'night_meal'
    THIRST = 'thirst'
    BREAKFAST = 'breakfast'
    HEALTHY = 'healthy'
    CHEAT = 'cheat'
    DESSERT = 'dessert'

    CHOICES = [
        (GROCERY, pgettext_lazy('Im Grocery Shopping', 'Grocery')),
        (MEAT, pgettext_lazy('Fresh Meat', 'Meat')),
        (LUNCHY, pgettext_lazy('Feeling Lunchy', 'Lunchy')),
        (NIGHT_MEAL, pgettext_lazy('Late Night Meal', 'Night meal')),
        (MOVIE_NIGHT, pgettext_lazy('Movie Night', 'Movie night')),
        (THIRST, pgettext_lazy('Punch my Thirst', 'Thirst')),
        (BREAKFAST, pgettext_lazy('Early for Breakfast', 'Breakfast')),
        (HEALTHY, pgettext_lazy('Feeling Healthy', 'Healthy')),
        (CHEAT, pgettext_lazy('Cheat Day', 'Cheat')),
        (DESSERT, pgettext_lazy('Craving Dessert', 'Dessert'))]


class BusyStatus:
    QUIET = 'quiet'
    MODERATE = 'moderate'
    BUSY = 'busy'

    CHOICES = [
        (QUIET, pgettext_lazy('Quiet status', 'Quiet')),
        (MODERATE, pgettext_lazy('Moderate status', 'Moderate')),
        (BUSY, pgettext_lazy('Busy status', 'Busy'))]