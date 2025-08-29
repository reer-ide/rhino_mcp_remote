FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy pyproject.toml and uv.lock first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the server
CMD ["python", "-m", "remote_server.server"] 