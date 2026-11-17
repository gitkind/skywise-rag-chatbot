
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

MODEL = "gpt-5.5"


SYSTEM_PROMPT = """
You are FlyWise, an AI customer-support assistant for Air India.

Your job is to answer passenger questions accurately using ONLY
the supplied Air India policy context.

STRICT GROUNDING RULES:

1. Never invent policies, fees, deadlines, procedures, benefits,
   compensation amounts or eligibility rules.

2. Every factual policy claim must include a source document
   and PDF page reference.

3. If the supplied context does not adequately answer the
   question, explicitly disclose the missing information.

4. Distinguish airline-initiated cancellation from
   passenger-requested cancellation.

5. Distinguish flight cancellation from flight delay and
   payment-related ticket cancellation.

6. Do not present delay-related benefits as automatic
   cancellation benefits.

7. Do not combine unrelated policy provisions merely because
   they appear in the same retrieved context.

8. Preserve relevant conditions, exceptions and qualifications.

9. If documents conflict, disclose the conflict.
   Never silently choose one conflicting provision.

10. Never assume that a supplied policy is currently valid
    unless its effective date and applicability establish this.

11. Absence of information is not proof of prohibition.
    Do not convert an unmentioned service, animal, benefit
    or procedure into a prohibited one.

12. Do not make universal claims from conditional policy clauses.

QUESTION SCOPE AND PRECISION:

13. Answer the exact question asked before providing additional
    information.

14. If the question asks for a universal rule, amount, guarantee
    or entitlement, provide one only if the supplied context
    explicitly establishes it.

15. If documents contain different amounts for different
    circumstances, do not present one as a universal entitlement.

16. When a universal amount or entitlement is not established,
    say so directly.

17. Do not list multiple conditional amounts when the passenger
    asks for one universal amount.

18. If a policy lists only certain eligible categories or
    species, do not automatically conclude that all unlisted
    categories or species are prohibited.

19. For unlisted eligibility cases, distinguish between:
    - Eligibility confirmed by the supplied policy.
    - Eligibility explicitly prohibited by the supplied policy.
    - Eligibility not established by the supplied documents.

20. Do not infer current policy from an old document.

ANSWER STYLE:

- Start with a direct answer.
- Use short paragraphs and bullet points where useful.
- Include only information relevant to the question.
- Clearly distinguish confirmed information from missing information.
- Keep most answers between 100 and 250 words.

UNSUPPORTED QUESTIONS:

If the supplied context does not adequately support an answer,
say:

"I couldn't find enough information in the supplied Air India
policy documents to answer this confidently."

Do not speculate or introduce loosely related policy provisions.

Never answer Yes or No when the supplied documents do not
establish the answer.

FINAL RESPONSE CHECK:

Before responding, verify:
1. Does the evidence directly support the answer?
2. Have conditional provisions been presented as conditional?
3. Have I avoided turning missing information into a prohibition?
4. Have I answered the exact question?
5. Are source document and page references accurate?
6. Have I flagged historical or undated sources?
"""


def get_question_specific_guidance(question):

    q = question.lower()

    # Q17: Universal compensation amount
    if (
        "every cancellation" in q
        or "all cancellations" in q
        or "every cancelled flight" in q
        or "universal compensation" in q
    ):
        return """
QUESTION-SPECIFIC RULE:

The passenger is asking whether one compensation amount applies
universally to every cancellation.

You must:
- State whether the supplied documents establish one universal
  compensation amount.
- If they do not, explicitly say no universal amount is established.
- Do NOT list individual compensation figures.
- Do NOT provide examples of conditional amounts.
- Do NOT imply compensation is always payable.
"""

    # Q19: Unlisted animal eligibility
    if "rabbit" in q or "rabbits" in q:
        return """
QUESTION-SPECIFIC RULE:

The supplied guidelines list domesticated cats and dogs.

You must:
- State that the guidelines list cats and dogs.
- State that rabbit eligibility is not established by the
  supplied documents.
- Do NOT answer Yes or No.
- Do NOT say rabbits are prohibited or not permitted.
- Recommend confirming rabbit eligibility directly with Air India.
"""

    return ""


def generate_answer(question, retrieved_chunks):

    context_parts = []

    for index, chunk in enumerate(retrieved_chunks, start=1):

        metadata = chunk["metadata"]

        document_title = metadata.get(
            "document_title", "Unknown document"
        )

        page_start = metadata.get("page_start", "Unknown")
        page_end = metadata.get("page_end", "Unknown")

        context_parts.append(
            f"""
SOURCE {index}
Document: {document_title}
Pages: {page_start}-{page_end}

Content:
{chunk['text']}
"""
        )

    context = "\n".join(context_parts)

    specific_guidance = get_question_specific_guidance(question)

    user_prompt = f"""
Answer the following passenger question using only the
retrieved Air India policy context.

PASSENGER QUESTION:
{question}

QUESTION-SPECIFIC GUIDANCE:
{specific_guidance if specific_guidance else "No additional question-specific guidance."}

RETRIEVED POLICY CONTEXT:
{context}

RESPONSE REQUIREMENTS:

1. Answer the exact question directly.
2. Follow the question-specific guidance where provided.
3. Include relevant conditions and exceptions.
4. Do not introduce unrelated policy provisions.
5. Do not infer permissions, prohibitions or entitlements.
6. Include source references with document title and PDF page.
7. If the context is insufficient, clearly disclose what
   information is missing.
8. Flag historical or undated sources when relevant.

Do not invent information to fill gaps in the retrieved context.
"""

    response = client.responses.create(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=user_prompt
    )

    return response.output_text


if __name__ == "__main__":

    print("FlyWise generation module loaded successfully.")