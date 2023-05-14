#Create ubuntu as base image
FROM python
WORKDIR /

#Install packages
#RUN ["apt-get", "update", "-y"]
#RUN ["apt-get", "install","vim", "python3", "python3-pip",  "ca-certificates" ,"curl", "gnupg" ,"lsb-release", "git" ,"-y"]
RUN ["pip", "install", "pipenv"]
COPY ./ /
RUN ["pipenv", "install", "--system", "--deploy","--ignore-pipfile" ]
CMD gunicorn wsgi:app --config gunicorn_config.py
ENV PYTHONUNBUFFERED 1


