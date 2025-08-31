from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.routers import api_router

# Get redis manager instance from services
from src.services import message_handler_service
from src.utils import logger, redis_manager


redis_manager.set_message_handler(message_handler_service.handle_message)

@asynccontextmanager
async def lifespan(app: FastAPI):

    try:
        # Start Redis subscription
        logger.info("Starting Redis connection and subscription...")
        await redis_manager.connect()

        await redis_manager.start_subscription()

        logger.info("Async Redis subscription started")

        yield
    finally:
        # Cleanup Redis subscription
        logger.info("Stopping Redis subscription and connection...")
        await redis_manager.stop_subscription()
        await redis_manager.disconnect()
        logger.info("Async Redis subscription stopped")

        # Close any other resources that need to be closed
        logger.info("All connections closed, application shutdown complete")


app = FastAPI(
    title="Chat Service",
    version="v1.0.1",
    description="Chat service for question answering",
    lifespan=lifespan,
)

app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081, timeout_keep_alive=1800)