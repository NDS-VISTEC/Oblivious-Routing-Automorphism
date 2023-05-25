# Indicate the Python image
FROM python:3.8

# Set the application directory
WORKDIR /app

# Install the application dependencies
ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Command used to start the application
CMD ["python","main.py"]