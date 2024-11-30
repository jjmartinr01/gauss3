FROM nginx:1.25

# Install htpasswd (part of apache2-utils)
RUN apt-get update && apt-get install -y apache2-utils && rm -rf /var/lib/apt/lists/*

# Define the ARG variables for user and password
ARG USER
ARG PASSWORD

# Remove the default nginx configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration file
COPY scripts/nginx.conf /etc/nginx/conf.d

# Create the .htpasswd file with the provided user and password
RUN htpasswd -cb /etc/nginx/.htpasswd ${USER} ${PASSWORD}

# Expose ports (if needed, depending on your configuration)
EXPOSE 80 443
