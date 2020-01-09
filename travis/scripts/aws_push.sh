#!/bin/bash

if [[ "$TRAVIS_BRANCH" == "master" ]] && [[ "$TRAVIS_COMMIT_MESSAGE" != *"[skip build]"* ]]; then
    # Build Server
    docker build -t halalivery-server -f Dockerfile .

    # Build Nginx
    docker build -t halalivery-server-nginx -f ./nginx/Dockerfile ./nginx/

    # Login into the Docker ECR
    eval $(aws ecr get-login --no-include-email --region eu-west-2)
    
    # Push Server
    docker tag halalivery-server:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server:latest
    
    # Push Nginx
    docker tag halalivery-server-nginx:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx:latest
fi

if [[ "$TRAVIS_BRANCH" == "qa" ]] && [[ "$TRAVIS_COMMIT_MESSAGE" != *"[skip build]"* ]]; then
    # Build Server
    docker build -t halalivery-server-qa -f Dockerfile .
    
    # Build Nginx
    docker build -t halalivery-server-nginx-qa -f ./nginx/Dockerfile ./nginx/

    # Login into the Docker ECR
    eval $(aws ecr get-login --no-include-email --region eu-west-2)
    
    # Push Server
    docker tag halalivery-server-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-qa:latest
    
    # Push Nginx
    docker tag halalivery-server-nginx-qa:latest ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx-qa:latest
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-2.amazonaws.com/halalivery-server-nginx-qa:latest
fi