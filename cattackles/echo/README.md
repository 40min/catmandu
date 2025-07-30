# Echo Cattackle

A demonstration cattackle that echoes text and generates AI-powered jokes using Google Gemini. This cattackle showcases **message accumulation** functionality and serves as a reference implementation for new cattackles.

## Features

- **Echo**: Echoes back any text you send (supports both immediate and accumulated parameters)
- **Ping**: Simple ping/pong functionality for testing with parameter information
- **Joke**: Generates funny anekdots (short jokes) about any topic using AI
- **Message Accumulation**: Send multiple messages, then execute commands with accumulated parameters

## Commands

- `/echo_echo [text]` - Echoes back the provided text or accumulated messages
- `/echo_ping` - Returns "pong" with parameter information
- `/echo_joke [topic]` - Generates a funny joke about the given topic or first accumulated message

## Message Accumulation Support

This cattackle demonstrates the new message accumulation feature. You can:

1. **Send multiple messages** without commands (they get accumulated)
2. **Execute any command** to use accumulated messages as parameters
3. **Mix immediate and accumulated parameters** (accumulated takes priority)

### Usage Patterns

**Traditional (immediate parameters):**

```
User: /echo_echo Hello world!
Bot: Echo (immediate): Hello world!
```

**New (accumulated parameters):**

```
User: Hello
User: world
User: from
User: accumulator
User: /echo_echo
Bot: Echo (from accumulated): Hello world from accumulator
```

**Multi-parameter demonstration:**

```
User: First message
User: Second message
User: Third message
User: /echo_echo
Bot: First message; Second message; Third message
```

## Running the Echo Cattackle

### Option 1: Running on Host Machine

This is the recommended approach for development and testing individual cattackles.

#### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Running Catmandu core service (see main [README](../../README.md))

#### Setup

1. **Navigate to the cattackle directory:**

   ```bash
   cd cattackles/echo
   ```

2. **Install dependencies:**

   ```bash
   uv pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)**

#### Running

1. **Start the cattackle server:**

   ```bash
   python src/server.py
   ```

   The server will start on port 8001 by default and provide an MCP endpoint for the core service to connect to.

2. **Verify it's running:**

   ```bash
   curl http://localhost:8001/health
   ```

   You should see a health check response.

### Option 2: Running with Docker

This approach runs both the core service and the echo cattackle in containers, which is ideal for production deployments.

#### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

#### Setup

1. **From the project root, set up environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
   ```

2. **Start all services:**

   ```bash
   make docker-up
   # Or directly: docker-compose up -d
   ```

3. **View logs:**

   ```bash
   make docker-logs
   # Or directly: docker-compose logs -f
   ```

The echo cattackle will be automatically discovered and connected to the core service.

For more details on Docker deployment, see the [Docker documentation](../../docs/docker.md).

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required for joke functionality)
- `GEMINI_MODEL`: Gemini model to use (default: gemini-1.5-flash)
- `LOG_LEVEL`: Logging level (default: INFO)
- `MCP_SERVER_PORT`: Port for the MCP server (default: 8001)

## Testing

Run tests with:

```bash
uv run pytest cattackles/echo/tests/ -v
```

## Example Usage

**Traditional usage:**

```
User: /echo_echo Hello world!
Bot: Echo (immediate): Hello world!

User: /echo_ping
Bot: pong

User: /echo_joke cats
Bot: Why don't cats play poker in the jungle? Because there are too many cheetahs! 🐱
```

**With message accumulation:**

```
User: I want to tell you about
User: my favorite animal
User: which is a cat
User: /echo_joke
Bot: Why did the cat sit on the computer? Because it wanted to keep an eye on the mouse! 🐱

User: Task 1: Buy groceries
User: Task 2: Walk the dog
User: Task 3: Call mom
User: /echo_echo
Bot: Task 1: Buy groceries; Task 2: Walk the dog; Task 3: Call mom
```

Note: The joke command requires a valid GEMINI_API_KEY to be configured in the .env file.

## Related Documentation

- **[Main Project README](../../README.md)** - Complete project overview and setup
- **[Docker Deployment](../../docs/docker.md)** - Running with Docker containers
- **[Cattackle Specification](../../architecture/spec/ARCH-cattackle-spec-v1.md)** - How to build your own cattackles
- **[Architecture Overview](../../architecture/)** - System design and architecture
