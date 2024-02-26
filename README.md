# Running Gauss with Docker

This guide outlines the steps to run the application using Docker. Docker provides a convenient way to package your application and its dependencies into a container, ensuring consistency across different environments.

## Prerequisites

- Docker installed on your system. You can download and install Docker from [here](https://docs.docker.com/get-docker/).

## Steps

### 1. Clone the Repository

Clone your Django application repository from GitHub or any other source.

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Add settings.py
Add the settings.py file in the gauss directory

### 3. Configure Environment Variables

Create a `.env` file in the project root directory and define environment variables required for your application. 

```plaintext
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_USER=your_postgres_deault_user
POSTGRES_DB=your_postgres_deault_database
RABBITMQ_DEFAULT_VHOST=your_rabbitmq_vhost
RABBITMQ_DEFAULT_USER=your_rabbitmq_user
RABBITMQ_DEFAULT_PASS=your_rabbitmq_password

```

### 4. Build Docker Images

Run the following command to build Docker images for your application:

```bash
docker-compose build
```

### 5. Start Docker Containers

Once the images are built, start the Docker containers:

```bash
docker-compose up -d
```

This command will start the containers in detached mode, meaning they will run in the background.

### 6. Access Your Application

You can now access your Django application at `http://localhost:1337` in your web browser. 

### 7. Additional Commands

- To stop the containers, run:

  ```bash
  docker-compose down
  ```

- To view logs of a specific container, run:

  ```bash
  docker-compose logs <container-name>
  ```

- To create first migration, run
  ```bash
  docker exec -it <name-gauss-container> bash
  ```
  Then inside the container
  ```bash
  /cleanMigration.sh
  ```

Replace `<container-name>` with the name of the container whose logs you want to view.
