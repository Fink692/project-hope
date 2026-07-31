import hashlib
import hmac
import os
import re

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


runtime_environment = os.environ.get("AI_GATEWAY_ENV", "development").lower()
app = FastAPI(
    title="Project Hope bounded AI gateway",
    version="1.0.0",
    docs_url="/docs" if runtime_environment != "production" else None,
    redoc_url="/redoc" if runtime_environment != "production" else None,
)


class TextRequest(BaseModel):
    text: str = Field(max_length=12000)


class DraftEmailRequest(BaseModel):
    subject: str = Field(default="Follow-up from Project Hope", max_length=500)
    untrusted_body: str = Field(default="", max_length=12000)


def require_gateway_token(
    x_project_hope_gateway_token: str | None = Header(default=None),
):
    expected = os.environ.get("AI_GATEWAY_TOKEN", "")
    if expected and not x_project_hope_gateway_token:
        raise HTTPException(status_code=401, detail="Gateway token required.")
    if expected and not hmac.compare_digest(x_project_hope_gateway_token or "", expected):
        raise HTTPException(status_code=403, detail="Invalid gateway token.")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "runtime": "deterministic-local-adapter-v1", "side_effects": False}


@app.post("/v1/classify-intent")
def classify_intent(request: TextRequest, _: None = Depends(require_gateway_token)):
    text = request.text.lower()
    crisis_terms = [term for term in ("suicide", "emergency", "abuse", "overdose", "immediate danger") if term in text]
    if crisis_terms:
        return {"intent": "human_transfer", "riskFlags": crisis_terms, "requiresHuman": True}
    if any(term in text for term in ("appointment", "book", "schedule")):
        intent = "appointment"
    elif any(term in text for term in ("resource", "food", "housing", "support")):
        intent = "resource_search"
    else:
        intent = "human_transfer"
    return {"intent": intent, "riskFlags": ["human_review_required"], "requiresHuman": True}


@app.post("/v1/embed")
def embed(request: TextRequest, _: None = Depends(require_gateway_token)):
    words = re.findall(r"[a-z0-9]+", request.text.lower())
    vector = [int(hashlib.sha256(f"{word}:{index}".encode()).hexdigest()[:8], 16) / 2**32 for index, word in enumerate(words[:16])]
    return {"embedding": vector, "semantic": False, "model": "deterministic-hash-v1"}


@app.post("/v1/draft-email")
def draft_email(request: DraftEmailRequest, _: None = Depends(require_gateway_token)):
    return {
        "subject": request.subject,
        "body": "Thank you for contacting us. A staff member will review your message and follow up with you.\n\nThis draft requires human review before sending.",
        "citations": [],
        "riskFlags": ["untrusted_input", "human_approval_required"],
        "untrustedInputHash": hashlib.sha256(request.untrusted_body.encode()).hexdigest(),
    }
