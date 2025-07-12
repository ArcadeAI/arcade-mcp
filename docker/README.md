# Arcade Docker Compose Guide

This guide provides detailed instructions on how to set up and run Arcade using Docker Compose.

## Prerequisites

-   **Docker** installed on your system. [Install Docker](https://docs.docker.com/get-docker/)
-   **Docker Compose** installed. It comes bundled with Docker Desktop on Windows and macOS. For Linux, follow the [Docker Compose installation guide](https://docs.docker.com/compose/install/).

## Getting Started

### 1. Clone the Repository

Begin by cloning the Arcade repository:

```bash
git clone https://github.com/ArcadeAI/arcade-ai.git
```

### 2. Build package wheels

From the root of the arcade-ai repository:

```bash
make full-dist
```

### 3. Copy and Configure Environment Variables

Change to the `docker` directory:

```bash
cd arcade-ai/docker
```

Copy the example environment file to `.env`:

```bash
cp env.example .env
```

Open the `.env` file in your preferred text editor and fill in the required values. At a minimum, you **must** provide the `OPENAI_API_KEY`:

```env:.env
### LLM ###

OPENAI_API_KEY=your_openai_api_key_here
```

If you plan to use other Large Language Model (LLM) providers, add their API keys as well:

```env:.env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 4. Run Docker Compose

Start the Arcade services using Docker Compose:

```bash
docker compose up
```

This command will build and start all the services defined in the `docker-compose.yml` file and make their ports available to your host machine.

### 5. Verify the Engine is Running

In a separate terminal window, check if the engine is running:

```bash
curl http://localhost:9099/v1/health
```

You should receive a response indicating that the engine is healthy:

```json
{ "healthy": "true" }
```

Open a browser and navigate to http://localhost:9099/dashboard to view the Arcade dashboard.

## Adding Authentication Providers

Arcade supports various authentication providers. To add an auth provider, follow these steps:

### 1. Enable the Auth Provider in the Configuration

Edit the `docker.engine.yaml` file to enable the desired auth provider. For example, to enable Google authentication, modify the file as follows:

```yaml:docker.engine.yaml
auth:
  providers:
    - id: google
      enabled: true  # Change from false to true
```

### 2. Add Client ID and Secret to the `.env` File

Obtain the client ID and client secret from your auth provider and add them to the `.env` file:

```env:.env
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
```

Repeat this step for any other auth providers you wish to enable.

### 3. Restart the Docker Compose Services

After making changes to the configuration, restart the services:

```bash
docker compose down
docker compose up
```

## Troubleshooting

-   **Engine Health Check Fails**: Ensure that all environment variables are correctly set in the `.env` file and that the services have started without errors.
-   **Port Conflicts**: If the default ports are already in use, modify the ports in the `docker-compose.yml` file.
-   **Authentication Errors**: Double-check the client IDs and secrets provided for auth providers.

NOTE: `arcade login` will not work within a docker container, you must copy your credentials into the container if you would like to use it.
