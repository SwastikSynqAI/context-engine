"""
Browser session tests — skipped unless --browser flag is passed.
Run locally with browser: python -m pytest tests/hr/test_browser_session.py --browser -v
"""
import pytest


def pytest_addoption(parser):
    try:
        parser.addoption("--browser", action="store_true", default=False)
    except ValueError:
        pass  # already added by conftest


@pytest.fixture
def browser_enabled(request):
    return request.config.getoption("--browser", default=False)


def test_session_module_importable():
    from src.engines.hr.browser.session import BrowserSession
    assert BrowserSession is not None


def test_session_profile_path():
    from pathlib import Path
    from src.engines.hr.browser.session import BrowserSession
    s = BrowserSession()
    assert "synq-context" in str(s.profile_dir) or ".synq-context" in str(s.profile_dir)


def test_captcha_detection_keywords():
    from src.engines.hr.browser.session import BrowserSession
    s = BrowserSession()
    assert "captcha" in s.CAPTCHA_INDICATORS
    assert "verify you are human" in s.CAPTCHA_INDICATORS


def test_captcha_detected_exception_importable():
    from src.engines.hr.browser.session import CaptchaDetected
    assert issubclass(CaptchaDetected, Exception)


def test_context_manager_protocol():
    from src.engines.hr.browser.session import BrowserSession
    s = BrowserSession()
    assert hasattr(s, "__aenter__")
    assert hasattr(s, "__aexit__")


@pytest.mark.asyncio
async def test_browser_launch_and_close(browser_enabled):
    if not browser_enabled:
        pytest.skip("Pass --browser to run browser tests")
    from src.engines.hr.browser.session import BrowserSession
    s = BrowserSession(headless=True)
    await s.start()
    assert s.context is not None
    await s.stop()
    assert s.context is None


@pytest.mark.asyncio
async def test_new_page_returns_page(browser_enabled):
    if not browser_enabled:
        pytest.skip("Pass --browser to run browser tests")
    from src.engines.hr.browser.session import BrowserSession
    async with BrowserSession(headless=True) as s:
        page = await s.new_page()
        assert page is not None
