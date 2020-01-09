import os
from .common import Common
import ast
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bool_from_env(name, default_value):
    if name in os.environ:
        value = os.environ[name]
        try:
            return ast.literal_eval(value)
        except ValueError as e:
            raise ValueError(
                '{} is an invalid value for {}'.format(value, name)) from e
    return default_value

class Production(Common):
    INSTALLED_APPS = Common.INSTALLED_APPS
    SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
    # Site
    # https://docs.djangoproject.com/en/2.0/ref/settings/#allowed-hosts
    ALLOWED_HOSTS = ["*"]
    INSTALLED_APPS += ("gunicorn", )

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/2.0/howto/static-files/
    # http://django-storages.readthedocs.org/en/latest/index.html
    INSTALLED_APPS += ('storages',)



    AWS_STORAGE_BUCKET_NAME = 'cdn.halalivery.co.uk'
    AWS_S3_REGION_NAME = 'eu-west-2'  # e.g. us-east-2
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    # Tell django-storages the domain to use to refer to static files.
    #AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    AWS_S3_CUSTOM_DOMAIN = 'cdn.halalivery.co.uk'
    STATICFILES_LOCATION = 'static'
    STATICFILES_STORAGE = 'halalivery.core.storages.S3Boto3Storage'

    MEDIAFILES_LOCATION = 'media'
    DEFAULT_FILE_STORAGE = 'halalivery.core.storages.MediaStorage'
    AWS_S3_SECURE_URLS = True


    # AWS_STORAGE_BUCKET_NAME = 'cdn.halalivery.co.uk'
    # AWS_S3_REGION_NAME = 'eu-west-2'  # e.g. us-east-2
    # AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    # AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    # Tell django-storages the domain to use to refer to static files.
    #AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    # AWS_S3_CUSTOM_DOMAIN = 'cdn.halalivery.co.uk'
    # STATICFILES_LOCATION = 'static'
    # STATICFILES_STORAGE = 'custom_storages.StaticStorage'

    # Amazon S3 configuration
    # AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    # AWS_LOCATION = os.environ.get('AWS_LOCATION', '')
    # AWS_MEDIA_BUCKET_NAME = os.environ.get('AWS_MEDIA_BUCKET_NAME')
    # AWS_MEDIA_CUSTOM_DOMAIN = os.environ.get('AWS_MEDIA_CUSTOM_DOMAIN')
    # AWS_QUERYSTRING_AUTH = get_bool_from_env('AWS_QUERYSTRING_AUTH', False)
    # AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_STATIC_CUSTOM_DOMAIN')
    # AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', None)
    # AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    # AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    # AWS_DEFAULT_ACL = os.environ.get('AWS_DEFAULT_ACL', None)

    # if AWS_STORAGE_BUCKET_NAME:
    #     STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    # if AWS_MEDIA_BUCKET_NAME:
    #     DEFAULT_FILE_STORAGE = 'halalivery.core.storages.S3MediaStorage'
    #     THUMBNAIL_DEFAULT_STORAGE = DEFAULT_FILE_STORAGE


    ANYMAIL = {
        "AMAZON_SES_CLIENT_PARAMS": {
            # example: override normal Boto credentials specifically for Anymail
            "aws_access_key_id": AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
            "region_name": "eu-west-1",
            # override other default options
            "config": {
                "connect_timeout": 30,
                "read_timeout": 30,
            }
        },
    }

    #  Sentry
    SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()])








    '''
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.getenv('DJANGO_AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('DJANGO_AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('DJANGO_AWS_STORAGE_BUCKET_NAME')
    # AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    AWS_DEFAULT_ACL = 'public-read'
    AWS_AUTO_CREATE_BUCKET = True
    AWS_QUERYSTRING_AUTH = False
    # AWS_LOCATION = 'static'
    MEDIA_URL = u'https://s3.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}/'
    # STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
    # STATICFILES_DIRS = [
    #     os.path.join(BASE_DIR, 'halalivery/static'),
    # ]

    # https://developers.google.com/web/fundamentals/performance/optimizing-content-efficiency/http-caching#cache-control
    # Response can be cached by browser and any intermediary caches (i.e. it is "public") for up to 1 day
    # 86400 = (60 seconds x 60 minutes x 24 hours)
    AWS_HEADERS = {
        'Cache-Control': 'max-age=86400, s-maxage=86400, must-revalidate',
    }
    '''
