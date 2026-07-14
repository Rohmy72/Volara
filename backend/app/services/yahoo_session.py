"""Shared HTTP session for Yahoo Finance calls.

Yahoo blocks plain-HTTP-client traffic from datacenter IPs (i.e. Render), so we
impersonate Chrome's TLS fingerprint via curl_cffi. Do not set a User-Agent
header on this session: `impersonate` already supplies one that matches the TLS
fingerprint, and overriding it re-flags the request as a bot.
"""
from __future__ import annotations

from curl_cffi import requests  # type: ignore

session = requests.Session(impersonate="chrome")
