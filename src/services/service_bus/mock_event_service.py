import json

from azure.servicebus import ServiceBusClient, ServiceBusMessage

from common.config import config
from common.logging import get_logger
from services.crm_service import CRMService

logger = get_logger(__name__)

crm = CRMService()

CONN_STR = config.service_bus_connection_string
TOPIC_NAME = config.service_bus_topic_name


def send_mock_lead_created(event_index: int):
    client = ServiceBusClient.from_connection_string(CONN_STR)
    event = crm.mock_lead_event(event_index)

    with client:
        sender = client.get_topic_sender(topic_name=TOPIC_NAME)
        with sender:
            msg = ServiceBusMessage(json.dumps(event))
            sender.send_messages(msg)
            logger.info("Mock LeadUpdated event sent!")
