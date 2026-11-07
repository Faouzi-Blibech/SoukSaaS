import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from app.models import Interaction, Lead, Payment, Prospect, QAEntry
from app.schemas import PayRequest, Product
from scripts.seed import seed

ROOT = Path(__file__).resolve().parents[2]


def test_product_json_validates():
    product = Product.model_validate(json.loads((ROOT / "data" / "product.json").read_text("utf-8")))
    assert {p.id for p in product.plans} == {"std", "pro"}
    assert product.currency == "TND"


def test_seed_counts_and_no_card_like_numbers():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    c = seed(eng)
    assert c["Prospect"] == 40 and c["Interaction"] == 80
    assert c["Payment"] == 30 and c["Lead"] == 25 and c["QAEntry"] >= 3
    with Session(eng) as s:
        texts = []
        for m in (Prospect, Interaction, Payment, Lead, QAEntry):
            texts += [json.dumps(r.model_dump(), default=str) for r in s.exec(select(m)).all()]
        assert not re.search(r"\d{13,19}", " ".join(texts).replace(" ", "").replace("-", ""))
        assert {p.status for p in s.exec(select(Payment)).all()} >= {
            "succeeded", "declined", "pending", "held_for_approval", "approved", "rejected"}
        consent = [x.consent for x in s.exec(select(Lead)).all()]
        assert 0.6 <= sum(consent) / len(consent) <= 0.8


def test_request_schema_rejects_extra_field():
    with pytest.raises(ValidationError):
        PayRequest(session_id="s", plan_id="std", test_token="tok_success", card_number="x")
