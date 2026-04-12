"""AI Email Writer — generate personalized emails using free LLM APIs."""

import json
import os

import requests


class AIWriter:
    """Generate personalized emails using Groq or Google Gemini (both free)."""

    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def __init__(self, settings):
        self.groq_key = settings.get("groq_api_key", "") or os.environ.get("GROQ_API_KEY", "")
        self.gemini_key = settings.get("gemini_api_key", "") or os.environ.get("GEMINI_API_KEY", "")

    def is_available(self):
        """Check if any AI provider is configured."""
        return bool(self.groq_key or self.gemini_key)

    def generate_first_line(self, lead_data, audit_data=None):
        """
        Generate a personalized opening line from lead/SEO data.
        Returns str or None.
        """
        prompt = self._build_first_line_prompt(lead_data, audit_data)
        result = self._call_llm(prompt)
        if result:
            # Clean up: remove quotes, ensure single line
            result = result.strip().strip('"').strip("'")
            if "\n" in result:
                result = result.split("\n")[0]
        return result

    def generate_email(self, lead_data, template_style="value_first", audit_data=None):
        """
        Generate a complete personalized email.
        Returns dict with subject, body or None.
        """
        prompt = self._build_email_prompt(lead_data, template_style, audit_data)
        result = self._call_llm(prompt)
        if not result:
            return None

        # Parse subject and body
        lines = result.strip().split("\n")
        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif subject and not in_body:
                in_body = True
                body_lines.append(line)
            elif in_body:
                body_lines.append(line)

        if not subject and lines:
            subject = lines[0]
            body_lines = lines[1:]

        return {
            "subject": subject,
            "body": "\n".join(body_lines).strip(),
        }

    def generate_ab_variant(self, original_subject, original_body, lead_data):
        """
        Generate an A/B test variant of an existing email.
        Returns dict with subject, body or None.
        """
        prompt = f"""You are an expert cold email copywriter. Create a B variant of this email for A/B testing.
Keep the same intent and offer but change the angle, tone, or hook.

Original subject: {original_subject}
Original email:
{original_body[:500]}

Business: {lead_data.get('business_name', '')}
Niche: {lead_data.get('niche', '')}
Location: {lead_data.get('location', '')}

Write ONLY the new variant. Format:
Subject: [new subject]
[new body]

Rules:
- Different opening hook
- Same call to action
- Under 150 words
- Conversational tone
- No spam words"""

        result = self._call_llm(prompt)
        if not result:
            return None

        lines = result.strip().split("\n")
        subject = ""
        body_lines = []

        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif subject:
                body_lines.append(line)

        if not subject and lines:
            subject = lines[0]
            body_lines = lines[1:]

        return {
            "subject": subject,
            "body": "\n".join(body_lines).strip(),
        }

    def _build_first_line_prompt(self, lead_data, audit_data=None):
        """Build prompt for first line generation."""
        context = f"""Business: {lead_data.get('business_name', 'Unknown')}
Website: {lead_data.get('website', '')}
Niche: {lead_data.get('niche', '')}
Location: {lead_data.get('location', '')}
SEO Score: {lead_data.get('seo_score', 'N/A')}/100
SEO Issues: {lead_data.get('seo_issues', 'Unknown')}"""

        if audit_data:
            context += f"\nAudit Details: {str(audit_data)[:200]}"

        return f"""Write a personalized, specific opening line for a cold email to this business.
The opening should reference something specific about their website or business that shows you did research.

{context}

Rules:
- One sentence only
- Reference specific detail about their business
- Natural, conversational tone
- No generic phrases like "I noticed your business" or "I came across your website"
- Show genuine observation

Write ONLY the opening line, nothing else."""

    def _build_email_prompt(self, lead_data, style, audit_data=None):
        """Build prompt for full email generation."""
        styles = {
            "value_first": "Lead with a free, actionable tip they can implement today",
            "curiosity": "Open with a surprising insight or question about their market",
            "social_proof": "Reference results you've achieved for similar businesses",
            "direct": "Be straightforward about what you offer and why it matters to them",
        }
        style_guide = styles.get(style, styles["value_first"])

        return f"""Write a cold email to this business owner. Style: {style_guide}

Business: {lead_data.get('business_name', 'Unknown')}
Website: {lead_data.get('website', '')}
Niche: {lead_data.get('niche', '')}
Location: {lead_data.get('location', '')}
SEO Score: {lead_data.get('seo_score', 'N/A')}/100
Issues: {lead_data.get('seo_issues', 'various improvements available')}

Format response as:
Subject: [subject line]
[email body]

Rules:
- Under 150 words total
- Conversational, not salesy
- One clear call to action (suggest a quick call)
- Reference specific details about their business
- End with simple sign-off using {{your_name}}
- No spam words, no ALL CAPS, max 1 exclamation mark
- Don't use words like "guarantee", "free", "limited time"
"""

    def _call_llm(self, prompt):
        """Call LLM with fallback chain: Groq -> Gemini."""
        # Try Groq first (faster, higher limits)
        if self.groq_key:
            result = self._call_groq(prompt)
            if result:
                return result

        # Fallback to Gemini
        if self.gemini_key:
            result = self._call_gemini(prompt)
            if result:
                return result

        return None

    def _call_groq(self, prompt):
        """Call Groq API (OpenAI-compatible)."""
        try:
            resp = requests.post(
                self.GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def _call_gemini(self, prompt):
        """Call Google Gemini API."""
        try:
            url = f"{self.GEMINI_URL}?key={self.gemini_key}"
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 500,
                        "temperature": 0.7,
                    },
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass
        return None
