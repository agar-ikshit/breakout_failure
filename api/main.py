from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import logging
from breakout.analyzer import analyze_vrz_vwap
from breakout.db import insert_failures
from breakout.settings import DEFAULT_INTERVAL, DEFAULT_PERIOD

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Breakout Failures API")

class FailureResponse(BaseModel):
    company: str
    ticker: str
    location: str
    failure_time: str
    break_time: Optional[str]
    close_at_failure: Optional[float]

class AnalyzeRequest(BaseModel):
    ticker: str
    company: Optional[str] = None
    save_to_db: Optional[bool] = False
    interval: Optional[str] = DEFAULT_INTERVAL
    period: Optional[str] = DEFAULT_PERIOD

@app.post("/analyze", response_model=List[FailureResponse])
async def analyze_single(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze a single ticker. Optionally store results to Supabase if save_to_db==True.
    """
    ticker = req.ticker
    company = req.company or req.ticker
    failures = analyze_vrz_vwap(ticker, company, interval=req.interval, period=req.period)
    if failures is None:
        # Return empty list instead of None to keep API consistent
        return []
    # Convert datetimes to ISO strings
    for f in failures:
        if hasattr(f['failure_time'], 'isoformat'):
            f['failure_time'] = f['failure_time'].isoformat()
        if 'break_time' in f and hasattr(f['break_time'], 'isoformat'):
            f['break_time'] = f['break_time'].isoformat()

    if req.save_to_db and failures:
        # Use background task so request doesn't block on DB I/O
        background_tasks.add_task(insert_failures, [{
            "company": f["company"],
            "ticker": f["ticker"],
            "location": f["location"],
            "failure_time": f["failure_time"]
        } for f in failures])
    return failures

@app.post("/analyze/batch", response_model=List[FailureResponse])
async def analyze_batch(requests: List[AnalyzeRequest], background_tasks: BackgroundTasks):
    """
    Analyze a batch of tickers in serial (you can later parallelize).
    """
    all_failures = []
    for req in requests:
        comp = req.company or req.ticker
        failures = analyze_vrz_vwap(req.ticker, comp, interval=req.interval, period=req.period)
        if failures:
            for f in failures:
                if hasattr(f['failure_time'], 'isoformat'):
                    f['failure_time'] = f['failure_time'].isoformat()
                if 'break_time' in f and hasattr(f['break_time'], 'isoformat'):
                    f['break_time'] = f['break_time'].isoformat()
            all_failures.extend(failures)

    if any(r.save_to_db for r in requests) and all_failures:
        # convert and store all at once
        payload = [{
            "company": f["company"],
            "ticker": f["ticker"],
            "location": f["location"],
            "failure_time": f["failure_time"]
        } for f in all_failures]
        background_tasks.add_task(insert_failures, payload)

    return all_failures
