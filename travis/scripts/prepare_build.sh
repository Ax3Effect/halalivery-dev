#!/bin/bash

export WORKING_DIR=`pwd`
echo "> Working dir: $WORKING_DIR"
echo "> Getting data..."
git clone git@github.com:Amurmurmur/halalivery-configs.git

# Prepare halalivery-server
if [ "$TRAVIS_BRANCH" == "master" ]
    then
    echo "> Making data dir"
    sudo mv halalivery-configs/halalivery-server/aws/nginx-prod nginx
    sudo mv halalivery-configs/halalivery-server/aws/Dockerrun.aws.prod.json ./Dockerrun.aws.json
    sudo mv halalivery-configs/halalivery-server/newrelic/newrelic.prod.ini ./newrelic.ini
fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then
    echo "> Making data dir"
    sudo mv halalivery-configs/halalivery-server/aws/nginx-qa nginx
    sudo mv halalivery-configs/halalivery-server/aws/Dockerrun.aws.qa.json ./Dockerrun.aws.json
    sudo mv halalivery-configs/halalivery-server/newrelic/newrelic.qa.ini ./newrelic.ini
fi

mv halalivery-configs ../halalivery-configs

git add -A && git commit -m "Add all build artifacts for halalivery-server"
git archive -v -o ./halalivery-server.zip --format=zip HEAD
mv ./halalivery-server.zip ../halalivery-server.zip

rm -rf ./nginx

# Prepare halalivery-worker
if [ "$TRAVIS_BRANCH" == "master" ]
    then
    echo "> Making Dockerrun"
    sudo mv ../halalivery-configs/halalivery-worker/aws/Dockerrun.aws.prod.json ./Dockerrun.aws.json
    #sudo mv ../halalivery-configs/halalivery-worker/aws/worker/* ./
fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then
    echo "> Making Dockerrun"
    sudo mv ../halalivery-configs/halalivery-worker/aws/Dockerrun.aws.qa.json ./Dockerrun.aws.json
    #sudo mv ../halalivery-configs/halalivery-worker/aws/worker/* ./
fi

git add -A && git commit -m "Add all build artifacts for halalivery-worker celery-beat worker."
git archive -v -o ./halalivery-worker.zip --format=zip HEAD
mv ./halalivery-worker.zip ../halalivery-worker.zip