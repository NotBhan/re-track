"""Tests for Bounded Concurrency Guard and MCP Concurrency Hardening."""

import asyncio
import pytest

from app.application.use_cases.context import BoundedConcurrencyGuard


@pytest.mark.asyncio
async def test_single_slot_acquisition_and_release():
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=1.0)

    acquired, err = await guard.acquire()
    assert acquired
    assert err is None

    guard.release()


@pytest.mark.asyncio
async def test_queue_saturation_returns_busy_error():
    # max_concurrent=1, max_queue=3 -> 1 running + 3 waiting = 4 total active.
    # 5th request should be immediately rejected with BusyError.
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=3, timeout=5.0)

    # 1. Acquire running slot
    acquired1, _ = await guard.acquire()
    assert acquired1

    # 2. Queue 3 waiting requests
    wait_tasks = []
    for _ in range(3):
        task = asyncio.create_task(guard.acquire())
        wait_tasks.append(task)

    # Allow event loop to process queueing
    await asyncio.sleep(0.05)
    assert guard.waiting_count == 3

    # 3. 4th queued request (5th overall) exceeds max_queue=3 -> BusyError
    acquired_overflow, err_overflow = await guard.acquire()
    assert not acquired_overflow
    assert err_overflow == "BusyError"

    # Cleanup: release slot and let queued tasks acquire and release
    guard.release()
    for task in wait_tasks:
        acq, err = await task
        if acq:
            guard.release()


@pytest.mark.asyncio
async def test_queue_timeout_returns_timeout_error():
    # max_concurrent=1, max_queue=5, timeout=0.1s
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=0.1)

    acquired1, _ = await guard.acquire()
    assert acquired1

    # Second request waits and times out after 0.1s
    acquired2, err2 = await guard.acquire()
    assert not acquired2
    assert err2 == "TimeoutError"

    guard.release()


@pytest.mark.asyncio
async def test_cancellation_frees_queue_counter():
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=2, timeout=5.0)

    acquired1, _ = await guard.acquire()
    assert acquired1

    # Start waiting task
    task = asyncio.create_task(guard.acquire())
    await asyncio.sleep(0.05)
    assert guard.waiting_count == 1

    # Cancel waiting task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Waiting count must be back to 0
    assert guard.waiting_count == 0

    guard.release()
