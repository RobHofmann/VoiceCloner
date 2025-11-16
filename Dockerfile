FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    espeak \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone the neutts-air repository to /app
RUN git clone https://github.com/neuphonic/neutts-air.git /app/neutts-air

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/neutts-air/requirements.txt

# Install FastAPI and uvicorn for the API server
RUN pip install --no-cache-dir fastapi uvicorn python-multipart aiofiles

# Copy API server code and static files
COPY api_server.py /app/
COPY static/ /app/static/

# Create directories for models, outputs, and voices
RUN mkdir -p /app/models /app/outputs /app/voices

# Expose port for API
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/neutts-air:$PYTHONPATH
ENV BACKBONE_DEVICE=cpu
ENV CODEC_DEVICE=cpu

# Run the API server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
