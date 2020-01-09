#!/bin/bash
# set -ev
# if [ "$TRAVIS_BRANCH" == "master" ]
#     then
#     rm -rf Dockerrun.aws.qa.json
#     mv Dockerrun.aws.prod.json Dockerrun.aws.json
#     rm -rf nginx/conf.d/halalivery.co.uk.qa.conf
# fi
# if [ "$TRAVIS_BRANCH" == "qa" ]
#     then
#     rm -rf Dockerrun.aws.prod.json
#     mv Dockerrun.aws.qa.json Dockerrun.aws.json
#     rm -rf nginx/conf.d/halalivery.co.uk.prod.conf
# fi

if [ "$TRAVIS_BRANCH" == "master" ]
    then
    rm -rf Dockerrun.aws.qa.json
    mv Dockerrun.aws.prod.json Dockerrun.aws.json
    rm -rf nginx/conf.d/halalivery.co.uk.prod.conf
fi
if [ "$TRAVIS_BRANCH" == "qa" ]
    then
    rm -rf Dockerrun.aws.prod.json
    mv Dockerrun.aws.qa.json Dockerrun.aws.json
    rm -rf nginx/conf.d/halalivery.co.uk.qa.conf
fi