# Notion Cattackle

A Catmandu cattackle that enables users to save Telegram messages directly to Notion pages organized by date.

## Features

- Save messages to daily Notion pages using `/to_notion` command
- Automatic page creation with date-based organization
- User-specific configuration for authentication and workspace paths
- Silent skip for unconfigured users

## Configuration

User configurations are managed through a Python configuration module that maps usernames to Notion tokens and workspace paths.

## Commands

- `/to_notion [message content]` - Save message content to today's Notion page

## Requirements

- Python 3.12+
- Notion integration token
- Configured workspace path for each user
