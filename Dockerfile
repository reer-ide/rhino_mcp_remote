FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install uv

# Copy pyproject.toml and uv.lock first for better caching
COPY pyproject.toml uv.lock README.md LICENSE ./ 

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set host to 0.0.0.0 for cloud deployment
ENV HOST=0.0.0.0

# Run the server using uv run to ensure proper virtual environment activation
CMD ["uv", "run", "python", "remote_server/server.py"]
