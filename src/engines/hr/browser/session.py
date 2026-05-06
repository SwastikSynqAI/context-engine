"""
Persistent async Playwright browser session for AI Hire scrapers.

Design decisions:
- Profile stored at ~/.synq-context/browser-profile/ so LinkedIn and Naukri
  sessions survive across runs — avoids re-login on every scheduled job.
- headless=False by default: Admin can observe the first few runs to verify
  the automation is working correctly before switching to headless.
- Every public action method wraps Playwright calls in _retry() with
  exponential backoff. LinkedIn changes selectors constantly; resilience is
  mandatory.
- Captcha detection aborts the run gracefully and logs for manual intervention
  rather than retrying into a ban.
- Rate limiting: configurable delay between actions to avoid triggering
  LinkedIn / Naukri bot detection.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import (
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
    )
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    BrowserContext = Page = Playwright = Any  # type: ignore[assignment,misc]


class CaptchaDetected(Exception):
    """Raised when a captcha is detected on the current page."""


class BrowserSession:
    """
    Manages a single persistent Playwright browser context.

    Usage:
        session = BrowserSession()
        await session.start()
        page = await session.new_page()
        await session.stop()

    Or as an async context manager:
        async with BrowserSession() as session:
            page = await session.new_page()
    """

    CAPTCHA_INDICATORS: list[str] = [
        "captcha",
        "verify you are human",
        "i am not a robot",
        "recaptcha",
        "hcaptcha",
        "are you a robot",
        "security check",
        "unusual activity",
    ]

    def __init__(
        self,
        *,
        headless: bool = False,
        profile_dir: Path | None = None,
        action_delay_ms: int = 1500,
        max_retries: int = 3,
        retry_base_delay_s: float = 2.0,
    ) -> None:
        self.headless = headless
        self.profile_dir = profile_dir or Path.home() / ".synq-context" / "browser-profile"
        self.action_delay_ms = action_delay_ms
        self.max_retries = max_retries
        self.retry_base_delay_s = retry_base_delay_s

        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    async def start(self) -> None:
        """Launch browser and load persistent context from profile_dir."""
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        logger.info("Browser session started (headless=%s, profile=%s)", self.headless, self.profile_dir)

    async def stop(self) -> None:
        """Close context and stop Playwright."""
        if self.context:
            await self.context.close()
            self.context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser session stopped")

    async def new_page(self) -> "Page":
        """Open a new page in the persistent context."""
        if self.context is None:
            raise RuntimeError("Call start() before new_page()")
        return await self.context.new_page()

    async def check_for_captcha(self, page: "Page") -> None:
        """Raise CaptchaDetected if any captcha indicator is found on the page."""
        content = (await page.content()).lower()
        for indicator in self.CAPTCHA_INDICATORS:
            if indicator in content:
                url = page.url
                logger.warning("Captcha detected at %s (indicator: '%s')", url, indicator)
                raise CaptchaDetected(
                    f"Captcha detected at {url}. Manual intervention required. "
                    f"Open the browser, solve the captcha, then re-run the job."
                )

    async def safe_goto(self, page: "Page", url: str, **kwargs: Any) -> None:
        """Navigate to URL with captcha check and rate-limit delay."""
        await page.goto(url, wait_until="domcontentloaded", **kwargs)
        await asyncio.sleep(self.action_delay_ms / 1000)
        await self.check_for_captcha(page)

    async def _retry(self, coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Retry an async callable up to max_retries times with exponential backoff."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return await coro_fn(*args, **kwargs)
            except CaptchaDetected:
                raise
            except Exception as exc:
                last_exc = exc
                delay = self.retry_base_delay_s * (2 ** attempt)
                logger.warning(
                    "Attempt %d/%d failed (%s). Retrying in %.1fs",
                    attempt + 1, self.max_retries, exc, delay,
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def click(self, page: "Page", selector: str, fallback_selectors: list[str] | None = None) -> None:
        """Click an element by selector, trying fallbacks if primary fails."""
        selectors = [selector] + (fallback_selectors or [])
        last_exc: Exception | None = None
        for sel in selectors:
            try:
                await self._retry(page.click, sel, timeout=10000)
                await asyncio.sleep(self.action_delay_ms / 1000)
                return
            except Exception as exc:
                last_exc = exc
                logger.debug("Selector '%s' failed: %s", sel, exc)
        raise last_exc  # type: ignore[misc]

    async def fill(self, page: "Page", selector: str, value: str) -> None:
        """Fill an input field with retry logic."""
        await self._retry(page.fill, selector, value, timeout=10000)
        await asyncio.sleep(self.action_delay_ms / 1000)

    async def wait_and_get_text(self, page: "Page", selector: str) -> str:
        """Wait for element and return its inner text."""
        await page.wait_for_selector(selector, timeout=15000)
        return (await page.inner_text(selector)).strip()

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()
