---
name: openai-assist
description: Use the OpenAI API (GPT models) to supplement Claude's response when the user explicitly requests it ("GPT한테도 물어봐", "OpenAI로 확인해봐", "GPT 의견도 듣고 싶어", "use GPT to double-check") or when Claude judges a second opinion from a different model would genuinely improve the answer — for example, cross-validating a complex analysis, getting an alternative perspective on a subjective question, or checking reasoning on a tricky problem. Trigger this skill whenever OpenAI, GPT, ChatGPT, or a "second opinion from another model" is mentioned, even casually.
---

# OpenAI Assist

Query OpenAI's GPT models to supplement Claude's own response. This gives the user a second perspective from a different model family when it would be genuinely useful.

## When to use this

- The user explicitly asks for GPT/OpenAI input
- Claude judges that cross-validating with another model would meaningfully improve the answer (complex analysis, ambiguous questions, subjective evaluations)

## Permission requirement

**Ask the user for permission every single time before making an OpenAI API call.** This is non-negotiable — the call costs money and uses someone else's API quota. Even if the user asked for it in a previous turn, confirm again if you're about to make a new call.

Example confirmation:
> "OpenAI API를 호출해서 GPT의 의견도 함께 보여드릴까요? (API 비용이 발생합니다)"

Only proceed after the user confirms.

## How to call the API

The project has `OPENAI_API_KEY` in `.env` and the `openai` Python package installed. Write and run an inline script from the project root:

```python
import sys, os
sys.path.insert(0, "src")

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
if not api_key:
    print("OPENAI_API_KEY is not set in .env")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url=base_url)

response = client.chat.completions.create(
    model=os.getenv("OPENAI_CANDIDATE_MODEL", "gpt-5.4-mini"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Respond in the same language as the user's question."},
        {"role": "user", "content": """YOUR QUESTION HERE"""},
    ],
    temperature=0.7,
)

print(response.choices[0].message.content)
```

### Model selection guide

| Use case | Model | Env var |
|----------|-------|---------|
| Quick questions, validation | `gpt-5.4-mini` | `OPENAI_CANDIDATE_MODEL` |
| Deep analysis, complex reasoning | `gpt-5.4` | `OPENAI_FINAL_MODEL` |

Default to the lighter model (`OPENAI_CANDIDATE_MODEL`) unless the task clearly needs deeper reasoning.

## Presenting the result

After getting the GPT response, present both perspectives clearly:

```
### Claude's answer
[Your own analysis]

### GPT's perspective
[The OpenAI response]

### Summary
[Where they agree, where they differ, and your synthesis]
```

The goal is to give the user richer information, not to defer to GPT. Claude's own analysis should always come first, and the summary should highlight what's most useful from each.

## If the API call fails

If the key is missing or the call errors out, tell the user what went wrong and continue with Claude's own answer. Don't retry without asking.
