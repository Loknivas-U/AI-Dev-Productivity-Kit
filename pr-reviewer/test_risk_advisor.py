from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_advisor import build_advisory_comment, parse_high_priority_findings


class RiskAdvisorTest(unittest.TestCase):
    def test_empty_high_priority_placeholder_counts_as_zero(self) -> None:
        review_text = """## 🔍 AI PR Review — Example

### Issues Found

#### 🔴 High Priority
- No high priority issues found.

#### 🟡 Medium Priority
- **`app.py:12`** — Missing timeout. Add one.
"""
        findings = parse_high_priority_findings(review_text)
        advisory = build_advisory_comment("Example", 7, findings)

        self.assertEqual(findings, [])
        self.assertIn("flagged **0 High priority issue(s)**", advisory)


if __name__ == "__main__":
    unittest.main()
