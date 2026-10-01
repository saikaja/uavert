"""Paged queries against ArcGIS Online feature services (used by Toronto Police)."""

from collections.abc import AsyncIterator

import httpx

from uavert.sources.http import SourceUnavailable, get_json

PAGE_SIZE = 2000  # the services' maxRecordCount


async def query_pages(
    client: httpx.AsyncClient, layer_url: str, where: str, out_fields: str = "*", fmt: str = "json"
) -> AsyncIterator[list[dict]]:
    """Yield pages of features until the service reports no more."""
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": fmt,
        }
        if fmt == "json":
            params["returnGeometry"] = "false"
        else:
            params.update(outSR="4326", geometryPrecision="6")
        data = await get_json(client, f"{layer_url}/query", params)
        if "error" in data:
            raise SourceUnavailable(f"{layer_url}: {data['error'].get('message', data['error'])}")
        features = data.get("features", [])
        if features:
            yield features
        more = data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit")
        if not more or not features:
            return
        offset += len(features)
