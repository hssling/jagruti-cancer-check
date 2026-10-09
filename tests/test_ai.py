"""Check the OpenRouter request shape and the safety of what comes back, with no network."""
import json

import httpx2
import openai

import ai


def capture_openrouter(reply_content, model=None):
    """An OpenRouterBackend whose HTTP calls are answered locally; returns (backend, sent requests)."""
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "gen-1", "object": "chat.completion", "created": 0, "model": "anthropic/claude-opus-5.5",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": reply_content}}]})

    backend = ai.OpenRouterBackend("test-key", model)
    backend.client = openai.OpenAI(api_key="test-key", base_url="https://openrouter.ai/api/v1",
                                   http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    return backend, sent


def test_openrouter_is_preferred_and_defaults_to_free_models():
    c = ai.make_client(openrouter_key="k", anthropic_key="k2")
    assert isinstance(c, ai.OpenRouterBackend)
    assert c.free and c.model == ai.FREE_MODELS[0]
    assert c.extra["models"] == ai.FREE_MODELS and c.extra["reasoning"] == {"enabled": False}
    assert ai.make_client(openrouter_key="k", openrouter_model="anthropic/claude-haiku-5.5").model == "anthropic/claude-haiku-5.5"
    assert isinstance(ai.make_client(anthropic_key="k2"), ai.AnthropicBackend)
    assert ai.make_client() is None


def test_story_request_and_untrusted_reply_filtering():
    reply = json.dumps({
        "answers": [{"id": "age", "value": "48"}, {"id": "sex", "value": "male"},
                    {"id": "mouthUlcer", "value": "true"},
                    {"id": "age", "value": "480"},          # out of range: ignored, keeps 48
                    {"id": "diagnosis", "value": "cancer"}],  # not a form field: ignored
        "follow_up_questions": ["Do you smoke?"], "language": "Kannada"})
    backend, sent = capture_openrouter(reply)
    found, questions, lang = ai.read_story(backend, "ನನಗೆ 48 ವರ್ಷ")
    assert found == {"age": 48, "sex": "male", "mouthUlcer": True}
    assert questions == ["Do you smoke?"] and lang == "Kannada"
    body = sent[0]  # free models: fallback list, no strict schema, thinking off
    assert body["model"] == ai.FREE_MODELS[0] and body["models"] == ai.FREE_MODELS
    assert "response_format" not in body
    assert body["reasoning"] == {"enabled": False}


def test_paid_model_gets_strict_schema():
    reply = json.dumps({"answers": [], "follow_up_questions": [], "language": "English"})
    backend, sent = capture_openrouter(reply, model="anthropic/claude-haiku-5.5")
    ai.read_story(backend, "hello")
    assert sent[0]["response_format"]["type"] == "json_schema"
    assert sent[0]["reasoning"] == {"effort": "low"} and "models" not in sent[0]


def test_all_free_models_busy_gives_a_message():
    def handler(request):
        return httpx2.Response(200, json={"error": {"message": "Provider returned error", "code": 429}})
    backend = ai.OpenRouterBackend("k")
    backend.client = openai.OpenAI(api_key="k", base_url="https://openrouter.ai/api/v1",
                                   http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    try:
        ai.read_story(backend, "hello")
    except ai.AIError as e:
        assert "could not answer" in str(e)
    else:
        raise AssertionError("expected AIError")


def test_json_wrapped_in_text_is_still_read():
    backend, _ = capture_openrouter('Here you go:\n{"answers": [{"id": "age", "value": "60"}], '
                                    '"follow_up_questions": [], "language": "English"}')
    found, _, _ = ai.read_story(backend, "I am 60")
    assert found == {"age": 60}


def test_api_errors_become_friendly_messages():
    def handler(request):
        return httpx2.Response(402, json={"error": {"message": "Insufficient credits", "code": 402}})
    backend = ai.OpenRouterBackend("k")
    backend.client = openai.OpenAI(api_key="k", base_url="https://openrouter.ai/api/v1", max_retries=0,
                                   http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    try:
        ai.read_story(backend, "hello")
    except ai.AIError as e:
        assert "credits" in str(e)
    else:
        raise AssertionError("expected AIError")
