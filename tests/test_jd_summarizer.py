import json

from agents.jd_summarizer import JDSummarizerAgent

JD = {"title": "Backend Developer",
      "description": "Responsibilities:\n- Build APIs\nQualifications:\nProficiency in Python and SQL. 3 years of experience."}


def llm_reply(payload):
    return {"message": {"content": json.dumps(payload)}}


def test_csv_with_non_utf8_bytes_loads_all_jobs(jd_csv):
    jds = JDSummarizerAgent(str(jd_csv)).load_jds()      # the real CSV contains a 0x92 byte
    assert len(jds) == 20
    assert jds[0]["title"] == "Software Engineer"


def test_llm_path_is_used_with_a_chat_model(monkeypatch):
    seen = {}

    def chat(model, messages, format=None):
        seen.update(model=model, format=format)
        return llm_reply({"required_skills": ["Python", "SQL"], "years_of_experience": "3",
                          "education": "BSc", "certifications": [], "responsibilities": ["Build APIs"]})

    monkeypatch.setattr("agents.jd_summarizer.ollama.chat", chat)
    monkeypatch.delenv("OLLAMA_CHAT_MODEL", raising=False)
    result = JDSummarizerAgent().summarize_jd(JD)
    assert seen["model"] == "llama3" and seen["model"] != "nomic-embed-text"
    assert seen["format"] == "json"
    assert result["extraction_method"] == "llm"
    assert result["required_skills"] == ["Python", "SQL"]


def test_chat_model_is_configurable(monkeypatch):
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "mistral")
    assert JDSummarizerAgent().chat_model == "mistral"


def test_llm_output_types_are_normalised(monkeypatch):
    """Models sometimes return a list where a string is expected; SQLite can't store lists."""
    monkeypatch.setattr("agents.jd_summarizer.ollama.chat", lambda **k: llm_reply(
        {"required_skills": "Python, SQL", "years_of_experience": 3,
         "education": ["BSc", "MSc"], "certifications": None, "responsibilities": ["a", "b"]}))
    r = JDSummarizerAgent().summarize_jd(JD)
    assert r["required_skills"] == ["Python", "SQL"]
    assert r["years_of_experience"] == "3"
    assert r["education"] == "BSc, MSc"
    assert r["certifications"] == []


def test_falls_back_to_rules_and_only_tries_the_llm_once(monkeypatch, capsys):
    calls = []

    def chat(**kwargs):
        calls.append(1)
        raise ConnectionError("ollama not running")

    monkeypatch.setattr("agents.jd_summarizer.ollama.chat", chat)
    agent = JDSummarizerAgent()
    results = [agent.summarize_jd(JD) for _ in range(3)]
    assert len(calls) == 1                                   # no retry storm
    assert all(r["extraction_method"] == "rules" for r in results)
    assert "LLM extraction unavailable" in capsys.readouterr().out


def test_invalid_json_from_llm_falls_back(monkeypatch):
    monkeypatch.setattr("agents.jd_summarizer.ollama.chat",
                        lambda **k: {"message": {"content": "sorry, here is some prose"}})
    assert JDSummarizerAgent().summarize_jd(JD)["extraction_method"] == "rules"
