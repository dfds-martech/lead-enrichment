import asyncio
from google.cloud import bigquery

from common.config import config
from common.logging import get_logger
from services.bigquery.schemas import BigQueryRow

logger = get_logger(__name__)

class BigQueryClient:
    """Client for buffering and inserting rows into BigQuery."""

    def __init__(self):
        self.project_id = config.BQPROJECTID
        self.dataset_id = config.BQDATASETID
        self.table_id = config.BQTABLEID
        
        # Initialize Google Client (Sync)
        self.client = bigquery.Client(project=self.project_id)
        self.full_table_id = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

        # Batching state
        self.batch: list[dict] = []
        self.batch_size = 50
        self._lock = asyncio.Lock()

    async def add_row(self, row: BigQueryRow) -> bool:
        """
        Adds a row to the buffer. Flushes immediately if batch is full.
        Returns True if successful (or buffered), False if flush failed.
        """
        try:
            async with self._lock:
                # Convert Pydantic model to dict
                self.batch.append(row.model_dump())
                current_size = len(self.batch)
            
            logger.debug(f"Added row to BQ batch. Current size: {current_size}")

            if current_size >= self.batch_size:
                return await self.flush()
            
            return True

        except Exception as e:
            logger.error(f"Error adding row to BigQuery batch: {e}")
            return False

    async def flush(self) -> bool:
        """Flushes the current batch to BigQuery."""
        async with self._lock:
            if not self.batch:
                return True
            
            rows_to_insert = list(self.batch)
            self.batch = []

        try:
            # Run blocking insert in a thread
            errors = await asyncio.to_thread(
                self.client.insert_rows_json, self.full_table_id, rows_to_insert
            )
            
            if not errors:
                logger.info(f"Successfully flushed {len(rows_to_insert)} rows to BigQuery.")
                return True
            else:
                logger.error(f"BigQuery errors: {errors}")
                return False

        except Exception as e:
            logger.error(f"Error flushing batch to BigQuery: {e}")
            return False