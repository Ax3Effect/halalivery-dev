import os
from os.path import join
from distutils.util import strtobool
import dj_database_url
from configurations import Configuration
from django_prices.templatetags.prices_i18n import get_currency_fraction

import urllib
from django.utils.translation import gettext_lazy as _, pgettext_lazy

def get_bool_from_env(name, default_value):
    if name in os.environ:
        value = os.environ[name]
        try:
            return ast.literal_eval(value)
        except ValueError as e:
            raise ValueError(
                '{} is an invalid value for {}'.format(value, name)) from e
    return default_value

class Common(Configuration):

    INSTALLED_APPS = (
        # 'grappelli',
        # 'nested_inline'
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',

        'debug_toolbar',
        # Third party apps
        'anymail',
        'import_export',
        # 'nested_admin',
        'rest_framework',            # utilities for rest apis
        'rest_framework.authtoken',  # token authentication
        'django_filters',            # for filtering rest endpoints
        'django_extensions',
        'django_celery_results',
        'django_celery_beat',
        # Postgis
        'django.contrib.gis',
        # Google maps for Geofields
        'mapwidgets',
        # 'floppyforms',
        'django_countries',
        'django_prices',
        'django_prices_openexchangerates',
        'django_prices_vatlayer',
        'measurement',
        'django_measurement',
        'versatileimagefield',

        # Your apps
        'halalivery.core',
        'halalivery.users',
        'halalivery.marketplaces',
        'halalivery.drivers',
        'halalivery.basket',
        'halalivery.delivery',
        'halalivery.menu',
        'halalivery.order',
        'halalivery.vendors',
        'halalivery.coupons',
        'halalivery.partner_discounts',
        'halalivery.payment'
    )

    # https://docs.djangoproject.com/en/2.0/topics/http/middleware/
    MIDDLEWARE = (
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    ALLOWED_HOSTS = ["*"]
    # import custom_storages
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    ROOT_URLCONF = 'halalivery.urls'
    SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
    WSGI_APPLICATION = 'halalivery.wsgi.application'

    # Email
    EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"

    ADMINS = (
        ('Author', 'root@halalivery.co.uk'),
    )

    # Postgres
    DATABASES = {}

    # AWS Docker database
    if 'DATABASE_URL' in os.environ:
        DATABASES = {
            'default': {
                # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'ENGINE': 'django.contrib.gis.db.backends.postgis',
                'NAME': os.environ['POSTGRES_DB'],
                'USER': os.environ['POSTGRES_USER'],
                'PASSWORD': os.environ['POSTGRES_PASSWORD'],
                'HOST': os.environ['DATABASE_URL'],
                'PORT': os.environ['POSTGRES_PORT'],
            }
        }
    else:
        # DATABASES = {
        #     'default': dj_database_url.config(
        #         default='postgres://postgres:@postgres:5432/postgres',
        #         conn_max_age=int(os.getenv('POSTGRES_CONN_MAX_AGE', 600))
        #     )
        # }
        DATABASES = {
            'default': dj_database_url.config(
                default='postgis://docker:docker@postgis:5432/gis',
                conn_max_age=int(os.getenv('POSTGRES_CONN_MAX_AGE', 600))
            )
        }
    """
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',
            'USER': 'postgres',
            'HOST': 'db',
            'PORT': 5432,
        }
    }
    """

    # General
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
    APPEND_SLASH = False

    LANGUAGE_CODE = 'en-us'
    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = False
    USE_L10N = True
    USE_TZ = True
    TIME_ZONE = 'Europe/London'
    LOGIN_REDIRECT_URL = '/'

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/2.0/howto/static-files/
    STATIC_ROOT = os.path.normpath(join(os.path.dirname(BASE_DIR), 'static'))
    STATICFILES_DIRS = []
    STATIC_URL = os.environ.get('STATIC_URL', '/static/')
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    )

    # Media files
    MEDIA_ROOT = join(os.path.dirname(BASE_DIR), 'media')
    MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': STATICFILES_DIRS,
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

    # Set DEBUG to False as a default for safety
    # https://docs.djangoproject.com/en/dev/ref/settings/#debug
    DEBUG = strtobool(os.getenv('DJANGO_DEBUG', 'no'))

    # Password Validation
    # https://docs.djangoproject.com/en/2.0/topics/auth/passwords/#module-django.contrib.auth.password_validation
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]

    # Logging
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'django.server': {
                '()': 'django.utils.log.ServerFormatter',
                'format': '[%(server_time)s] %(message)s',
            },
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'django.server': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'django.server',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
            },
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'debug.log',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'propagate': True,
            },
            'django.server': {
                'handlers': ['django.server'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['mail_admins', 'console'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'INFO'
            },
        }
    }

    # Custom user app
    AUTH_USER_MODEL = 'users.User'

    # Django Rest Framework
    REST_FRAMEWORK = {
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': int(os.getenv('DJANGO_PAGINATION_LIMIT', 10)),
        'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
            'rest_framework.renderers.BrowsableAPIRenderer',
        ),
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.SessionAuthentication',
            'rest_framework.authentication.TokenAuthentication',
        )
    }

    # AWS_STORAGE_BUCKET_NAME = 'cdn.halalivery.co.uk'
    # AWS_S3_REGION_NAME = 'eu-west-2'  # e.g. us-east-2
    # AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    # AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    # # Tell django-storages the domain to use to refer to static files.
    # #AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    # AWS_S3_CUSTOM_DOMAIN = 'cdn.halalivery.co.uk'
    #STATICFILES_LOCATION = 'static'
    # STATICFILES_STORAGE = 'custom_storages.StaticStorage'

    # MEDIAFILES_LOCATION = 'media'
    # DEFAULT_FILE_STORAGE = 'custom_storages.MediaStorage'
    # AWS_S3_SECURE_URLS = True

    # MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
    # MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')

    # STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
    # STATIC_URL = os.environ.get('STATIC_URL', '/static/')
    # STATICFILES_DIRS = [
    #     ('assets', os.path.join(PROJECT_ROOT, 'saleor', 'static', 'assets')),
    #     ('favicons', os.path.join(PROJECT_ROOT, 'saleor', 'static', 'favicons')),
    #     ('images', os.path.join(PROJECT_ROOT, 'saleor', 'static', 'images')),
    #     ('dashboard/images', os.path.join(
    #         PROJECT_ROOT, 'saleor', 'static', 'dashboard', 'images'))]
    # STATICFILES_FINDERS = [
    #     'django.contrib.staticfiles.finders.FileSystemFinder',
    #     'django.contrib.staticfiles.finders.AppDirectoriesFinder']

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    def show_toolbar(request):
        if request.user.is_superuser:
            return True
        else:
            return False

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    }

    # CELERY SETTINGS
    # CELERY_BROKER_URL = 'sqs://{0}:{1}@'.format(
    #     urllib.parse.quote_plus(str(AWS_ACCESS_KEY_ID), safe=''),
    #     urllib.parse.quote_plus(str(AWS_SECRET_ACCESS_KEY), safe='')
    # )
    #CELERY_BROKER_URL = urllib.parse.quote(os.getenv('BROKER_URL'), safe='')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('CLOUDAMQP_URL')) or 'sqs://{0}:{1}@'.format(
        urllib.parse.quote_plus(str(AWS_ACCESS_KEY_ID), safe=''),
        urllib.parse.quote_plus(str(AWS_SECRET_ACCESS_KEY), safe='')
    )
    # AWS_ACCESS_KEY_FORMATED = urllib.parse.quote(AWS_ACCESS_KEY_ID, safe='')
    # AWS_SECRET_ACCESS_KEY_FORMATED = urllib.parse.quote(AWS_SECRET_ACCESS_KEY, safe='')
    # CELERY_BROKER_URL = "sqs://{0}:{1}@".format(AWS_ACCESS_KEY_FORMATED, AWS_SECRET_ACCESS_KEY_FORMATED)
    CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_RESULT_BACKEND = 'django-db'
    CELERY_TIMEZONE = 'Europe/London'
    # CELERY_ENABLE_UTC = False
    queue_name_prefix = os.environ.get('QUEUE_NAME_PREFIX', '%s-' % {True: 'dev', False: 'production'}[DEBUG])

    CELERY_BROKER_TRANSPORT_OPTIONS = {'region': 'eu-west-2',
                                       'visibility_timeout': 3600,
                                       'polling_interval': 10,
                                       'queue_name_prefix': queue_name_prefix,
                                       'CELERYD_PREFETCH_MULTIPLIER': 0,
                                       }

    # Payment gateways
    DUMMY = 'dummy'
    BRAINTREE = 'braintree'
    RAZORPAY = 'razorpay'
    STRIPE = 'stripe'

    CHECKOUT_PAYMENT_GATEWAYS = {
        DUMMY: pgettext_lazy('Payment method name', 'Dummy gateway'),
        STRIPE: pgettext_lazy('Payment method name', 'Stripe gateway'),
    }

    PAYMENT_GATEWAYS = {
        STRIPE: {
            'module': 'halalivery.payment.gateways.stripe',
            'connection_params': {
                'public_key': os.environ.get('STRIPE_PUBLIC_KEY'),
                'secret_key': os.environ.get('STRIPE_SECRET_KEY'),
                'store_name': os.environ.get('STRIPE_STORE_NAME', 'Halalivery LTD.'),
                'store_image': os.environ.get('STRIPE_STORE_IMAGE', None),
                'prefill': get_bool_from_env('STRIPE_PREFILL', True),
                'remember_me': os.environ.get('STRIPE_REMEMBER_ME', True),
                'locale': os.environ.get('STRIPE_LOCALE', 'auto'),
                'enable_billing_address': os.environ.get(
                    'STRIPE_ENABLE_BILLING_ADDRESS', False),
                'enable_shipping_address': os.environ.get(
                    'STRIPE_ENABLE_SHIPPING_ADDRESS', False)
            }
        }
    }

    DEFAULT_COUNTRY = os.environ.get('DEFAULT_COUNTRY', 'UK')
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'GBP')
    DEFAULT_DECIMAL_PLACES = get_currency_fraction(DEFAULT_CURRENCY)
    DEFAULT_MAX_DIGITS = 12
    AVAILABLE_CURRENCIES = [DEFAULT_CURRENCY]

    OPENEXCHANGERATES_API_KEY = os.environ.get('OPENEXCHANGERATES_API_KEY', None)

    VATLAYER_ACCESS_KEY = os.environ.get('VATLAYER_ACCESS_KEY')
    VATLAYER_USE_HTTPS = get_bool_from_env('VATLAYER_USE_HTTPS', False)
