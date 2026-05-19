# Start from official Node image
FROM node:20-slim

# Set working directory inside the container
WORKDIR /app

# Copy package files first (Docker caches this layer)
# If packages don't change, Docker won't reinstall them
COPY package.json package-lock.json ./

# Install Node dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Expose port 5173 (Vite's default port)
EXPOSE 5173

# Start Vite dev server
# --host makes it accessible outside the container
CMD ["npm", "run", "dev", "--", "--host"]