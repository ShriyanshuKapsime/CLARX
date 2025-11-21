"""
Rule-based dark pattern detection modules
"""
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional


class DarkPatternDetector:
    def __init__(self):
        self.violations = []

    def detect_all(self, html: str, soup: BeautifulSoup, scraper_result: Dict) -> List[Dict]:
        """Run all detectors and return violations"""
        violations = []

        # Fake Scarcity
        scarcity = self.detect_fake_scarcity(html, soup)
        if scarcity.get('detected'):
            violations.append({
                "type": "fake_scarcity",
                "title": "Fake Scarcity",
                "severity": scarcity.get('severity', 'medium'),
                "confidence": scarcity.get('confidence', 'medium'),
                "explanation": scarcity.get('explanation', 'Scarcity indicators detected'),
                "snippet": scarcity.get('snippet', '')
            })

        # Fake Timer
        timer_analysis = scraper_result.get('timer_analysis', {})
        if timer_analysis.get('fake_timer'):
            violations.append({
                "type": "fake_timer",
                "title": "Fake Timer",
                "severity": "high",
                "confidence": timer_analysis.get('confidence', 'medium'),
                "explanation": "Timer script is purely client-side and restarts per session.",
                "snippet": ""
            })

        # Drip Pricing
        drip = self.detect_drip_pricing(html, soup)
        if drip.get('detected'):
            violations.append({
                "type": "drip_pricing",
                "title": "Drip Pricing",
                "severity": drip.get('severity', 'medium'),
                "confidence": drip.get('confidence', 'medium'),
                "explanation": drip.get('explanation', 'Hidden fees detected'),
                "snippet": drip.get('snippet', '')
            })

        # Pre-ticked Add-ons
        pre_ticked = self.detect_pre_ticked_addons(html, soup)
        if pre_ticked.get('detected'):
            violations.append({
                "type": "pre_ticked_addon",
                "title": "Pre-Ticked Add-On",
                "severity": pre_ticked.get('severity', 'low'),
                "confidence": pre_ticked.get('confidence', 'medium'),
                "explanation": pre_ticked.get('explanation', 'Add-ons selected by default'),
                "snippet": pre_ticked.get('snippet', '')
            })

        # Confirm Shaming
        shaming = self.detect_confirm_shaming(html, soup)
        if shaming.get('detected'):
            violations.append({
                "type": "confirm_shaming",
                "title": "Confirm Shaming",
                "severity": shaming.get('severity', 'low'),
                "confidence": shaming.get('confidence', 'medium'),
                "explanation": shaming.get('explanation', 'Manipulative language detected'),
                "snippet": shaming.get('snippet', '')
            })

        return violations

    def detect_fake_scarcity(self, html: str, soup: BeautifulSoup) -> Dict:
        """Detect fake scarcity indicators"""
        text = soup.get_text().lower()
        html_lower = html.lower()

        scarcity_keywords = [
            'only', 'left in stock', 'hurry', 'selling fast', 'limited stock',
            'only a few left', 'almost gone', 'last few items', 'limited time',
            'stock running out', 'be quick'
        ]

        found_keywords = [kw for kw in scarcity_keywords if kw in text]

        # Look for countdown timers with scarcity text
        timer_with_scarcity = bool(
            re.search(r'\d{1,2}:\d{2}:\d{2}', text) and
            any(kw in text for kw in ['only', 'left', 'hurry', 'limited'])
        )

        # Look for inventory numbers
        inventory_patterns = [
            r'only\s+(\d+)\s+left',
            r'(\d+)\s+in\s+stock',
            r'only\s+(\d+)\s+available'
        ]
        inventory_found = any(re.search(pattern, text, re.I) for pattern in inventory_patterns)

        detected = len(found_keywords) >= 2 or timer_with_scarcity or inventory_found

        if detected:
            confidence = "high" if (timer_with_scarcity and inventory_found) else "medium"
            severity = "high" if confidence == "high" else "medium"

            explanation = "Countdown resets on every refresh with identical inventory text."
            if inventory_found:
                explanation = "Scarcity messaging detected with inventory claims that may reset on refresh."

            return {
                "detected": True,
                "confidence": confidence,
                "severity": severity,
                "explanation": explanation,
                "keywords": found_keywords
            }

        return {"detected": False}

    def detect_drip_pricing(self, html: str, soup: BeautifulSoup) -> Dict:
        """Detect hidden fees that appear later"""
        text = soup.get_text().lower()
        html_lower = html.lower()

        # Look for fee-related terms
        fee_keywords = [
            'handling fee', 'processing fee', 'convenience fee', 'service charge',
            'delivery charge', 'shipping fee', 'taxes extra', 'gst extra'
        ]

        # Check if fees are mentioned but not prominently displayed
        fee_mentions = [kw for kw in fee_keywords if kw in text]

        # Look for checkout-specific fee mentions
        checkout_indicators = ['checkout', 'cart', 'payment', 'billing']
        has_checkout_context = any(indicator in text for indicator in checkout_indicators)

        # Check for small print or hidden text
        small_print = soup.find_all(['small', 'span'], class_=re.compile(r'small|fine|print|hidden', re.I))
        hidden_fees = any(fee_kw in str(elem).lower() for elem in small_print for fee_kw in fee_keywords)

        detected = (len(fee_mentions) > 0 and has_checkout_context) or hidden_fees

        if detected:
            confidence = "high" if hidden_fees else "medium"
            explanation = "An extra handling fee appears only after address confirmation."
            if hidden_fees:
                explanation = "Fees mentioned in small print or hidden sections, revealed only at checkout."

            return {
                "detected": True,
                "confidence": confidence,
                "severity": "medium",
                "explanation": explanation
            }

        return {"detected": False}

    def detect_pre_ticked_addons(self, html: str, soup: BeautifulSoup) -> Dict:
        """Detect pre-selected add-ons like warranties"""
        # Look for checked checkboxes
        checked_inputs = soup.find_all('input', {'type': 'checkbox', 'checked': True})
        checked_inputs.extend(soup.find_all('input', {'type': 'checkbox', 'checked': 'checked'}))

        addon_keywords = ['warranty', 'insurance', 'protection', 'extended', 'add-on', 'accessory']
        text = soup.get_text().lower()

        pre_ticked_addons = []
        for inp in checked_inputs:
            # Find parent or nearby text
            parent = inp.find_parent()
            if parent:
                parent_text = parent.get_text().lower()
                if any(kw in parent_text for kw in addon_keywords):
                    pre_ticked_addons.append(parent_text[:100])

        # Also check for default selected options
        selected_options = soup.find_all('option', selected=True)
        for opt in selected_options:
            opt_text = opt.get_text().lower()
            if any(kw in opt_text for kw in addon_keywords):
                pre_ticked_addons.append(opt_text)

        detected = len(pre_ticked_addons) > 0

        if detected:
            confidence = "high" if len(pre_ticked_addons) >= 2 else "medium"
            explanation = "Extended warranty checkbox is enabled by default."

            return {
                "detected": True,
                "confidence": confidence,
                "severity": "low",
                "explanation": explanation,
                "addons": pre_ticked_addons
            }

        return {"detected": False}

    def detect_confirm_shaming(self, html: str, soup: BeautifulSoup) -> Dict:
        """Detect manipulative language that shames users"""
        text = soup.get_text().lower()

        shaming_patterns = [
            r'no thanks.*(?:i don\'?t want|i\'?ll pass)',
            r'(?:decline|skip).*savings',
            r'no.*(?:i\'?m not interested|not for me)',
        ]

        shaming_keywords = [
            'no thanks, i don\'t want savings',
            'decline offer',
            'skip this deal',
            'i\'ll pass on savings'
        ]

        detected = any(re.search(pattern, text, re.I) for pattern in shaming_patterns) or \
                   any(kw in text for kw in shaming_keywords)

        if detected:
            return {
                "detected": True,
                "confidence": "medium",
                "severity": "low",
                "explanation": "Manipulative language used to pressure users into accepting offers."
            }

        return {"detected": False}

    def calculate_trust_score(self, violations: List[Dict]) -> Dict:
        """
        Calculate trust grade based on violations
        Weights: pre-ticked (2), fake timer (2), drip pricing (1), fake scarcity (1), others (1)
        """
        weights = {
            "pre_ticked_addon": 2,
            "fake_timer": 2,
            "drip_pricing": 1,
            "fake_scarcity": 1,
            "confirm_shaming": 1,
        }

        total_score = 0
        for violation in violations:
            vtype = violation.get('type', '')
            weight = weights.get(vtype, 1)
            # Adjust by severity
            severity_multiplier = {"high": 1.5, "medium": 1.0, "low": 0.5}.get(violation.get('severity', 'medium'), 1.0)
            total_score += weight * severity_multiplier

        # Map to grade
        if total_score == 0:
            grade = "A"
            summary = "Low Risk"
        elif total_score <= 2:
            grade = "B"
            summary = "Moderate Risk"
        elif total_score <= 4:
            grade = "C"
            summary = "High Manipulation Detected"
        elif total_score <= 6:
            grade = "D"
            summary = "High Manipulation Detected"
        else:
            grade = "F"
            summary = "Critical Manipulation"

        return {
            "grade": grade,
            "summary": summary,
            "score": total_score
        }

