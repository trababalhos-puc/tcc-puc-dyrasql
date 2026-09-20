#!/usr/bin/env python3

"""
Metadata Connector - extracao opcional de metadados Iceberg via catalogo REST
O fluxo principal de decisao usa EXPLAIN (TYPE IO) do Trino.
"""

import logging
import os

logger = logging.getLogger(__name__)


class MetadataConnector:
    """Conecta com o catalogo Iceberg REST quando disponivel"""

    def __init__(self):
        self.rest_uri = os.getenv("ICEBERG_REST_URI", "http://iceberg-rest:8181")
        self.catalog = None

    def get_metadata(self, table_name):
        if not self.catalog:
            logger.debug(
                "Catalogo Iceberg REST nao inicializado; metadados virao do EXPLAIN. Tabela: %s",
                table_name,
            )
            return None
        return None
