"""Initializes and registers all connectors."""

from connectors.base import ConnectorRegistry
from connectors.discourse.connector import DiscourseConnector
from connectors.lemmy.connector import LemmyConnector
from connectors.devto.connector import DevtoConnector
from connectors.ghost.connector import GhostConnector
from connectors.webhook_hmac.connector import WebhookHmacConnector
from connectors.assisted.connector import AssistedConnector
from connectors.hashnode.connector import HashnodeConnector
from connectors.slack.connector import SlackConnector
from connectors.mrss.connector import MrssConnector


def register_all_connectors():
    ConnectorRegistry.register(DiscourseConnector())
    ConnectorRegistry.register(LemmyConnector())
    ConnectorRegistry.register(DevtoConnector())
    ConnectorRegistry.register(GhostConnector())
    ConnectorRegistry.register(WebhookHmacConnector())
    ConnectorRegistry.register(AssistedConnector())
    ConnectorRegistry.register(HashnodeConnector())
    ConnectorRegistry.register(SlackConnector())
    ConnectorRegistry.register(MrssConnector())


register_all_connectors()
