#!/bin/bash

# Define variables
REPO_URL="https://github.com/jjmartinr01/gauss3"
BRANCH="develop"
LOCAL_DIR="/var/www/python/gauss3/"
DOCKER_COMPOSE_FILE="$LOCAL_DIR/docker-compose.yml"
LOG_FILE="/var/log/deploy_gauss3.log"

# Ensure the script is run as a privileged user
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or use sudo" | tee -a $LOG_FILE
  exit 1
fi

# Log the start of the deployment
echo "$(date): Starting deployment" | tee -a $LOG_FILE

# Pull the latest code from the repository
if [ ! -d "$LOCAL_DIR" ]; then
  git clone -b $BRANCH $REPO_URL $LOCAL_DIR | tee -a $LOG_FILE
else
  cd $LOCAL_DIR
  git fetch origin | tee -a $LOG_FILE
  git pull origin/$BRANCH | tee -a $LOG_FILE
fi

# Navigate to the project directory
cd $LOCAL_DIR

# Build and deploy the Docker Compose setup
docker-compose -f $DOCKER_COMPOSE_FILE down | tee -a $LOG_FILE
docker-compose -f $DOCKER_COMPOSE_FILE pull | tee -a $LOG_FILE
docker-compose -f $DOCKER_COMPOSE_FILE build | tee -a $LOG_FILE
docker-compose -f $DOCKER_COMPOSE_FILE up -d --remove-orphans | tee -a $LOG_FILE

# Log the completion of the deployment
echo "$(date): Deployment completed" | tee -a $LOG_FILE
