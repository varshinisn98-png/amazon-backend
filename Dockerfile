# Step 1: Use an official lightweight Python image as base
FROM python:3.10-slim

# Step 2: Set environment variables to prevent bytecode and buffer outputs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Step 3: Set the working directory inside the container
WORKDIR /app

# Step 4: Copy requirements file to leverage Docker layer caching
COPY requirements.txt /app/

# Step 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Copy application code into container
COPY . /app/

# Step 7: Expose port 8000 for FastAPI application
EXPOSE 8000

# Step 8: Command to start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
