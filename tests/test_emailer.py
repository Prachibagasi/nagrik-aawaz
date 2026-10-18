import smtplib

import pytest

from agents.emailer import EmailerAgent


def test_email_uses_candidate_name_and_matched_skills():
    e = EmailerAgent(simulate=True)
    body = e.generate_email_content({"name": "Alyssa Chavez", "skills": "Python, SQL"},
                                    "Backend Developer", "Python, Docker")
    assert "Dear Alyssa Chavez," in body
    assert "Backend Developer" in body
    assert "experience in: Python." in body          # Docker isn't a match


def test_email_without_matching_skills_omits_the_sentence():
    body = EmailerAgent(simulate=True).generate_email_content(
        {"name": "A", "skills": "Photoshop"}, "Dev", "Python")
    assert "particularly impressed" not in body


def test_simulated_send_never_touches_smtp(monkeypatch, capsys):
    def no_smtp(*a, **k):
        raise AssertionError("SMTP must not be used in simulation mode")
    monkeypatch.setattr(smtplib, "SMTP", no_smtp)
    assert EmailerAgent(simulate=True).send_email("a@b.com", "Subject: Hi\n\nBody") is True
    assert "Simulated Email" in capsys.readouterr().out


def test_live_mode_without_credentials_fails_fast(monkeypatch):
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("SENDER_EMAIL", raising=False)
    with pytest.raises(ValueError, match="EMAIL_PASSWORD"):
        EmailerAgent(simulate=False)


def test_live_mode_sends_via_smtp(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, server, port): sent["server"] = (server, port)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): sent["tls"] = True
        def login(self, user, pw): sent["login"] = (user, pw)
        def sendmail(self, frm, to, msg): sent.update(frm=frm, to=to, msg=msg)

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    e = EmailerAgent(smtp_server="smtp.test", port=2525, sender_email="hr@co.com",
                     password="secret", simulate=False)
    assert e.send_email("cand@x.com", "Subject: Interview\n\nHello") is True
    assert sent["server"] == ("smtp.test", 2525) and sent["tls"] and sent["to"] == "cand@x.com"
    assert "Subject: Interview" in sent["msg"]


def test_candidates_without_email_are_skipped(capsys):
    e = EmailerAgent(simulate=True)
    results = e.send_interview_invitations(
        [{"job_title": "Dev", "name": "NoMail", "email": ""},
         {"job_title": "Dev", "name": "HasMail", "email": "h@x.com", "skills": "Python"}],
        {"Dev": {"summary": {"required_skills": ["Python"]}}})
    assert [r["email"] for r in results] == ["h@x.com"]
