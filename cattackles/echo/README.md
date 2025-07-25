# Echo Cattackle

A funny cattackle that echoes text and generates AI-powered jokes using Google Gemini.

## Features

- **Echo**: Echoes back any text you send
- **Ping**: Simple ping/pong functionality for testing
- **Joke**: Generates funny anekdots (short jokes) about any topic using AI

## Commands

- `/echo_echo <text>` - Echoes back the provided text
- `/echo_ping` - Returns "pong"
- `/echo_joke <topic>` - Generates a funny joke about the given topic

## Setup

1. Install dependencies:
   ```bash
   cd cattackles/echo
   uv pip install -r requirements.txt
   ```

2. Configure Google Gemini API:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required for joke functionality)
- `GEMINI_MODEL`: model name
- `LOG_LEVEL`: Logging level (default: INFO)

## Testing

Run tests with:
```bash
uv run pytest cattackles/echo/tests/ -v
```

## Example Usage

```
User: /echo_echo Hello world!
Bot: Hello world!

User: /echo_ping
Bot: pong

User: /echo_joke cats
Bot: Why don't cats play poker in the jungle? Because there are too many cheetahs! 🐱
```

Note: The joke command requires a valid GEMINI_API_KEY to be configured in the .env file.
