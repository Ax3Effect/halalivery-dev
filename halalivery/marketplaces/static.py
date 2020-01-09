"""Static variables definitions"""

from decimal import Decimal

HALALIVERY_PERCENT = Decimal('0.30')
HALALIVERY_RESTAURANT_DELIVERY_FEE = Decimal('2.50')
HALALIVERY_GROCERY_DELIVERY_FEE = Decimal('4.00')
HALALIVERY_ADDITIONAL_FEE = Decimal('1.50')

ORDER_STATUS = (
    (0, 'Pending'),
    (1, 'Confirmed'),
    (2, 'Preparing'),
    (3, 'Ready for pickup'),
    (4, 'Driver arrived'),
    (5, 'Driver collected'),
    (6, 'Driver delivered'),
    (7, 'Canceled'),
    (8, 'Self picked up')
)

BUSY_STATUS = (
    (0, 'Quiet'),
    (1, 'Moderate'),
    (2, 'Busy'),
)
ORDER_STATUS_DICT = dict((v, k) for k, v in ORDER_STATUS)

PRICE_STRATEGY = (
    ('No additional cost', 'NO_ADDITIONAL_COST'),
    ('Item price aggregate', 'ITEM_PRICE_AGGREGATE')
)

WEEKDAYS = (
    (1, "Monday"),
    (2, "Tuesday"),
    (3, "Wednesday"),
    (4, "Thursday"),
    (5, "Friday"),
    (6, "Saturday"),
    (7, "Sunday")
)
DELIVERY_TYPE = ((0, 'Halalivery Delivery'), (1, 'Vendor Driver Delivery'), (2, 'Self pickup'))
MOODS = (("grocery", "I'm Grocery Shopping"),
         ("meat", "Fresh Meat"),
         ("lunchy", "Feeling Lunchy"),
         ("night_meal", "Late Night Meal"),
         ("movie_night", "Movie Night"),
         ("thirst", "Punch my Thirst"),
         ("breakfast", "Early for Breakfast"),
         ("healthy", "Feeling Healthy"),
         ("cheat", "Cheat Day"),
         ("dessert", "Craving Dessert"))

VOUCHER_TYPE = (
    ("PERCENT", "Percent discount"),
)
