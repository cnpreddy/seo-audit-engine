#!/usr/bin/env python3
"""
Local SEO Audit Engine — web service.

Endpoints:
  GET  /                a simple form to try it manually
  GET  /audit            HTML report for ?url=&name=&city=
  GET  /audit.json       JSON version of the same result
  GET  /health           health check for the hosting platform
"""
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from audit_engine import run_audit
from report_generator import render_report

app = FastAPI(title="Local SEO Audit Engine")

FORM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local SEO Audit Engine</title>
<style>
  body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:#f9f9f7;
       color:#0b0b0b; max-width:520px; margin:60px auto; padding:0 20px;}
  h1{font-size:22px;}
  p{color:#52514e; font-size:14px;}
  form{display:flex; flex-direction:column; gap:12px; margin-top:24px;}
  input{padding:10px 12px; border:1px solid rgba(11,11,11,0.15); border-radius:8px; font-size:14px;}
  button{padding:11px 16px; border:none; border-radius:8px; background:#0b0b0b; color:#fff;
         font-weight:600; font-size:14px; cursor:pointer;}
</style>
</head>
<body>
  <h1>Local SEO Audit Engine</h1>
  <p>Enter a business website to generate a free instant SEO snapshot.</p>
  <form action="/audit" method="get">
    <input name="url" placeholder="https://example.com" required>
    <input name="name" placeholder="Business name (optional)">
    <input name="city" placeholder="City, State (optional)">
    <button type="submit">Run Audit</button>
  </form>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return FORM_PAGE


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/audit", response_class=HTMLResponse)
def audit(
    url: str = Query(..., description="Business website URL"),
    name: str = Query(None, description="Business name"),
    city: str = Query(None, description="City, State"),
):
    result = run_audit(url, business_name=name, city=city)
    return render_report(result)


@app.get("/audit.json", response_class=JSONResponse)
def audit_json(
    url: str = Query(...),
    name: str = Query(None),
    city: str = Query(None),
):
    return run_audit(url, business_name=name, city=city)
