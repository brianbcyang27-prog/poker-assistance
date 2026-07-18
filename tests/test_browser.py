"""Tests for v4.3.0 Browser System.

Tests BrowserSecurity, BrowserState, PageExtractor, SessionManager,
BrowserManager, and the enhanced ♦Q WebResearchWorker.
"""

import asyncio
import functools
import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from jarvis.browser.browser_state import BrowserState, BrowserStatus, TabInfo
from jarvis.browser.security import BrowserSecurity, BrowserDecision
from jarvis.browser.extractor import PageExtractor, PageData, extractor
from jarvis.browser.sessions import SessionManager, BrowserSession, session_manager
from jarvis.browser.manager import BrowserManager, browser_manager
from jarvis.browser.playwright_provider import BrowserResult


class TestBrowserState(unittest.TestCase):
    """BrowserState and status tracking."""

    def test_initial_state(self):
        state = BrowserState()
        self.assertEqual(state.status, BrowserStatus.IDLE)
        self.assertEqual(state.current_url, "")
        self.assertEqual(state.current_title, "")
        self.assertEqual(state.tab_count, 0)

    def test_update_navigation(self):
        state = BrowserState()
        state.update_navigation(
            url="https://example.com",
            title="Example",
            duration_ms=150.5,
        )
        self.assertEqual(state.current_url, "https://example.com")
        self.assertEqual(state.current_title, "Example")
        self.assertEqual(state.status, BrowserStatus.BROWSING)
        self.assertTrue(state.last_action_time > 0)
        self.assertEqual(len(state.navigation_history), 1)

    def test_navigation_history_limit(self):
        state = BrowserState()
        for i in range(105):
            state.update_navigation(f"https://example.com/{i}", f"Page {i}", 10)
        self.assertEqual(len(state.navigation_history), 50)

    def test_status_transitions(self):
        state = BrowserState()
        state.update_status(BrowserStatus.IDLE)
        self.assertEqual(state.status, BrowserStatus.IDLE)

        state.update_status(BrowserStatus.NAVIGATING, "navigate:https://example.com")
        self.assertEqual(state.status, BrowserStatus.NAVIGATING)
        self.assertIn("navigate:", state.current_action)

    def test_error_handling(self):
        state = BrowserState()
        state.set_error("Something went wrong")
        self.assertEqual(state.status, BrowserStatus.ERROR)
        self.assertEqual(state.last_error, "Something went wrong")

    def test_to_dict(self):
        state = BrowserState()
        state.update_navigation("https://example.com", "Example", 100)
        d = state.to_dict()
        self.assertIn("status", d)
        self.assertIn("current_url", d)
        self.assertIn("current_title", d)
        self.assertIn("tab_count", d)
        self.assertIn("tabs", d)
        self.assertIn("history_length", d)

    def test_tab_management(self):
        state = BrowserState()
        state.add_tab(TabInfo(id="1", url="https://a.com", title="A"))
        state.add_tab(TabInfo(id="2", url="https://b.com", title="B"))
        state.set_active_tab("2")
        self.assertEqual(state.active_tab_id, "2")
        self.assertEqual(state.tab_count, 2)

        state.remove_tab("1")
        self.assertEqual(state.tab_count, 1)


class TestBrowserSecurity(unittest.TestCase):
    """BrowserSecurity permission checks."""

    def test_safe_actions(self):
        sec = BrowserSecurity()
        for action in ["extract", "screenshot", "get_content", "get_text", "get_links"]:
            result = sec.check_action(action, url="https://example.com", agent="test")
            self.assertTrue(result.allowed, f"Action {action} should be safe")

    def test_navigate_safe_domain(self):
        sec = BrowserSecurity()
        result = sec.check_action("navigate", url="https://github.com", agent="test")
        self.assertTrue(result.allowed)

    def test_navigate_unknown_domain(self):
        sec = BrowserSecurity()
        result = sec.check_action("navigate", url="https://example.com", agent="test")
        self.assertTrue(result.allowed)

    def test_navigate_sensitive_domain(self):
        sec = BrowserSecurity()
        result = sec.check_action("navigate", url="https://bank.example.com", agent="test")
        # "bank" is in SENSITIVE_DOMAINS, risk becomes "high"
        # In normal mode, "high" requires confirmation but is NOT allowed
        self.assertFalse(result.allowed)

    def test_navigate_blocked_domain(self):
        sec = BrowserSecurity()
        result = sec.check_action("navigate", url="https://malware.com", agent="test")
        self.assertFalse(result.allowed)

    def test_type_action_risk(self):
        sec = BrowserSecurity()
        result = sec.check_action("type", url="https://example.com", agent="test")
        self.assertTrue(result.allowed)

    def test_evaluate_action_risk(self):
        sec = BrowserSecurity()
        result = sec.check_action("evaluate", url="https://example.com", agent="test")
        # "evaluate" is not in BROWSER_ACTION_RISKS, defaults to "medium"
        # In normal mode, medium is allowed with notification
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, "medium")

    def test_strict_mode(self):
        sec = BrowserSecurity(mode="strict")
        result = sec.check_action("type", url="https://example.com", agent="test")
        self.assertFalse(result.allowed)

        # extract is "safe" action, and github.com is a safe domain → overall "safe" risk
        result = sec.check_action("extract", url="https://github.com", agent="test")
        self.assertTrue(result.allowed)

    def test_permissive_mode(self):
        sec = BrowserSecurity(mode="permissive")
        result = sec.check_action("navigate", url="https://example.com", agent="test")
        self.assertTrue(result.allowed)

    def test_unknown_action_not_in_risk_table(self):
        sec = BrowserSecurity()
        result = sec.check_action("nonexistent_action", url="https://example.com", agent="test")
        # Unknown actions default to "medium" risk, which is allowed in normal mode
        self.assertTrue(result.allowed)
        self.assertEqual(result.risk_level, "medium")

    def test_approve_and_revoke(self):
        sec = BrowserSecurity()
        sec.approve("navigate", url="https://example.com", agent="test")
        stats = sec.get_stats()
        self.assertEqual(stats["cached_approvals"], 1)

        sec.revoke("navigate", url="https://example.com", agent="test")
        stats = sec.get_stats()
        self.assertEqual(stats["cached_approvals"], 0)

    def test_stats(self):
        sec = BrowserSecurity()
        stats = sec.get_stats()
        self.assertIn("mode", stats)
        self.assertIn("cached_approvals", stats)
        self.assertIn("action_risks", stats)
        self.assertIn("safe_domains", stats)
        self.assertIn("sensitive_domains", stats)


class TestPageExtractor(unittest.TestCase):
    """PageExtractor structured data extraction."""

    def setUp(self):
        self.extractor = PageExtractor()

    def test_extract_simple_html(self):
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test paragraph.</p>
            <a href="https://example.com">Example Link</a>
        </body>
        </html>
        """
        data = asyncio.run(
            self.extractor.extract_from_html(html, url="https://test.com")
        )
        self.assertEqual(data.title, "Test Page")
        self.assertIn("Hello World", data.content)
        self.assertGreaterEqual(len(data.links), 1)

    def test_extract_forms(self):
        html = """
        <html><body>
        <form action="/submit" method="post">
            <input name="username" type="text" />
            <input name="password" type="password" />
            <button type="submit">Login</button>
        </form>
        </body></html>
        """
        data = asyncio.run(
            self.extractor.extract_from_html(html)
        )
        self.assertGreaterEqual(len(data.forms), 1)
        self.assertGreaterEqual(len(data.forms[0].fields), 2)

    def test_extract_tables(self):
        html = """
        <html><body>
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>A</td><td>1</td></tr>
            <tr><td>B</td><td>2</td></tr>
        </table>
        </body></html>
        """
        data = asyncio.run(
            self.extractor.extract_from_html(html)
        )
        self.assertGreaterEqual(len(data.tables), 1)

    def test_to_dict(self):
        html = "<html><head><title>T</title></head><body><p>Content</p></body></html>"
        data = asyncio.run(
            self.extractor.extract_from_html(html)
        )
        d = data.to_dict()
        self.assertIn("title", d)
        self.assertIn("content", d)
        self.assertIn("links", d)
        self.assertIn("forms", d)

    def test_to_llm_context(self):
        html = "<html><head><title>API Docs</title></head><body><p>Use this API carefully.</p></body></html>"
        data = asyncio.run(
            self.extractor.extract_from_html(html)
        )
        ctx = data.to_llm_context()
        self.assertIn("API Docs", ctx)
        self.assertIn("Use this API carefully", ctx)


class TestSessionManager(unittest.TestCase):
    """SessionManager persistent browser profiles."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = SessionManager(storage_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_session(self):
        session = asyncio.run(
            self.manager.create("test_session")
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.name, "test_session")
        self.assertTrue(os.path.exists(session.profile_dir))

    def test_list_sessions(self):
        asyncio.run(self.manager.create("s1"))
        asyncio.run(self.manager.create("s2"))
        sessions = asyncio.run(self.manager.list_sessions())
        self.assertEqual(len(sessions), 2)

    def test_delete_session(self):
        asyncio.run(self.manager.create("to_delete"))
        result = asyncio.run(self.manager.delete("to_delete"))
        self.assertTrue(result)
        sessions = asyncio.run(self.manager.list_sessions())
        self.assertEqual(len(sessions), 0)

    def test_save_cookies(self):
        asyncio.run(self.manager.create("cookie_test"))
        cookies = [{"name": "sid", "value": "abc123", "domain": ".example.com"}]
        asyncio.run(
            self.manager.save_cookies("cookie_test", cookies)
        )
        session = asyncio.run(
            self.manager.restore("cookie_test")
        )
        self.assertEqual(len(session.cookies), 1)
        self.assertEqual(session.cookies[0]["name"], "sid")

    def test_stats(self):
        asyncio.run(self.manager.create("stats_test"))
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_sessions"], 1)


class TestBrowserManager(unittest.TestCase):
    """BrowserManager central gateway."""

    def setUp(self):
        self.manager = BrowserManager()

    def test_initial_state(self):
        state = self.manager.get_state()
        self.assertIn("status", state)

    def test_actions_list(self):
        actions = self.manager.get_actions()
        self.assertIn("navigate", actions)
        self.assertIn("search", actions)
        self.assertIn("extract", actions)
        self.assertIn("click", actions)
        self.assertIn("screenshot", actions)

    def test_stats(self):
        stats = self.manager.get_stats()
        self.assertFalse(stats["initialized"])
        self.assertIn("security", stats)
        self.assertIn("sessions", stats)

    def test_deny_unknown_action(self):
        """Unknown action returns error before trying to init browser."""
        result = asyncio.run(
            self.manager.execute("nonexistent", agent="test")
        )
        self.assertFalse(result.get("ok"))
        self.assertIn("Unknown action", result.get("error", ""))

    def test_action_log(self):
        self.manager._log_action("test", "success", "agent1", "safe")
        self.assertEqual(len(self.manager.get_recent_actions()), 1)

    def test_browser_manager_singleton(self):
        from jarvis.browser.manager import browser_manager as bm1
        from jarvis.browser.manager import browser_manager as bm2
        self.assertIs(bm1, bm2)

    def test_deny_high_risk_action(self):
        """High-risk action (navigate to blocked domain) is denied."""
        result = asyncio.run(
            self.manager.execute("navigate", url="https://malware.com", agent="test")
        )
        self.assertFalse(result.get("ok"))

    def test_approve_cached_action(self):
        """Approved action goes through the cache."""
        self.manager.security.approve("navigate", url="https://example.com", agent="test")
        # With cache hit, check_action returns allowed=True
        decision = self.manager.security.check_action("navigate", url="https://example.com", agent="test")
        self.assertTrue(decision.allowed)


class TestEnhancedWebResearchWorker(unittest.TestCase):
    """Enhanced ♦Q WebResearchWorker with BrowserManager."""

    def test_system_prompt_includes_browser(self):
        from jarvis.agents.workers.research import WebResearchWorker
        worker = WebResearchWorker()
        prompt = worker.get_system_prompt()
        self.assertIn("BROWSER", prompt)
        self.assertIn("search", prompt)
        self.assertIn("extract", prompt)
        self.assertIn("navigate", prompt)

    def test_worker_identity(self):
        from jarvis.agents.workers.research import WebResearchWorker, DocumentationWorker, FactCheckWorker
        qw = WebResearchWorker()
        self.assertEqual(qw.card_id, "♦Q")
        self.assertEqual(qw.name, "Web Research")

        jw = DocumentationWorker()
        self.assertEqual(jw.card_id, "♦J")

        tw = FactCheckWorker()
        self.assertEqual(tw.card_id, "♦10")


if __name__ == "__main__":
    unittest.main()
