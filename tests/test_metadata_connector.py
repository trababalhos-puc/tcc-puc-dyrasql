"""Testes do MetadataConnector."""

from metadata_connector import MetadataConnector


def test_get_metadata_without_catalog():
    connector = MetadataConnector()
    assert connector.get_metadata("iceberg.db.t") is None


def test_get_metadata_with_catalog_still_none():
    connector = MetadataConnector()
    connector.catalog = object()
    assert connector.get_metadata("iceberg.db.t") is None
