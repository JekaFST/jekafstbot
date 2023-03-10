FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine
RUN apk --update add bash nano
ENV STATIC_URL /static
ENV STATIC_PATH /var/www/app/static
COPY ./requirements.txt /var/www/requirements.txt
RUN apk add build-base linux-headers
RUN pip3 install --upgrade pip setuptools wheel -r /var/www/requirements.txt