"""End-to-end tests of main.py with Ollama faked out."""
import shutil
import smtplib
import sqlite3
import sys

import pytest

import main
from conftest import fake_vector


@pytest.fixture
def small_setup(tmp_path, resumes_dir, jd_csv, monkeypatch, fake_ollama):
    """6 resumes + the real 20 JDs, a temp DB, and no real LLM."""
    rdir = tmp_path / "resumes"
    rdir.mkdir()
    for pdf in sorted(resumes_dir.glob("*.pdf"))[:6]:
        shutil.copy(pdf, rdir)
    monkeypatch.chdir(tmp_path)  # diagram files get written to the cwd
    monkeypatch.setattr("agents.jd_summarizer.ollama.chat",
                        lambda **k: (_ for _ in ()).throw(ConnectionError("no chat model")))
    return {"rdir": str(rdir), "csv": str(jd_csv), "db": str(tmp_path / "t.db")}


def run(setup, *extra, monkeypatch):
    argv = ["main.py", "--jd-file", setup["csv"], "--resumes-dir", setup["rdir"],
            "--db-file", setup["db"], "--threshold", "0", *extra]
    monkeypatch.setattr(sys, "argv", argv)
    main.run_pipeline(main.parse_arguments())


def table_count(db, table):
    with sqlite3.connect(db) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_pipeline_runs_and_is_idempotent(small_setup, monkeypatch):
    run(small_setup, monkeypatch=monkeypatch)
    first = {t: table_count(small_setup["db"], t) for t in ("jd_summaries", "cv_data", "match_scores", "shortlist")}
    assert first["jd_summaries"] == 20 and first["cv_data"] == 6 and first["match_scores"] == 120

    run(small_setup, monkeypatch=monkeypatch)       # second run must not add rows
    second = {t: table_count(small_setup["db"], t) for t in first}
    assert second == first


def test_stored_candidate_names_are_real(small_setup, monkeypatch):
    run(small_setup, monkeypatch=monkeypatch)
    with sqlite3.connect(small_setup["db"]) as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM cv_data")]
    assert "Candidate Resume" not in names and len(set(names)) == 6


def test_top_n_limits_shortlist_per_job(small_setup, monkeypatch):
    run(small_setup, "--top-n", "2", monkeypatch=monkeypatch)
    assert table_count(small_setup["db"], "shortlist") == 20 * 2


def test_exits_cleanly_when_ollama_is_down(small_setup, monkeypatch, capsys):
    monkeypatch.setattr("utils.embeddings.ollama.embeddings",
                        lambda model, prompt: (_ for _ in ()).throw(ConnectionError("refused")))
    with pytest.raises(SystemExit) as exc:
        run(small_setup, monkeypatch=monkeypatch)
    assert exc.value.code == 1
    assert "ollama pull" in capsys.readouterr().out
    assert not __import__("os").path.exists(small_setup["db"])   # nothing written from fake data


def test_send_emails_is_simulated_by_default(small_setup, monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: pytest.fail("SMTP used without --live"))
    run(small_setup, "--top-n", "1", "--send-emails", monkeypatch=monkeypatch)
    with sqlite3.connect(small_setup["db"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM shortlist WHERE email_sent = 1").fetchone()[0] == 0


def test_live_mode_sends_and_records_status(small_setup, monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, *a): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): pass
        def login(self, *a): pass
        def sendmail(self, frm, to, msg): sent.append(to)

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SENDER_EMAIL", "hr@co.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "secret")
    run(small_setup, "--top-n", "1", "--send-emails", "--live", monkeypatch=monkeypatch)
    assert len(sent) == 20
    with sqlite3.connect(small_setup["db"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM shortlist WHERE email_sent = 1").fetchone()[0] == 20


def test_live_without_credentials_exits(small_setup, monkeypatch):
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("SENDER_EMAIL", raising=False)
    with pytest.raises(SystemExit):
        run(small_setup, "--send-emails", "--live", monkeypatch=monkeypatch)


@pytest.mark.parametrize("bad", [["--skill-weight", "2"], ["--top-n", "0"], ["--live"]])
def test_invalid_arguments_are_rejected(bad, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", *bad])
    with pytest.raises(SystemExit):
        main.parse_arguments()
