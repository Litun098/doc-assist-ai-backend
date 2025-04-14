# Using Upstash Redis with AnyDocAI

AnyDocAI can use Upstash Redis as a serverless alternative to running Redis locally. This document explains how to set up and use Upstash Redis with AnyDocAI.

## What is Upstash Redis?

[Upstash](https://upstash.com/) provides serverless Redis with a REST API. This means you don't need to install or manage a Redis server locally or in your deployment environment. Instead, you can use Upstash's HTTP-based API to interact with Redis.

## Setting Up Upstash Redis

1. **Create an Upstash account**:
   - Go to [https://upstash.com/](https://upstash.com/)
   - Sign up for a free account

2. **Create a Redis database**:
   - From the Upstash dashboard, click "Create Database"
   - Choose a name for your database (e.g., "anydocai")
   - Select the region closest to your users
   - Choose the free tier for development
   - Click "Create"

3. **Get your credentials**:
   - From your Upstash dashboard, select your database
   - Go to the "REST API" tab
   - Copy the endpoint URL and token

4. **Update your .env file**:
   ```
   # Upstash Redis REST API
   UPSTASH_REDIS_REST_URL=https://your-endpoint.upstash.io
   UPSTASH_REDIS_REST_TOKEN=your-token-here
   UPSTASH_REDIS_PORT=6379

   # Standard Redis URL (used by Celery)
   # For local Redis (if installed)
   REDIS_URL=redis://localhost:6379/0

   # For Upstash Redis (uncomment to use)
   # REDIS_URL=rediss://:your-token-here@your-endpoint.upstash.io:443?ssl_cert_reqs=CERT_NONE
   ```

## Testing the Connection

You can test your Upstash Redis connection using the provided test script:

```bash
python scripts/test_upstash.py
```

If the connection is successful, you should see output confirming that basic Redis operations (SET, GET, HSET, RPUSH, etc.) are working.

## How It Works

AnyDocAI uses a custom Redis client (`app/services/redis_client.py`) that communicates with Upstash Redis via its REST API. The client follows the Upstash REST API format, which uses URL paths for commands and JSON for data.

For example, to set a key:
```
POST https://your-db.upstash.io/set/mykey
Body: "myvalue"
```

Or to get a key:
```
POST https://your-db.upstash.io/get/mykey
```

This client is used for:

1. **Background Tasks**: Celery uses Redis as a message broker and result backend
2. **Caching**: Temporary storage of processing results and user data
3. **Rate Limiting**: Managing API usage and preventing abuse

The implementation automatically detects if Upstash Redis is configured and uses it instead of a traditional Redis connection.

## Limitations

When using Upstash Redis, be aware of these limitations:

1. **Latency**: REST API calls have higher latency than direct Redis connections
2. **Free Tier Limits**: The free tier has limits on database size and operations
3. **Connection Pooling**: Not available with the REST API

For production use, consider upgrading to a paid Upstash plan or using a traditional Redis deployment.

## Troubleshooting

If you encounter issues with Upstash Redis:

1. **Check your credentials**: Ensure your endpoint URL and token are correct
2. **Verify network access**: Make sure your environment can access the Upstash API
3. **Check rate limits**: The free tier has limits on the number of requests
4. **Enable debug logging**: Set `DEBUG=True` in your .env file for more detailed logs
5. **SSL Issues with Celery**: If you see SSL errors with Celery, make sure your Redis URL includes `?ssl_cert_reqs=CERT_NONE`
6. **REST API Format**: Upstash REST API expects commands in a specific format - make sure you're using the updated client

### Common Errors

- **"Command is not available"**: This usually means the REST API request format is incorrect
- **"A rediss:// URL must have parameter ssl_cert_reqs"**: Add `?ssl_cert_reqs=CERT_NONE` to your Redis URL
- **Connection timeouts**: Check your network configuration and firewall settings

For more help, refer to the [Upstash documentation](https://docs.upstash.com/).
