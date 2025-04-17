# Celery Setup for AnyDocAI

AnyDocAI uses Celery for background task processing. This document explains how to set up and use Celery with AnyDocAI.

## Development Setup

For development, AnyDocAI uses a SQLite-based broker for Celery. This eliminates the need for a Redis or RabbitMQ server during development.

### How It Works

1. **SQLite-Based Broker**: Celery tasks are stored in a SQLite database file (`celery/celery.sqlite`)
2. **SQLite-Based Results Backend**: Task results are stored in the same SQLite database
3. **Automatic Database Creation**: The SQLite database is created automatically when the application starts

### Starting the Celery Worker

To start the Celery worker in development mode:

```bash
celery -A config.celery_worker worker --loglevel=info
```

You should see output indicating that the SQLite-based broker is being used:

```
Using SQLite-based broker for Celery (development mode)
```

### Testing Celery

You can test the Celery setup using the provided test script:

```bash
python scripts/test_celery.py
```

This script:
1. Creates a test file
2. Submits a task to process the file
3. Waits for the task to complete
4. Reports the result

## Production Setup

For production, you should use a more robust broker like Redis or RabbitMQ. To configure this:

1. **Install Redis**: Follow the Redis installation instructions for your platform
2. **Update Configuration**: Modify the `celery_worker.py` file to use Redis instead of the file-based broker
3. **Set Environment Variables**: Configure the Redis connection in your environment variables

Example Redis configuration for production:

```python
broker_url = 'redis://localhost:6379/0'
backend_url = 'redis://localhost:6379/0'
```

## Upstash Redis Integration

While AnyDocAI uses Upstash Redis REST API for direct Redis operations, Celery requires the Redis protocol. For production with Upstash:

1. Use the Upstash Redis URL with the Redis protocol (rediss://)
2. Configure SSL settings properly
3. Test thoroughly before deployment

## Troubleshooting

If you encounter issues with Celery:

1. **Check SQLite Database**: Ensure the `celery/celery.sqlite` file exists and is writable
2. **Check Logs**: Look for error messages in the Celery worker logs
3. **Test Tasks**: Use the test script to verify that tasks can be submitted and processed
4. **Check Dependencies**: Ensure SQLAlchemy is installed (`pip install sqlalchemy`)

For more help, refer to the [Celery documentation](https://docs.celeryq.dev/).
