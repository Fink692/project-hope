"""Run a privacy-safe live smoke test against the configured local Ollama models."""

import json

import main


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run() -> dict[str, object]:
    health = main.healthz()
    models = health["models"]
    require(health["status"] == "ok", "Configured models are not ready.")
    require(models.get("chatReady") is True, "Chat model is not ready.")
    require(models.get("embeddingReady") is True, "Embedding model is not ready.")

    classification = main.classify_intent(
        main.TextRequest(text="Please help me schedule a volunteer orientation."), None
    )
    require(classification["semantic"] is True, "Classification used fallback.")
    require(classification["requiresHuman"] is True, "Human gate was removed.")

    crisis = main.classify_intent(
        main.TextRequest(text="This is an emergency and I am in immediate danger."),
        None,
    )
    require(crisis["intent"] == "human_transfer", "Crisis transfer failed.")
    require(crisis["semantic"] is False, "Crisis path reached the language model.")

    draft = main.draft_email(
        main.DraftEmailRequest(
            subject="Volunteer orientation",
            untrusted_body="Could I attend the Tuesday orientation?",
        ),
        None,
    )
    require(draft["semantic"] is True, "Email drafting used fallback.")
    require(
        "human_approval_required" in draft["riskFlags"],
        "Draft approval gate was removed.",
    )

    translation = main.translate(
        main.TranslationRequest(
            source_language="en",
            target_language="fr",
            text="Thank you for volunteering with our community programme.",
        ),
        None,
    )
    require(translation["provider"] == "ollama", "Translation used fallback.")

    plain = main.plain_language(
        main.TextRequest(
            text="Individuals may commence the application approximately two weeks before orientation."
        ),
        None,
    )
    require(plain["provider"] == "ollama", "Plain-language rewrite used fallback.")

    grant = main.answer_grant(
        main.GrantAnswerRequest(
            question="How many volunteers completed orientation?",
            passages=[
                {
                    "id": "evidence-1",
                    "text": "In 2025, 42 volunteers completed orientation.",
                }
            ],
        ),
        None,
    )
    require(grant["provider"] == "ollama", "Grant answer used fallback.")
    require(
        set(grant["citations"]).issubset({"evidence-1"}),
        "Grant answer returned an invented citation.",
    )

    embedding = main.embed(
        main.TextRequest(text="volunteer orientation and community support"), None
    )
    require(embedding["semantic"] is True, "Embedding used fallback.")
    require(len(embedding["embedding"]) >= 128, "Embedding is unexpectedly short.")

    return {
        "status": "ok",
        "chat_model": models["chatModel"],
        "embedding_model": models["embeddingModel"],
        "classification": classification["provider"],
        "drafting": draft["provider"],
        "translation": translation["provider"],
        "plain_language": plain["provider"],
        "grant_answer": grant["provider"],
        "embedding_dimensions": len(embedding["embedding"]),
        "crisis_override": crisis["provider"],
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
