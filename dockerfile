# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory to /app
WORKDIR /app

# Create a virtual environment and activate it
RUN python -m venv venv
RUN /bin/bash -c "source venv/bin/activate"

# Copy the requirements file into the container at /app
COPY requirements.txt /app

# Install PyAudio
RUN apt-get update && \
    apt-get install -y portaudio19-dev && \
    pip install -r requirements.txt 

# Copy the current directory contents into the container at /app
COPY . /app

EXPOSE 7500
# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# Define the command to run your application
CMD ["python3", "main.py"]
