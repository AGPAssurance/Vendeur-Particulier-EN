# base image  
FROM python:3.9   

# setup environment variable  
ENV DockerHOME=/home/app/  

RUN mkdir -p $DockerHOME  

# where your code lives  
WORKDIR $DockerHOME  

# set environment variables  
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1  

# install dependencies  
RUN pip install --upgrade pip  

# copy whole project to your docker home directory. 
COPY ./  $DockerHOME  


# run this command to install all dependencies  
RUN pip install -r requirements.txt  
RUN pip install src/libs/agplib-0.5.3-py3-none-any.whl 

RUN apt-get update -y
RUN apt-get install -y tzdata

ENV TZ America/New_York

# port where the Django app runs  
EXPOSE 8000  

# start server  
CMD python ${DockerHOME}/src/service.py