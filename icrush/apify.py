"""Apify API client with retry logic, polling, and cost tracking."""

import asyncio
import time
from dataclasses import dataclass, field

import httpx

from icrush.config import TOKEN


@dataclass
class RunResult:
    run_id: str
    dataset_id: str


class ApifyClient:
    """Async HTTP client for the Apify REST API."""

    def __init__(self) -> None:
        self._runs: list[dict] = []  # { id, actor } for cost report
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    async def _fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        retries: int = 3,
    ) -> httpx.Response:
        """HTTP call with retry on network errors (3s/6s/9s backoff)."""
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await self._client.request(method, url, json=body)
                return resp
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as e:
                last_err = e
                if attempt < retries - 1:
                    delay = 3 * (attempt + 1)
                    print(f"  ⚡ fetch 重试 {attempt + 1}/{retries}: {e}")
                    await asyncio.sleep(delay)
        raise last_err  # type: ignore[misc]

    async def start_actor(self, actor: str, input_data: dict) -> RunResult:
        """POST /v2/acts/{actor}/runs → return runId + datasetId."""
        actor_slug = actor.replace("/", "~")
        url = f"https://api.apify.com/v2/acts/{actor_slug}/runs?token={TOKEN}"
        resp = await self._fetch(url, method="POST", body=input_data)
        if not resp.is_success:
            raise RuntimeError(f"startActor({actor}): HTTP {resp.status_code}: {resp.text}")
        data = resp.json()["data"]
        self._runs.append({"id": data["id"], "actor": actor})
        return RunResult(run_id=data["id"], dataset_id=data["defaultDatasetId"])

    async def wait_for_run(self, run_id: str, max_wait_sec: int = 1800) -> dict:
        """Poll GET /v2/actor-runs/{runId} every 5s until terminal status."""
        t0 = time.monotonic()
        while time.monotonic() - t0 < max_wait_sec:
            resp = await self._fetch(
                f"https://api.apify.com/v2/actor-runs/{run_id}?token={TOKEN}"
            )
            data = resp.json()["data"]
            status: str = data["status"]
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                if status != "SUCCEEDED":
                    raise RuntimeError(f"Run {run_id} ended with status {status}")
                return data
            await asyncio.sleep(5)
        raise TimeoutError(f"Run {run_id} timed out after {max_wait_sec}s")

    async def fetch_dataset(self, dataset_id: str) -> list[dict]:
        """GET /v2/datasets/{datasetId}/items."""
        url = (
            f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            f"?token={TOKEN}&clean=true&limit=10000"
        )
        resp = await self._fetch(url)
        if not resp.is_success:
            raise RuntimeError(f"fetchDataset({dataset_id}): HTTP {resp.status_code}")
        return resp.json()

    async def report_cost(self) -> float:
        """Sum usageTotalUsd across all tracked runs."""
        total: float = 0.0
        lines: list[str] = []
        for run in self._runs:
            try:
                resp = await self._fetch(
                    f"https://api.apify.com/v2/actor-runs/{run['id']}?token={TOKEN}"
                )
                usd = resp.json()["data"].get("usageTotalUsd", 0)
                total += usd
                lines.append(f"  {run['actor']}: ${usd:.4f}")
            except Exception:
                lines.append(f"  {run['actor']}: ?")
        print("\n💰 Apify 成本：")
        for line in lines:
            print(line)
        print("  ─────────")
        print(f"  TOTAL: ${total:.4f}  (~¥{total * 7.25:.2f})")
        return total

    async def close(self) -> None:
        await self._client.aclose()
