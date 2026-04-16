import pytest
import asyncio
import pandas as pd
from unittest.mock import MagicMock, AsyncMock

import agent  # adjust to your actual module
from agent import (
    is_valid_pairing,
    query_university_context,
    email_transcript,
    transfer_to_human,
    CallState,
)

# If resend is imported in agent.py, we patch it there
import resend


def make_parsed(group: str, subgroup: str):
    mock = MagicMock()
    mock.group = group
    mock.subgroup = subgroup
    return mock


# ---- is_valid_pairing tests ----

class TestIsValidPairing:

    def test_valid_pairing(self):
        assert is_valid_pairing("Dining_food", "Dining_Halls") is True

    def test_valid_pairing_contact_info_shared_subgroup(self):
        assert is_valid_pairing("Safety", "Contact_Info") is True
        assert is_valid_pairing("Housing", "Contact_Info") is True

    def test_valid_pairing_no_matching_group(self):
        assert is_valid_pairing("No_Matching_Group", "NoSubgroup") is True

    def test_valid_pairing_not_applicable(self):
        assert is_valid_pairing("NotApplicable", "NotApplicable") is True

    def test_invalid_subgroup_for_valid_group(self):
        assert is_valid_pairing("Safety", "Dining_Halls") is False

    def test_invalid_group(self):
        assert is_valid_pairing("Nonexistent_Group", "Contact_Info") is False

    def test_empty_strings(self):
        assert is_valid_pairing("", "") is False

    def test_case_sensitivity(self):
        assert is_valid_pairing("dining_food", "dining_halls") is False
        assert is_valid_pairing("Dining_food", "dining_halls") is False


# ---- query_university_context tests ----

class TestQueryUniversityContext:

    def test_valid_lookup(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Safety_Card_Entry"],
            "Information Text": ["All buildings require card access."],
            "Source(url)": ["https://example.com/safety"]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Safety", "Card_Entry")
        context, urls, key = query_university_context(parsed)

        assert key == "Safety_Card_Entry"
        assert context == "All buildings require card access."
        assert urls == "https://example.com/safety"

    def test_multiple_urls_split_by_pipe(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Housing_Housing_Cost"],
            "Information Text": ["Housing costs vary."],
            "Source(url)": ["https://a.com|https://b.com|https://c.com"]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Housing", "Housing_Cost")
        context, urls, key = query_university_context(parsed)

        assert urls == "https://a.com\nhttps://b.com\nhttps://c.com"

    def test_nan_url_returns_empty_string(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Athletics_Intramural"],
            "Information Text": ["Intramural sports info."],
            "Source(url)": [float("nan")]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Athletics", "Intramural")
        context, urls, key = query_university_context(parsed)

        assert context == "Intramural sports info."
        assert urls == ""

    def test_empty_string_url_returns_empty(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Athletics_Intramural"],
            "Information Text": ["Info here."],
            "Source(url)": [""]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Athletics", "Intramural")
        _, urls, _ = query_university_context(parsed)

        assert urls == ""

    def test_no_matching_row_returns_empty(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Safety_Card_Entry"],
            "Information Text": ["Some info."],
            "Source(url)": ["https://example.com"]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Housing", "Layout_Info")
        context, urls, key = query_university_context(parsed)

        assert context == ""
        assert urls == ""
        assert key == "Housing_Layout_Info"

    def test_duplicate_rows_returns_empty(self, monkeypatch):
        test_db = pd.DataFrame({
            "Lookup_Key": ["Safety_Card_Entry", "Safety_Card_Entry"],
            "Information Text": ["Info 1", "Info 2"],
            "Source(url)": ["url1", "url2"]
        })
        monkeypatch.setattr(agent, "db", test_db)

        parsed = make_parsed("Safety", "Card_Entry")
        context, urls, key = query_university_context(parsed)

        assert context == ""
        assert urls == ""
        assert key == "Safety_Card_Entry"


# ---- email_transcript tests ----

class TestEmailTranscript:

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, monkeypatch):
        captured = {}

        def fake_send(payload):
            captured.update(payload)

        monkeypatch.setattr(resend.Emails, "send", fake_send)

        call = CallState()
        call.email = "test@gmail.com"
        call.transcript = [
            {"speaker": "User", "text": "Tell me about housing"},
            {"speaker": "Agent", "text": "Housing costs vary.", "urls": "https://example.com"},
        ]

        await email_transcript(call, "English", MagicMock())

        assert captured["to"] == ["test@gmail.com"]
        assert "Housing costs vary." in captured["text"]
        assert "https://example.com" in captured["text"]
        assert captured["from"] == "onboarding@resend.dev"

    @pytest.mark.asyncio
    async def test_includes_urls_in_transcript(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(resend.Emails, "send", lambda p: captured.update(p))

        call = CallState()
        call.email = "test@gmail.com"
        call.transcript = [
            {"speaker": "Agent", "text": "Here is info.", "urls": "https://a.com\nhttps://b.com"},
        ]

        await email_transcript(call, "English", MagicMock())

        assert "https://a.com" in captured["text"]
        assert "https://b.com" in captured["text"]
        assert "Reference URLs:" in captured["text"]

    @pytest.mark.asyncio
    async def test_no_urls_field_still_works(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(resend.Emails, "send", lambda p: captured.update(p))

        call = CallState()
        call.email = "test@gmail.com"
        call.transcript = [
            {"speaker": "User", "text": "Hello"},
        ]

        await email_transcript(call, "English", MagicMock())

        assert "Hello" in captured["text"]
        assert "Reference URLs" not in captured["text"]

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_early(self, monkeypatch):
        send_called = False

        def fake_send(payload):
            nonlocal send_called
            send_called = True

        monkeypatch.setattr(resend.Emails, "send", fake_send)

        call = CallState()
        call.email = "test@gmail.com"
        call.transcript = []

        await email_transcript(call, "English", MagicMock())

        assert send_called is False


# ---- transfer_to_human tests ----

class TestTransferToHuman:

    @pytest.mark.asyncio
    async def test_sets_ending_state(self, monkeypatch):
        mock_call = MagicMock()
        mock_client = MagicMock()
        mock_client.calls.return_value = mock_call
        monkeypatch.setattr(agent, "TwilioClient", lambda sid, token: mock_client)
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "fake_sid")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake_token")
        monkeypatch.setenv("FORWARDING_PHONE_NUMBER", "+1234567890")

        call = CallState()
        call.call_sid = "CA123"
        call.language = "English"
        ws = MagicMock()
        ws.send_json = AsyncMock()

        await transfer_to_human("transfer me", call, ws)

        assert call.ending_state is True

    @pytest.mark.asyncio
    async def test_calls_twilio_with_correct_sid(self, monkeypatch):
        mock_call = MagicMock()
        mock_client = MagicMock()
        mock_client.calls.return_value = mock_call
        monkeypatch.setattr(agent, "TwilioClient", lambda sid, token: mock_client)
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "fake_sid")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake_token")
        monkeypatch.setenv("FORWARDING_PHONE_NUMBER", "+1234567890")

        call = CallState()
        call.call_sid = "CA123"
        call.language = "English"
        ws = MagicMock()
        ws.send_json = AsyncMock()

        await transfer_to_human("transfer me", call, ws)

        mock_client.calls.assert_called_with("CA123")
        mock_call.update.assert_called_once()
        twiml = mock_call.update.call_args[1]["twiml"]
        assert "+1234567890" in twiml

    @pytest.mark.asyncio
    async def test_sends_message_before_transfer(self, monkeypatch):
        mock_call = MagicMock()
        mock_client = MagicMock()
        mock_client.calls.return_value = mock_call
        monkeypatch.setattr(agent, "TwilioClient", lambda sid, token: mock_client)
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "fake_sid")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake_token")
        monkeypatch.setenv("FORWARDING_PHONE_NUMBER", "+1234567890")

        call = CallState()
        call.call_sid = "CA123"
        call.language = "English"
        ws = MagicMock()
        ws.send_json = AsyncMock()

        await transfer_to_human("transfer me", call, ws)

        ws.send_json.assert_called()
        first_call = ws.send_json.call_args_list[0][0][0]
        assert first_call["type"] == "text"
        assert first_call["last"] is True