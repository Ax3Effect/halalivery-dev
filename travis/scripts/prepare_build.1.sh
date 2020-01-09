#!/bin/bash

export WORKING_DIR=`pwd`
echo "> Working dir: $WORKING_DIR"
echo "> Getting data..."
git clone git@github.com:Amurmurmur/halalivery-configs.git

# Prepare halalivery-server
if [ "$TRAVIS_BRANCH" == "master" ]
    then
    echo "> Making data dir"
    sudo mv halalivery-configs/halalivery-server/aws/nginx-prod ./nginx
    sudo mv halalivery-configs/halalivery-server/aws/Dockerrun.aws.prod.json ./Dockerrun.aws.json
    sudo mv halalivery-configs/halalivery-server/newrelic/newrelic.prod.ini ./newrelic.ini
fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then
    echo "> Making data dir"
    sudo mv halalivery-configs/halalivery-server/aws/nginx-qa ./nginx
    sudo mv halalivery-configs/halalivery-server/aws/Dockerrun.aws.qa.json ./Dockerrun.aws.json
    sudo mv halalivery-configs/halalivery-server/newrelic/newrelic.qa.ini ./newrelic.ini
fi

mv halalivery-configs ../halalivery-configs

git add -A && git commit -m "Add all build artifacts"
git archive -v -o ./travis-${TRAVIS_COMMIT}-${EPOCH}.zip --format=zip HEAD
mv ./travis-${TRAVIS_COMMIT}-${EPOCH}.zip ../travis-${TRAVIS_COMMIT}-${EPOCH}.zip

# Prepare halalivery-worker
if [ "$TRAVIS_BRANCH" == "master" ]
    then
    echo "> Making data dir"
    sudo mv ../halalivery-configs/halalivery-worker/aws/Dockerrun.aws.prod.json ./Dockerrun.aws.json
fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then
    echo "> Making data dir"
    sudo mv ../halalivery-configs/halalivery-worker/aws/Dockerrun.aws.qa.json ./Dockerrun.aws.json
fi

git add -A && git commit -m "Add all build artifacts"
git archive -v -o ./travis-${TRAVIS_BUILD_NUMBER}-${EPOCH}-celery-beat.zip --format=zip HEAD
mv ./travis-${TRAVIS_BUILD_NUMBER}-${EPOCH}-celery-beat.zip ../travis-${TRAVIS_BUILD_NUMBER}-${EPOCH}-celery-beat.zip
#git archive -v -o ${TRAVIS_BUILD_DIR}${REPO}-${BUILD_ENV}-${TRAVIS_TAG}-${TRAVIS_BUILD_NUMBER}-celery-beat.zip --format=zip HEAD