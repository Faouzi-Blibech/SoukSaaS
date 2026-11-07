"""Q&A generation, owner moderation and semantic matching over approved entries."""
import re
import threading

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import settings
from app.llm import chat_json, load_product
from app.models import QAEntry
from app.schemas import Product

# TF-IDF (char_wb 2-4 grams, stopwords stripped, scaled by the share of query n-grams the corpus
# knows) cosine scores live on a lower scale than embedding cosines (0.72). Calibrated on the
# seeded entries: EN/FR paraphrases and typos score 0.39-1.0 ("what are the session hours" 0.39,
# "remboursement possible?" 0.65); off-topic stays <= 0.34 ("tell me prices of laptops" 0.34,
# "do you sell laptops" 0.10, "weather in Paris" 0.12). 0.37 sits in that gap.
TFIDF_THRESHOLD = 0.37
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


_STOP = frozenset(
    ["a", "an", "the", "is", "are", "was", "be", "do", "does", "did", "can", "could", "will", "would", "i", "you", "we", "me", "my", "your", "it", "its", "to", "of", "in", "on", "at", "for", "and", "or", "what", "whats", "which", "who", "how", "there", "this", "that", "with", "about", "have", "has", "get", "want", "please", "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "est", "sont", "a", "ai", "as", "avez", "avons", "y", "il", "elle", "on", "je", "tu", "nous", "vous", "mon", "ma", "mes", "ce", "cet", "cette", "et", "ou", "que", "qui", "quoi", "quel", "quelle", "quels", "quelles", "en", "au", "aux", "pour", "par", "sur", "dans", "ca", "c", "s", "qu", "est-ce"])


def _norm(text: str) -> str:
    """Lowercase, drop punctuation and stopwords so shared function words do not inflate scores."""
    words = re.findall(r"\w+", text.lower())
    kept = [w for w in words if w not in _STOP]
    return " ".join(kept or words)


class QADraft(BaseModel):
    question: str
    variants: list[str] = Field(default_factory=list)
    answer: str


class QADraftList(BaseModel):
    entries: list[QADraft]


# ---------------------------------------------------------------- generation
def _mock_entries(p: Product) -> list[dict]:
    pol = p.policies
    plans = " / ".join(f"{pl.name}: {pl.price:g} {p.currency}" for pl in p.plans)
    feats = ", ".join(p.features)
    aud = " and ".join(p.audience)
    spec = [
        ("How much does it cost?", ["What is the price?", "Quel est le prix ?", "Combien ca coute ?", "Combien coute la formation ?"],
         f"{plans}."),
        ("What is included in the program?", ["What features do I get?", "Qu'est-ce qui est inclus ?"],
         f"{p.name} includes: {feats}."),
        ("When do the sessions take place?", ["What is the schedule?", "Quels sont les horaires ?"],
         pol.schedule),
        ("Is there a refund policy?", ["Can I get my money back?", "Quelle est la politique de remboursement ?"],
         pol.refund),
        ("Do I need prior experience?", ["What are the prerequisites?", "Faut-il des prerequis ?"],
         pol.prerequisites),
        ("Do I get a certificate?", ["Is there a certificate?", "Y a-t-il un certificat ?"], pol.certificate),
        ("Who is this program for?", ["Who can join?", "A qui s'adresse la formation ?"],
         f"It is designed for {aud}."),
        ("What is the difference between Standard and Pro?",
         ["Standard vs Pro?", "Quelle est la difference entre Standard et Pro ?"],
         f"Available plans: {plans}."),
        ("How can I contact you?", ["What is your contact email?", "Comment vous contacter ?"],
         f"Write to {p.contact}."),
    ]
    out = [{"question": q, "variants": v, "answer": a} for q, v, a in spec if a]
    known = {e["question"].lower() for e in out}
    for q in p.faq_seed:
        if q.lower() not in known:
            out.append({"question": q, "variants": [q.rstrip("?").strip(), f"Question: {q}"],
                        "answer": p.description})
    return out


def generate_qa(product: Product | None = None) -> list[QAEntry]:
    """Return UNSAVED draft entries (use save_drafts to persist)."""
    product = product or load_product()
    system = ("You write a customer FAQ for one product. Use only the product JSON. "
              'Reply as JSON {"entries":[{"question","variants","answer"}]} with 2-3 EN/FR variants each.')
    result = chat_json(system, product.model_dump_json(), QADraftList, task="qa_generate",
                       mock=lambda: {"entries": _mock_entries(product)})
    return [QAEntry(question=e.question, variants=list(e.variants), answer=e.answer, status="draft")
            for e in result.entries]


def save_drafts(session: Session, entries: list[QAEntry]) -> list[QAEntry]:
    for e in entries:
        session.add(e)
    session.commit()
    for e in entries:
        session.refresh(e)
    invalidate()
    return entries


# ---------------------------------------------------------------- moderation
def _get(session: Session, entry_id: str) -> QAEntry:
    entry = session.get(QAEntry, entry_id)
    if entry is None:
        raise KeyError(entry_id)
    return entry


def _set_status(session: Session, entry_id: str, status: str) -> QAEntry:
    entry = _get(session, entry_id)
    entry.status = status
    session.add(entry)
    session.commit()
    session.refresh(entry)
    invalidate()
    return entry


def approve(session: Session, entry_id: str) -> QAEntry:
    return _set_status(session, entry_id, "approved")


def reject(session: Session, entry_id: str) -> QAEntry:
    return _set_status(session, entry_id, "rejected")


def update(session: Session, entry_id: str, question: str, answer: str,
           variants: list[str]) -> QAEntry:
    """Edit an entry; it goes back to draft and needs re-approval."""
    entry = _get(session, entry_id)
    entry.question, entry.answer, entry.variants, entry.status = question, answer, list(variants), "draft"
    session.add(entry)
    session.commit()
    session.refresh(entry)
    invalidate()
    return entry


# ---------------------------------------------------------------- matching
class Matcher:
    """Scores a query against question + variants of approved entries (best text wins)."""

    def __init__(self, entries: list[QAEntry]):
        self.ids: list[str] = []
        texts: list[str] = []
        for e in entries:
            for t in [e.question, *e.variants]:
                self.ids.append(e.id)
                texts.append(t)
        self.texts = texts
        self.kind = "tfidf"
        self.threshold = TFIDF_THRESHOLD
        self._embed = None
        if not texts:
            return
        if settings.embedding_mode == "local" and self._init_embeddings():
            return
        self._init_tfidf()

    def _init_embeddings(self) -> bool:
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(EMBEDDING_MODEL)
            self._matrix = model.encode(self.texts, normalize_embeddings=True)
            self._embed = lambda q: model.encode([q], normalize_embeddings=True)[0]
            self.kind, self.threshold = "embeddings", settings.qa_similarity_threshold
            return True
        except Exception:  # noqa: BLE001  not installed or model unavailable: silent fallback
            return False

    def _init_tfidf(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=True,
                                    sublinear_tf=True)
        self._matrix = self._vec.fit_transform([_norm(t) for t in self.texts])

    def best(self, text: str) -> tuple[str | None, float]:
        if not self.texts or not text.strip():
            return None, 0.0
        if self.kind == "embeddings":
            sims = self._matrix @ self._embed(text)
        else:
            q = _norm(text)
            sims = (self._matrix @ self._vec.transform([q]).T).toarray().ravel()
            # Out-of-vocabulary n-grams are invisible to the cosine, so a query that is mostly
            # unknown words ("tell me prices of laptops") would score on its one shared word.
            # Scale by the fraction of the query's distinct n-grams that the corpus knows.
            grams = set(self._vec.build_analyzer()(q))
            if grams:
                sims = sims * (len(grams & set(self._vec.vocabulary_)) / len(grams)) ** 0.5
        i = int(sims.argmax())
        return self.ids[i], float(sims[i])


_lock = threading.Lock()
_cache: dict = {"sig": None, "matcher": None}


def invalidate() -> None:
    with _lock:
        _cache["sig"] = None
        _cache["matcher"] = None


def _get_matcher(entries: list[QAEntry]) -> Matcher:
    # The signature guards against edits made outside this module (e.g. seeding).
    sig = (settings.embedding_mode, tuple((e.id, e.question, tuple(e.variants)) for e in entries))
    with _lock:
        if _cache["sig"] != sig:
            _cache["matcher"] = Matcher(entries)
            _cache["sig"] = sig
        return _cache["matcher"]


def match(session: Session, text: str) -> tuple[QAEntry | None, float]:
    """Best approved entry if its score clears the active threshold, else (None, score)."""
    entries = list(session.exec(select(QAEntry).where(QAEntry.status == "approved").order_by(QAEntry.id)))
    matcher = _get_matcher(entries)
    entry_id, score = matcher.best(text)
    if entry_id is None or score < matcher.threshold:
        return None, score
    entry = session.get(QAEntry, entry_id)
    entry.hits += 1
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry, score
