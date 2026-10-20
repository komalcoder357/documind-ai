
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import llm, rag
from .evidence import validate_citation, add_evidence
from .models import Document, Conversation, Message, User


INSUFFICIENT = (
    "I could not find sufficient supporting evidence in the selected "
    "documents to answer this reliably."
)

DOC_CITATION_PATTERN = re.compile(r"\[\[DOC:(\d+)\]\]")


def answer_question(
    db: Session,
    user: User,
    ws: list[int],
    doc_ids: list[int],
    question: str,
    conv_id=None,
    top_k=5,
):
    docs = {
        d.id: d
        for d in db.scalars(
            select(Document).where(
                Document.id.in_(doc_ids),
                Document.workspace_id.in_(ws),
                Document.status == "ready",
            )
        )
    }

    if not docs:
        return None

    conv = None

    if conv_id:
        conv = db.get(Conversation, conv_id)
        if (
            not conv
            or conv.user_id != user.id
            or conv.workspace_id not in ws
        ):
            return "bad_conversation"
    else:
        conv = Conversation(
            workspace_id=ws[0],
            user_id=user.id,
            title=question[:80],
        )
        db.add(conv)
        db.flush()

    history = [
        {"role": m.role, "content": m.content}
        for m in db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(6)
        )
    ][::-1]

    query = question

    if history and len(question.split()) < 6:
        prev = next(
            (
                m["content"]
                for m in reversed(history)
                if m["role"] == "user"
            ),
            "",
        )
        query = prev + " " + question

    hits, pipeline = rag.retrieve(
        db, ws, list(docs), query, top_k=top_k
    )

    db.add(
        Message(
            conversation_id=conv.id,
            role="user",
            content=question,
        )
    )

    result = {
        "conversation_id": conv.id,
        "pipeline": pipeline,
        "citations": [],
        "insufficient": False,
        "mode": None,
        "citation_status": "none",
        "warnings": [],
    }

    if not hits:
        result.update(
            answer=INSUFFICIENT,
            insufficient=True,
            mode="no_evidence",
        )
    else:
        passages = [h["chunk"].text for h in hits]

        try:
            answer, mode = llm.generate(
                question, passages, history
            )
        except llm.LLMUnavailable as e:
            answer = llm.extractive(passages)
            mode = "extractive_fallback"
            result["warnings"].append(
                f"LLM provider failed ({e}); showing extractive passages."
            )

        am = Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer,
        )
        db.add(am)
        db.flush()

        # Only the dedicated [[DOC:N]] tokens count as DocuMind citations.
        cited = sorted(
            {
                int(match)
                for match in DOC_CITATION_PATTERN.findall(answer)
            }
        )

        bad = [
            n for n in cited
            if not 1 <= n <= len(hits)
        ]

        valid_numbers = [
            n for n in cited if n not in bad
        ]

        # Extractive mode includes explicit tokens for its passages.
        shown = valid_numbers or (
            list(range(1, min(3, len(hits)) + 1))
            if mode == "extractive_fallback"
            else []
        )

        for n in shown:
            hit = hits[n - 1]
            chunk = hit["chunk"]

            ok, why = validate_citation(
                db,
                ws,
                chunk.id,
                chunk.document_id,
                chunk.page,
            )

            if not ok:
                bad.append(n)
                continue

            ev = add_evidence(
                db,
                chunk.workspace_id,
                "chunk",
                chunk.id,
                (
                    f"{docs[chunk.document_id].title}, page {chunk.page}"
                    if chunk.page
                    else docs[chunk.document_id].title
                ),
                f"Passage supporting answer to: {question[:200]}",
                chunk.text[:600],
                f"hybrid_retrieval:{mode}",
                "not_checked",
                {
                    "relevance": hit["fused"],
                    "citation_valid": True,
                },
                am.id,
            )

            result["citations"].append(
                {
                    "n": n,
                    "evidence_id": ev.id,
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_title": docs[chunk.document_id].title,
                    "page": chunk.page,
                    "heading": chunk.heading,
                    "excerpt": chunk.text[:600],
                }
            )

        bad = sorted(set(bad))

        if result["citations"] and not bad:
            result["citation_status"] = "valid"
        elif result["citations"]:
            result["citation_status"] = "partially_invalid"
        else:
            result["citation_status"] = "none"

        if bad:
            result["warnings"].append(
                f"Removed invalid DocuMind citation token(s): {bad}."
            )

        # Convert only dedicated DocuMind tokens for the existing UI.
        # Ordinary [1], [2], etc. inside source text remain untouched.
        verified_numbers = {
            citation["n"] for citation in result["citations"]
        }

        def render_citation(match):
            number = int(match.group(1))
            if number in verified_numbers:
                return f"[{number}]"
            return ""

        answer = DOC_CITATION_PATTERN.sub(
            render_citation, answer
        )

        if mode == "llm" and not result["citations"]:
            result["warnings"].append(
                "The answer contains no verified DocuMind citations; "
                "treat it with caution."
            )

        am.content = answer
        am.meta = {
            "citations": [
                c["chunk_id"] for c in result["citations"]
            ],
            "mode": mode,
        }

        result.update(answer=answer, mode=mode)

    if result["insufficient"]:
        db.add(
            Message(
                conversation_id=conv.id,
                role="assistant",
                content=INSUFFICIENT,
                meta={"insufficient": True},
            )
        )

    db.commit()
    return result
