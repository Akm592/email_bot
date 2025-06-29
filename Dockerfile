# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
# First, copy only requirements.txt to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port your Gradio app runs on
EXPOSE 7860

# Define environment variables (if any, e.g., for production)
# ENV NAME YourName

# Run app.py when the container launches
CMD ["python", "app.py"]
