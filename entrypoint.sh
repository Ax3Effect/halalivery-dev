#!/bin/bash

create_superuser="
import django
django.setup()
from django.contrib.auth.models import User
try:
    User.objects.create_superuser('$DJANGO_SUPERUSER_NAME', '$DJANGO_SUPERUSER_MAIL', '$DJANGO_SUPERUSER_PASS')
except Exception:
    pass
"
create_superuser() {
    if [ -z "$DJANGO_SUPERUSER_NAME" ] || [ -z "$DJANGO_SUPERUSER_MAIL" ] || [ -z "$DJANGO_SUPERUSER_PASS" ]; then
        echo "Environment variables for database not set, not creating superuser."
    else
        echo "Creating superuser"
        python -c "$create_superuser"
    fi
}

wait_for_db() {
    if [ -z "$DJANGO_DB_HOST" ] || [ -z "$DJANGO_DB_PORT" ]; then
        echo "No django database host or port, not waiting for db."
    else
        echo "Waiting for database"
        dockerize -wait tcp://"$DJANGO_DB_HOST":"$DJANGO_DB_PORT" -timeout 30s
    fi
}

if [ "$1" == "runserver" ]; then
    # No reason to wait for a DB
    # wait_for_db

    echo "Running migrations"
    # Apply database migrations
    python manage.py migrate
    # Collect static files
    echo "Running collectstatic"
    python manage.py collectstatic --noinput

    # echo "Start crons"
    # Run the command on container startup

    #create_superuser
    #exec python manage.py "$@"
    #exec "$@"
    newrelic-admin run-program gunicorn --bind 0.0.0.0:8000 --access-logfile - halalivery.wsgi:application
fi

if [ "$1" == "resetdb" ]; then
    # No reason to wait for a DB
    # wait_for_db

    #python manage.py reset_db --router=default --noinput
    python manage.py reset_db --noinput

    echo "Running migrations"
    # Apply database migrations
    python manage.py migrate
    # Collect static files
    echo "Running collectstatic"
    python manage.py collectstatic --noinput

    newrelic-admin run-program gunicorn --bind 0.0.0.0:8000 --access-logfile - halalivery.wsgi:application
fi

if [ "$1" == "nomigrate" ]; then
    wait_for_db

    echo "Running collectstatic"
    python manage.py collectstatic --noinput

    create_superuser

    exec python manage.py runserver "${@:2}"
fi

if [ "$1" == "migrate" ]; then
    wait_for_db

    echo "Running migrations"
    # Apply database migrations
    python manage.py "$@"
fi

if [ "$1" == "makemigrations" ];then
    wait_for_db
    exec python manage.py "$@"
fi

if [ "$1" == "loadtestdata" ];then
    wait_for_db
    exec python manage.py "$@"
fi

if [ "$1" == "celery" ];then
    celery -A halalivery worker --app=halalivery.celeryconf:app --loglevel=info
fi

if [ "$1" == "celerybeat" ];then
    celery -A halalivery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler --quiet
fi

exec "$@"