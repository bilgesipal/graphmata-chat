"""
Async Redis Manager module for Chat Service
Handles Redis connection, subscription, and message processing using redis.asyncio

EN: This module manages Redis connections and subscriptions for the Chat Service using fully async operations.
    It provides a clean interface for subscribing to Redis channels and processing messages without blocking.

TR: Bu modül, tamamen async işlemler kullanarak Sohbet Servisi için Redis bağlantılarını ve aboneliklerini yönetir.
    Redis kanallarına abone olmak ve mesajları engellemeden işlemek için temiz bir arayüz sağlar.
"""

import asyncio
import json
import os
import sys
from typing import Callable, Dict, Any, Optional

import redis.asyncio as redis

from src.config.config import AppConfig
from src.utils import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AsyncRedisManager:
    """
    Manages async Redis connection and subscriptions

    EN: This class handles the Redis connection and subscription lifecycle using async operations.
        It provides methods to start and stop subscriptions, and process incoming messages.
        All operations are non-blocking and integrate seamlessly with FastAPI's async event loop.

    TR: Bu sınıf, async işlemler kullanarak Redis bağlantısını ve abonelik yaşam döngüsünü yönetir.
        Abonelikleri başlatmak ve durdurmak, ve gelen mesajları işlemek için metodlar sağlar.
        Tüm işlemler engelleyici değildir ve FastAPI'nin async olay döngüsü ile sorunsuz entegre olur.
    """

    def __init__(self):
        """
        Initialize the async Redis manager

        EN: Creates an async Redis client with configuration from environment and initializes state variables.

        TR: Ortam değişkenlerinden yapılandırma ile bir async Redis istemcisi oluşturur ve durum değişkenlerini başlatır.
        """
        self.redis_client = None
        self.pubsub = None
        self.subscription_task = None
        self.message_handler = None
        self._running = False

    async def connect(self):
        """Establish connection to Redis with retry logic"""
        retry_count = 0
        max_retries = 3

        logger.info(
            f"Connecting to Redis with: host={AppConfig.REDIS_HOST}, port={AppConfig.REDIS_PORT}, db={AppConfig.REDIS_DB}"
        )

        while retry_count < max_retries:
            try:
                # self.redis_client = redis.Redis(
                #     host=AppConfig.REDIS_HOST,
                #     port=int(AppConfig.REDIS_PORT),
                #     db=int(AppConfig.REDIS_DB),
                #     decode_responses=True,
                #     socket_timeout=60.0,  # Add timeout
                #     socket_connect_timeout=60.0,  # Add connect timeout
                # )

                self.redis_client = redis.Redis(
                    host=AppConfig.REDIS_HOST,
                    port=int(AppConfig.REDIS_PORT),
                    db=int(AppConfig.REDIS_DB),
                    decode_responses=True,
                    socket_timeout=300.0,  # Eski: 60.0
                    socket_connect_timeout=60.0,
                    socket_keepalive=True,  # Yeni eklenen
                    retry_on_timeout=True,  # Yeni eklenen
                    health_check_interval=30,  # Yeni eklenen
                )
                # Test connection
                await self.redis_client.ping()
                logger.info(f"Redis connection established to {AppConfig.REDIS_HOST}")
                return
            except Exception as e:
                retry_count += 1
                logger.warning(f"Redis connection attempt {retry_count} failed: {e}")
                if retry_count >= max_retries:
                    logger.error(
                        f"Failed to connect to Redis after {max_retries} attempts"
                    )
                    raise
                await asyncio.sleep(1)  # Wait before retry

    async def disconnect(self):
        """
        Close Redis connection

        EN: Properly closes the Redis connection and cleans up resources.

        TR: Redis bağlantısını düzgün bir şekilde kapatır ve kaynakları temizler.
        """
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    def set_message_handler(self, handler: Callable):
        """
        Set the callback function for handling messages

        EN: Registers a callback function that will be invoked when messages are received.
            This function should be an async function that processes the message content.

        TR: Mesajlar alındığında çağrılacak bir geri çağırma işlevini kaydeder.
            Bu işlev, mesaj içeriğini işleyen bir async fonksiyon olmalıdır.

        Args:
            handler: The async function to call when a message is received
        """
        # EN: Store the handler function to be called when a message is received from Redis.
        #     This creates the connection between Redis events and our business logic.
        # TR: Redis'ten bir mesaj alındığında çağrılacak işlev fonksiyonunu saklar.
        #     Bu, Redis olayları ile iş mantığımız arasındaki bağlantıyı oluşturur.
        self.message_handler = handler

    async def handle_redis_message(self, message):
        """
        Handle messages from Redis channel

        EN: This async function is called when a message is received from Redis.
            It checks the message type and passes the data to the registered message handler.
            Since this is already running in the same event loop as FastAPI, we can directly await
            the message handler without any thread safety concerns.

        TR: Bu async fonksiyon, Redis'ten bir mesaj alındığında çağrılır.
            Mesaj türünü kontrol eder ve verileri kayıtlı mesaj işleyicisine aktarır.
            Bu zaten FastAPI ile aynı olay döngüsünde çalıştığı için, herhangi bir thread güvenliği
            endişesi olmadan mesaj işleyiciyi doğrudan await edebiliriz.

        Args:
            message: The message received from Redis
        """
        try:
            # Skip non-message types (like subscription confirmations)
            if message["type"] != "message":
                return

            # Get the message data
            data = message["data"]
            logger.info(f"Received message from Redis channel: {message['channel']}")

            # Process the message using the registered handler
            if self.message_handler:
                # Pass the raw message data to the handler
                task = asyncio.create_task(
                    self.message_handler(data)
                )  # create_task: Message handling without blocking event loop

                # Optional: Add task to a set to prevent garbage collection
                # and log completion (for monitoring purposes)
                task.add_done_callback(
                    lambda t: (
                        logger.info(f"Message processing completed")
                        if not t.exception()
                        else logger.error(f"Message processing failed: {t.exception()}")
                    )
                )

            else:
                logger.error("No message handler registered")

        except Exception as e:
            logger.error(f"Error processing Redis message: {e}")

    # async def _subscription_loop(self):
    #     """
    #     Main subscription loop that listens for Redis messages

    #     EN: This is the heart of the async Redis subscription system.
    #         It continuously listens for messages and processes them as they arrive.
    #         The loop runs until _running is set to False.

    #         Key advantages over threading approach:
    #         1. Runs in the same event loop as FastAPI
    #         2. No thread synchronization issues
    #         3. Better error handling and logging
    #         4. More efficient resource usage
    #         5. Easier to test and debug

    #     TR: Bu, async Redis abonelik sisteminin kalbidir.
    #         Sürekli olarak mesajları dinler ve geldikçe işler.
    #         Döngü, _running False olana kadar çalışır.

    #         Threading yaklaşımına göre temel avantajları:
    #         1. FastAPI ile aynı olay döngüsünde çalışır
    #         2. Thread senkronizasyon sorunları yok
    #         3. Daha iyi hata işleme ve loglama
    #         4. Daha verimli kaynak kullanımı
    #         5. Test etmesi ve debug etmesi daha kolay
    #     """
    #     try:
    #         async for message in self.pubsub.listen():
    #             if not self._running:
    #                 break
    #             await self.handle_redis_message(message)
    #     except asyncio.CancelledError:
    #         logger.info("Redis subscription loop cancelled")
    #     except Exception as e:
    #         logger.error(f"Error in Redis subscription loop: {e}")
    #     finally:
    #         logger.info("Redis subscription loop ended")

    async def _subscription_loop(self):
        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                await self.handle_redis_message(message)
        except asyncio.CancelledError:
            logger.info("Redis subscription loop cancelled")
        except Exception as e:
            logger.error(f"Error in Redis subscription loop: {e}")
            # Bağlantı hatası durumunda 5 saniye bekleyip yeniden bağlan
            if "connecting to" in str(e) or "timeout" in str(e).lower():
                logger.info("Connection lost, attempting to reconnect in 5 seconds...")
                await asyncio.sleep(5)
                if self._running:
                    try:
                        await self.connect()
                        self.pubsub = self.redis_client.pubsub()
                        await self.pubsub.subscribe(AppConfig.REDIS_LISTEN_CHAT)
                        logger.info(
                            "Reconnected successfully, restarting subscription loop"
                        )
                        # Kendini yeniden çağır
                        await self._subscription_loop()
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed: {reconnect_error}")
        finally:
            logger.info("Redis subscription loop ended")

    async def start_subscription(self):
        """
        Start Redis subscription

        EN: This method starts the Redis PubSub subscription using async operations.
            Instead of creating a separate thread, it creates an asyncio Task that runs
            concurrently with other async operations in the same event loop.

            Benefits of this approach:
            1. No thread overhead
            2. Better integration with FastAPI's lifecycle
            3. Easier error propagation and handling
            4. More predictable behavior
            5. Better resource management

        TR: Bu metod, async işlemler kullanarak Redis PubSub aboneliğini başlatır.
            Ayrı bir thread oluşturmak yerine, aynı olay döngüsünde diğer async işlemlerle
            eşzamanlı olarak çalışan bir asyncio Task oluşturur.

            Bu yaklaşımın faydaları:
            1. Thread overhead'i yok
            2. FastAPI'nin yaşam döngüsü ile daha iyi entegrasyon
            3. Daha kolay hata yayılımı ve işleme
            4. Daha öngörülebilir davranış
            5. Daha iyi kaynak yönetimi

        Returns:
            The subscription task
        """
        try:
            if not self.redis_client:
                await self.connect()

            # Create pubsub instance
            self.pubsub = self.redis_client.pubsub()

            # EN: Subscribe to the Redis channel specified in AppConfig.REDIS_SUBSCRIBE.
            #     This is where our application will listen for incoming messages.
            # TR: AppConfig.REDIS_SUBSCRIBE'da belirtilen Redis kanalına abone olur.
            #     Uygulamamız gelen mesajları bu kanaldan dinleyecektir.
            await self.pubsub.subscribe(AppConfig.REDIS_LISTEN_CHAT)

            logger.info(f"Subscribed to Redis channel: {AppConfig.REDIS_LISTEN_CHAT}")

            # Start the subscription loop as an asyncio task

            # ====================== ASYNCIO TASK EXPLANATION ======================
            # asyncio.create_task() schedules the coroutine to run on the event loop
            # and returns a Task object that represents the execution of the coroutine.
            #
            # How it works:
            # 1. The _subscription_loop() coroutine is submitted to the current event loop
            # 2. The event loop will run this task concurrently with other tasks
            # 3. No new threads are created - everything runs in the same event loop
            # 4. The task starts immediately but doesn't block this function
            #
            # Benefits:
            # - True concurrency without threads (cooperative multitasking)
            # - More efficient than threads (no context switching overhead)
            # - Tasks share the same memory space safely without locks
            # - We can await, cancel, or check the status of this task later
            #
            # In this specific case:
            # The subscription loop will run "in the background" while the FastAPI
            # app continues to handle HTTP requests. When Redis messages arrive,
            # they'll be processed by the event loop without blocking other operations.
            #
            # ====================== ASYNCIO TASK AÇIKLAMASI ======================
            # asyncio.create_task(), coroutine'i olay döngüsünde çalışacak şekilde zamanlar
            # ve coroutine'in yürütülmesini temsil eden bir Task nesnesi döndürür.
            #
            # Nasıl çalışır:
            # 1. _subscription_loop() coroutine'i mevcut olay döngüsüne gönderilir
            # 2. Olay döngüsü bu görevi diğer görevlerle eşzamanlı olarak çalıştırır
            # 3. Yeni thread'ler oluşturulmaz - her şey aynı olay döngüsünde çalışır
            # 4. Görev hemen başlar ancak bu fonksiyonu engellemez
            #
            # Faydaları:
            # - Thread'ler olmadan gerçek eşzamanlılık (işbirlikçi çoklu görev)
            # - Thread'lerden daha verimli (bağlam geçiş yükü yok)
            # - Görevler bellek alanını kilitler olmadan güvenli bir şekilde paylaşır
            # - Bu görevi daha sonra bekleyebilir, iptal edebilir veya durumunu kontrol edebiliriz

            self._running = True

            # EN: Create an asyncio task for the subscription loop that will run concurrently with other operations.
            #     This is a key part of the async design - it allows our application to listen for Redis messages
            #     while simultaneously handling HTTP requests and other tasks, all in the same event loop.
            # TR: Abonelik döngüsü için diğer işlemlerle eşzamanlı olarak çalışacak bir asyncio görevi oluştur.
            #     Bu, async tasarımın önemli bir parçasıdır - uygulamamızın Redis mesajlarını dinlerken
            #     aynı zamanda HTTP isteklerini ve diğer görevleri, hepsini aynı olay döngüsünde işlemesine olanak tanır.
            self.subscription_task = asyncio.create_task(self._subscription_loop())

            return self.subscription_task

        except Exception as e:
            logger.error(f"Error starting Redis subscription: {e}")
            return None

    async def stop_subscription(self):
        """
        Stop the Redis subscription

        EN: Safely stops the Redis subscription and cleans up resources.
            This ensures clean shutdown when the application stops.

        TR: Redis aboneliğini güvenli bir şekilde durdurur ve kaynakları temizler.
            Bu, uygulama durduğunda temiz bir kapatma sağlar.
        """
        self._running = False

        if self.subscription_task:
            self.subscription_task.cancel()
            try:
                await self.subscription_task
            except asyncio.CancelledError:
                pass
            self.subscription_task = None

        if self.pubsub:
            await self.pubsub.unsubscribe(AppConfig.REDIS_LISTEN_CHAT)
            await self.pubsub.close()
            self.pubsub = None

        logger.info("Redis subscription stopped")

    async def ping(self):
        """
        Check Redis connection by sending a ping command

        EN: This method sends a ping command to Redis and returns the response.
            Used for health checks to verify the Redis connection is working.

        TR: Bu metod Redis'e bir ping komutu gönderir ve yanıtı döndürür.
            Redis bağlantısının çalıştığını doğrulamak için sağlık kontrollerinde kullanılır.

        Returns:
            bool: True if the ping was successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            response = await self.redis_client.ping()
            return response
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def publish(self, channel: str, message: str):
        """
        Publish a message to a Redis channel

        EN: This method publishes a message to the specified Redis channel.
            Used for sending data to Redis for other services to consume.
            Also used for health checks to verify pub/sub functionality.

        TR: Bu metod belirtilen Redis kanalına bir mesaj yayınlar.
            Diğer servislerin tüketmesi için Redis'e veri göndermek için kullanılır.
            Ayrıca pub/sub işlevselliğini doğrulamak için sağlık kontrollerinde de kullanılır.

        Args:
            channel (str): The channel to publish to
            message (str): The message to publish

        Returns:
            int: The number of clients that received the message
        """
        try:
            if not self.redis_client:
                await self.connect()

            result = await self.redis_client.publish(channel, message)
            return result
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")
            raise

    def get_client(self):
        """
        Get the Redis client instance

        EN: This method returns the current Redis client instance.
            It can be used to perform direct Redis operations outside of the subscription context.

        TR: Bu metod mevcut Redis istemci örneğini döndürür.
            Abonelik bağlamı dışında doğrudan Redis işlemleri gerçekleştirmek için kullanılabilir.

        Returns:
            redis.Redis: The Redis client instance
        """
        return self.redis_client


    async def add_stream(
            self,
            stream_key: str,
            fields: Dict[str, Any],
            max_len: int = 1000,
            timeout: float = 5.0,
    ) -> Optional[str]:
        """
        Add a message to a Redis Stream in a robust, structured way.

        EN:
        This method adds a message to a Redis Stream with JSON-encoded payload under the "data" field.
        It uses maxlen and approximate trimming for memory control and includes timeout handling.

        TR:
        Bu metod, Redis Stream'e JSON formatında ve "data" alanı altında mesaj ekler.
        Bellek yönetimi için maxlen ve approximate kullanır. Zaman aşımı yönetimi dahildir.

        Args:
            stream_key (str): Stream'e mesajın ekleneceği Redis anahtarı
            fields (Dict[str, Any]): Mesaj içeriği (JSON'a dönüştürülecek)
            max_len (int): Stream'in maksimum uzunluğu (FIFO trimming)
            timeout (float): XADD işlemi için zaman aşımı (saniye)

        Returns:
            Optional[str]: Eklenen mesajın Redis ID'si, ya da None (başarısızlık durumunda)
        """
        try:
            # Redis bağlantısı kontrolü
            if not self.redis_client:
                await self.connect()
                if not self.redis_client:
                    raise RuntimeError("Redis client could not be initialized")

            # Payload'u JSON string olarak "data" alanına yerleştir
            try:
                json_payload = json.dumps(fields, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize fields to JSON: {e}")
                return None

            string_fields = {"data": json_payload}

            # Redis Stream'e mesajı ekle
            message_id = await asyncio.wait_for(
                self.redis_client.xadd(
                    stream_key,
                    string_fields,
                    maxlen=max_len,
                    approximate=True,
                ),
                timeout=timeout,
            )

            logger.info(
                f"✔ Added message to Redis Stream '{stream_key}' with ID: {message_id}"
            )
            return message_id

        except asyncio.TimeoutError:
            logger.error(
                f"⏱️ Timeout while adding message to Redis Stream '{stream_key}'"
            )
        except Exception as e:
            logger.error(f"❌ Error adding message to Redis Stream: {e}")

        return None
