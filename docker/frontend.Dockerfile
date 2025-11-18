# Frontend Dockerfile for Drishti IC Verification System
FROM node:18-alpine

# Set working directory
WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY frontend ./

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]
