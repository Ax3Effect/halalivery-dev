#!/bin/bash

if [ "$TRAVIS_BRANCH" == "master" ]
    then

    # Build server
    docker build -t halalivery-server -f Dockerfile .

    # Build nginx
    docker build -t halalivery-server-nginx -f ./nginx/Dockerfile ./nginx/
    
    # Build celery
    docker build -t halalivery-server-celery -f Dockerfile .
    docker build -t halalivery-worker-celery-beat -f Dockerfile .

    eval $(aws ecr get-login --no-include-email --region eu-west-2)
    docker tag halalivery-server:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server:latest
    docker tag halalivery-server-nginx:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx:latest

    # Push celery
    docker tag halalivery-server-celery:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-celery:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-celery:latest

    docker tag halalivery-worker-celery-beat:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-worker-celery-beat:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-worker-celery-beat:latest

fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then

    # Build Server
    docker build -t halalivery-server-qa -f Dockerfile .
    # Build Nginx
    docker build -t halalivery-server-nginx-qa -f ./nginx/Dockerfile ./nginx/
    # Build celery
    docker build -t halalivery-server-celery-qa -f Dockerfile .
    # Builld celery beat worker
    docker build -t halalivery-worker-celery-beat-qa -f Dockerfile .

    # Login into the Docker ECR
    eval $(aws ecr get-login --no-include-email --region eu-west-2)
    
    # Push Server
    docker tag halalivery-server-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-qa:latest
    
    # Push Nginx
    docker tag halalivery-server-nginx-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx-qa:latest

    # Push celery
    docker tag halalivery-server-celery-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-celery-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-celery-qa:latest

    # Push celery background worker
    docker tag halalivery-worker-celery-beat-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-worker-celery-beat-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-worker-celery-beat-qa:latest
fi