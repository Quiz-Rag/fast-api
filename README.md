# Network Security Project API

A FastAPI-based web API for the Network Security Project.

## Features

- FastAPI web framework
- Health check endpoint
- Interactive API documentation
- Virtual environment setup

## Setup Instructions

### Prerequisites

- Python 3.7+ installed on your system

### Installation

1. **Navigate to the fast-api directory**
   ```bash
   cd fast-api
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Activate virtual environment** (if not already active)
   ```bash
   source venv/bin/activate
   ```

2. **Start the server**
   ```bash
   uvicorn main:app --reload
   ```

3. **Access the API**
   - API Base URL: http://localhost:8000
   - Interactive Documentation: http://localhost:8000/docs
   - Alternative Documentation: http://localhost:8000/redoc

## API Endpoints

- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint

## Development

To stop the server, press `Ctrl+C` in the terminal.

To deactivate the virtual environment:
```bash
deactivate
```