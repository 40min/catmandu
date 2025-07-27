# Echo Cattackle

A funny cattackle that echoes text and generates AI-powered jokes using Google Gemini. Now supports **message accumulation** for improved user experience!

## Features

- **Echo**: Echoes back any text you send (supports both immediate and accumulated parameters)
- **Ping**: Simple ping/pong functionality for testing with parameter information
- **Joke**: Generates funny anekdots (short jokes) about any topic using AI
- **Multi Echo**: Demonstrates multiple accumulated parameters by numbering them
- **Message Accumulation**: Send multiple messages, then execute commands with accumulated parameters

## Commands

- `/echo_echo [text]` - Echoes back the provided text or accumulated messages
- `/echo_ping` - Returns "pong" with parameter information
- `/echo_joke [topic]` - Generates a funny joke about the given topic or first accumulated message
- `/echo_multi_echo` - Shows all accumulated messages with numbers

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
User: /echo_multi_echo
Bot: Multi-echo (3 messages):
1. First message
2. Second message
3. Third message
```

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
User: /echo_multi_echo
Bot: Multi-echo (3 messages):
1. Task 1: Buy groceries
2. Task 2: Walk the dog
3. Task 3: Call mom
```

Note: The joke command requires a valid GEMINI_API_KEY to be configured in the .env file.
