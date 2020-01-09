FROM python:3.7.3
ENV PYTHONUNBUFFERED 1

#RUN apt-get -y update && apt-get -y upgrade
# RUN apt-get update -y && \
#   # Cleanup apt cache
#   apt-get clean && \
#   rm -rf /var/lib/apt/lists/*

RUN apt-get update -y

# Only when using postgis
RUN apt-get install -y binutils libproj-dev gdal-bin

# Upgrade pip
RUN pip install --upgrade pip
# Allows docker to cache installed dependencies between builds
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Adds our application code to the image
COPY . code
WORKDIR code

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
