"""Generate the three I02 n8n templates (repo) and their local test copies (scratchpad).

Templates are provider-neutral: the OpenAI Chat Model node has no credential
attached (n8n asks for one on import) and the model id is a plain value the
user replaces. Test copies attach the local test credential.
"""
import json, os, sys, uuid

REPO = sys.argv[1]
SCRATCH = sys.argv[2]
TEST_CRED = {"openAiApi": {"id": "kunavoCred0001", "name": "Kunavo (OpenAI-compatible)"}}
MODEL_ID = "claude-sonnet-5"
UTM = "https://kunavo.com/docs/integrations/n8n?utm_source=n8n-templates&utm_medium=template&utm_campaign=i06-{slug}"


def nid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "kunavo-i02/" + name))


def node(name, typ, ver, pos, params, **extra):
    n = {"id": nid(name), "name": name, "type": typ, "typeVersion": ver, "position": pos, "parameters": params}
    n.update(extra)
    return n


def sticky(name, pos, content, w=420, h=300, color=None):
    p = {"content": content, "height": h, "width": w}
    if color:
        p["color"] = color
    return node(name, "n8n-nodes-base.stickyNote", 1, pos, p)


def model(name, pos):
    return node(
        name,
        "@n8n/n8n-nodes-langchain.lmChatOpenAi",
        1.3,
        pos,
        {"model": {"__rl": True, "mode": "id", "value": MODEL_ID}, "responsesApiEnabled": False, "options": {}},
    )


def chain(name, pos, text, system):
    return node(
        name,
        "@n8n/n8n-nodes-langchain.chainLlm",
        1.9,
        pos,
        {
            "promptType": "define",
            "text": text,
            "messages": {"messageValues": [{"type": "SystemMessagePromptTemplate", "message": system}]},
        },
    )


def if_node(name, pos, left, op_type, operation, right=None):
    cond = {"id": nid(name + "/c"), "leftValue": left, "operator": {"type": op_type, "operation": operation}}
    if right is None:
        cond["operator"]["singleValue"] = True
        cond["rightValue"] = ""
    else:
        cond["rightValue"] = right
    return node(
        name,
        "n8n-nodes-base.if",
        2.2,
        pos,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [cond],
                "combinator": "and",
            },
            "options": {},
        },
    )


def code(name, pos, js):
    return node(name, "n8n-nodes-base.code", 2, pos, {"jsCode": js})


def noop(name, pos):
    return node(name, "n8n-nodes-base.noOp", 1, pos, {})


def conn(*pairs):
    """pairs: (from, to, kind, out_index)"""
    c = {}
    for p in pairs:
        frm, to = p[0], p[1]
        kind = p[2] if len(p) > 2 else "main"
        out = p[3] if len(p) > 3 else 0
        slots = c.setdefault(frm, {}).setdefault(kind, [])
        while len(slots) <= out:
            slots.append([])
        slots[out].append({"node": to, "type": kind, "index": 0})
    return c


# --------------------------------------------------------------------------
# 1. Extract and validate structured data from form submissions
# --------------------------------------------------------------------------

EXTRACT_SYSTEM = """You extract contact details from text a person pasted into a form.
Return ONLY a JSON object, no prose and no code fences, with exactly these keys:
- "name": the person's full name, or null if not present
- "email": their email address, or null if not present
- "company": their company or organisation, or null if not present
- "intent": one of "buy", "support", "partnership", "other"
- "summary": one sentence (max 200 characters) saying what they want
Never invent an email address or a company that is not in the text."""

VALIDATE_JS = r"""// Parse and check the model's answer. Nothing here trusts the model:
// a field that fails a rule is reported, not repaired.
const INTENTS = ['buy', 'support', 'partnership', 'other'];
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

return $input.all().map((item) => {
  const raw = String(item.json.text ?? '');
  const attempt = ($('Validate').isExecuted && $runIndex > 0) ? 2 : (item.json.attempt ?? 1);
  const errors = [];
  let data = null;
  try {
    // Models sometimes wrap JSON in ``` fences despite the instruction.
    data = JSON.parse(raw.replace(/^\s*```(?:json)?\s*/i, '').replace(/\s*```\s*$/, ''));
  } catch (e) {
    errors.push('The answer is not valid JSON.');
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    errors.push('The answer must be a JSON object.');
  } else {
    for (const k of ['name', 'email', 'company', 'intent', 'summary']) {
      if (!(k in data)) errors.push(`Missing key "${k}".`);
    }
    if (data.email !== null && data.email !== undefined && !EMAIL.test(String(data.email))) {
      errors.push(`"email" is not an email address: ${data.email}`);
    }
    if (!INTENTS.includes(data.intent)) {
      errors.push(`"intent" must be one of ${INTENTS.join(', ')}.`);
    }
    if (typeof data.summary !== 'string' || data.summary.length === 0 || data.summary.length > 200) {
      errors.push('"summary" must be a sentence of at most 200 characters.');
    }
    if (!data.name && !data.email) {
      errors.push('Neither a name nor an email was found.');
    }
  }
  return { json: { valid: errors.length === 0, errors, data, raw, source: $('Form: paste text').first().json.Text } };
});"""

RETRY_SYSTEM = EXTRACT_SYSTEM + """
Your previous answer failed validation. Fix ONLY what the errors name and return the corrected JSON object.
If a value is genuinely not in the text, use null instead of guessing."""

RETRY_TEXT = """=Text:
{{ $json.source }}

Your previous answer:
{{ $json.raw }}

Validation errors:
{{ $json.errors.join('\\n') }}"""

VALIDATE_RETRY_JS = VALIDATE_JS.replace(
    "const attempt = ($('Validate').isExecuted && $runIndex > 0) ? 2 : (item.json.attempt ?? 1);\n", ""
)
VALIDATE_JS = VALIDATE_JS.replace(
    "const attempt = ($('Validate').isExecuted && $runIndex > 0) ? 2 : (item.json.attempt ?? 1);\n", ""
)

RESULT_MESSAGE = """=Name: {{ $json.data.name ?? '—' }}
Email: {{ $json.data.email ?? '—' }}
Company: {{ $json.data.company ?? '—' }}
Intent: {{ $json.data.intent }}
Summary: {{ $json.data.summary }}"""

PERSON_JS = r"""// The person filled in what the model could not. Their answer wins.
const f = $input.first().json;
return [{ json: {
  valid: true,
  reviewedByPerson: true,
  data: {
    name: f['Name'] || null,
    email: f['Email'] || null,
    company: f['Company'] || null,
    intent: (f['Intent'] || 'other').toLowerCase(),
    summary: f['What do you need?'] || '',
  },
} }];"""


def template_extract(test=False):
    slug = "extract-validate"
    trigger_name = "Form: paste text"
    nodes = [
        sticky(
            "About this workflow",
            [-560, -260],
            "## Extract and validate contact details from a form\n\n"
            "Someone pastes an email, a signature or a note. A chat model returns the details as JSON, "
            "a Code node checks every field, and a failed answer gets **one** corrected retry with the "
            "errors spelled out. If it still fails, the form asks the person to fill in the fields "
            "themselves, so nothing is lost and nothing is guessed.\n\n"
            "**Setup (2 minutes)**\n"
            "1. Open *Chat model* and pick or create an **OpenAI** credential.\n"
            "2. Any OpenAI-compatible provider works: set the credential's **Base URL** to your "
            "provider's address. It must end in `/v1`, or the credential test passes and every run fails.\n"
            "3. Set the model id your provider serves. Leave temperature at its default: some models "
            "reject non-default values.\n"
            "4. Activate and open the form URL from the trigger.\n\n"
            "Optional: [using this with Kunavo](" + UTM.format(slug=slug) + ").",
            w=520,
            h=520,
        ),
        sticky(
            "Retry and hand-off",
            [900, 260],
            "### One retry, then a person\nThe retry sends the original text, the previous answer and the exact "
            "validation errors. Two model calls is the most a submission can cost. After that the "
            "submitter sees a short form with the fields to fill in.",
            w=440,
            h=200,
            color=5,
        ),
        node(
            trigger_name,
            "n8n-nodes-base.formTrigger",
            2.3,
            [0, 0],
            {
                "formTitle": "Extract contact details",
                "formDescription": "Paste an email, a signature or a note. We pull out the contact details for you.",
                "formFields": {
                    "values": [
                        {
                            "fieldLabel": "Text",
                            "fieldType": "textarea",
                            "placeholder": "Hi, I'm Dana Ruiz from Northwind. Reach me at dana@northwind.example ...",
                            "requiredField": True,
                        }
                    ]
                },
                "options": {},
            },
            webhookId=nid("form1-webhook"),
        ),
        chain("Extract with LLM", [240, 0], "={{ $json.Text }}", EXTRACT_SYSTEM),
        model("Chat model", [240, 220]),
        code("Validate", [480, 0], VALIDATE_JS.replace("$('Form: paste text').first().json.Text", "$('Form: paste text').first().json.Text")),
        if_node("Valid?", [700, 0], "={{ $json.valid }}", "boolean", "true"),
        chain("Retry with errors", [920, 120], RETRY_TEXT, RETRY_SYSTEM),
        model("Chat model (retry)", [920, 340]),
        code("Validate retry", [1160, 120], VALIDATE_RETRY_JS),
        if_node("Valid after retry?", [1380, 120], "={{ $json.valid }}", "boolean", "true"),
        node(
            "Ask the person",
            "n8n-nodes-base.form",
            2.5,
            [1600, 240],
            {
                "operation": "page",
                "formFields": {
                    "values": [
                        {"fieldLabel": "Name", "fieldType": "text"},
                        {"fieldLabel": "Email", "fieldType": "email"},
                        {"fieldLabel": "Company", "fieldType": "text"},
                        {
                            "fieldLabel": "Intent",
                            "fieldType": "dropdown",
                            "fieldOptions": {"values": [{"option": "Buy"}, {"option": "Support"}, {"option": "Partnership"}, {"option": "Other"}]},
                            "requiredField": True,
                        },
                        {"fieldLabel": "What do you need?", "fieldType": "textarea", "requiredField": True},
                    ]
                },
                "options": {
                    "formTitle": "Please check your details",
                    "formDescription": "We could not read all of your details automatically. Fill in what you can.",
                },
            },
            webhookId=nid("form1-ask-webhook"),
        ),
        code("Use the person's answer", [1820, 240], PERSON_JS),
        node(
            "Show result",
            "n8n-nodes-base.form",
            2.5,
            [2040, 0],
            {
                "operation": "completion",
                "respondWith": "text",
                "completionTitle": "Here is what we extracted",
                "completionMessage": RESULT_MESSAGE,
                "options": {},
            },
            webhookId=nid("form1-done-webhook"),
        ),
    ]
    c = conn(
        (trigger_name, "Extract with LLM"),
        ("Chat model", "Extract with LLM", "ai_languageModel"),
        ("Extract with LLM", "Validate"),
        ("Validate", "Valid?"),
        ("Valid?", "Show result", "main", 0),
        ("Valid?", "Retry with errors", "main", 1),
        ("Chat model (retry)", "Retry with errors", "ai_languageModel"),
        ("Retry with errors", "Validate retry"),
        ("Validate retry", "Valid after retry?"),
        ("Valid after retry?", "Show result", "main", 0),
        ("Valid after retry?", "Ask the person", "main", 1),
        ("Ask the person", "Use the person's answer"),
        ("Use the person's answer", "Show result"),
    )
    return finish("Extract and validate contact details from form submissions with an LLM", "i02Extract00001", nodes, c, test)


# --------------------------------------------------------------------------
# 2. Draft support replies from an FAQ, with human review
# --------------------------------------------------------------------------

FAQ_JS = r"""// Your FAQ. Replace these with your own entries (or load them from a
// sheet / database node placed before this one and map them here).
const FAQ = [
  { id: 'refund', q: 'Can I get a refund?', a: 'Unused prepaid balance can be refunded within 14 days of purchase. Write to support with the order id.' },
  { id: 'invoice', q: 'Where do I find my receipts or invoices?', a: 'Every payment has a receipt on the Billing page. Download it from the payment row.' },
  { id: 'reset-password', q: 'How do I reset my password?', a: 'Use "Forgot password" on the sign-in page. The link is valid for 30 minutes.' },
  { id: 'api-key', q: 'How do I create or rotate an API key?', a: 'Open the Keys page, create a new key, update your app, then delete the old key.' },
  { id: 'limits', q: 'What are the rate limits?', a: 'Each key has a per-minute request limit shown on the Keys page. A 429 response means wait and retry with backoff.' },
  { id: 'delete-account', q: 'How do I delete my account?', a: 'Go to Settings, then Delete account. Remaining balance is forfeited unless refunded first.' },
];

// Simple word-overlap retrieval: good enough for a few dozen entries and
// free to run. Swap in a vector store node when the FAQ grows.
const STOP = new Set(['the','a','an','i','my','to','do','how','can','is','of','for','in','and','or','what','where','me','it','on','get','you','your']);
const words = (s) => String(s).toLowerCase().match(/[a-z0-9]+/g)?.filter((w) => !STOP.has(w) && w.length > 2) ?? [];

// The webhook body: {"email": "...", "question": "..."}
const body = $input.first().json.body ?? {};
const qWords = new Set(words(body.question));
const scored = FAQ.map((e) => ({ ...e, score: words(e.q + ' ' + e.a).filter((w) => qWords.has(w)).length }))
  .filter((e) => e.score > 0)
  .sort((x, y) => y.score - x.score)
  .slice(0, 3);

return [{ json: {
  email: body.email ?? null,
  question: String(body.question ?? ''),
  matches: scored.map(({ id, q, a }) => ({ id, q, a })),
  context: scored.map((e) => `[${e.id}] Q: ${e.q}\nA: ${e.a}`).join('\n\n'),
} }];"""

DRAFT_SYSTEM = """You draft replies for a support team. A person reviews every draft before it is sent.
Answer ONLY from the FAQ entries provided. Keep it under 120 words, friendly and direct.
End with the ids of the entries you used, like: (FAQ: refund, invoice)
If the entries do not answer the question, reply with exactly: NEEDS_HUMAN"""

DRAFT_TEXT = """=Customer question:
{{ $json.question }}

FAQ entries:
{{ $json.context }}"""

FINAL_JS = r"""// The reviewer's edit wins; otherwise the draft goes out unchanged.
const review = $input.first().json;
const draft = $('Draft reply').first().json.text;
const edited = String(review['Edited reply'] ?? '').trim();
return [{ json: {
  to: $('Find FAQ entries').first().json.email,
  reply: edited || draft,
  editedByReviewer: edited.length > 0,
} }];"""


def template_support(test=False):
    slug = "support-faq"
    nodes = [
        sticky(
            "About this workflow",
            [-560, -300],
            "## Draft support replies from your FAQ, with a human review\n\n"
            "Your website form or helpdesk POSTs `{\"email\", \"question\"}` to the webhook, which answers at once. "
            "The workflow finds the closest FAQ entries, "
            "a chat model drafts a reply **only from those entries**, and a reviewer approves, edits or "
            "escalates it before anything is sent. Questions the FAQ does not cover skip the model and go "
            "straight to a person.\n\n"
            "**Setup**\n"
            "1. Point your form or helpdesk at the *Webhook* URL, and replace the FAQ in *Find FAQ entries* with yours.\n"
            "2. *Chat model*: an **OpenAI** credential; for another OpenAI-compatible provider set its "
            "**Base URL** (ending in `/v1`) and the model id it serves.\n"
            "3. Replace *Notify reviewer* with your Slack or email node and send it "
            "`{{ $execution.resumeFormUrl }}`: that link opens the review form. Only the reviewer gets it; "
            "the customer never sees the draft.\n"
            "4. Replace *Send reply* and *Escalate to a person* with your helpdesk or email nodes.\n\n"
            "Optional: [using this with Kunavo](" + UTM.format(slug=slug) + ").",
            w=540,
            h=520,
        ),
        node(
            "Webhook: new question",
            "n8n-nodes-base.webhook",
            2,
            [0, 0],
            {"httpMethod": "POST", "path": "support-question", "responseMode": "onReceived", "options": {}},
            webhookId=nid("webhook2"),
        ),
        code("Find FAQ entries", [220, 0], FAQ_JS),
        if_node("Any FAQ match?", [440, 0], "={{ $json.matches.length }}", "number", "gt", 0),
        chain("Draft reply", [660, -100], DRAFT_TEXT, DRAFT_SYSTEM),
        model("Chat model", [660, 120]),
        # notStartsWith, not notEquals: B02 (q30) saw a model write NEEDS_HUMAN and then
        # an explanation, which an equality check passes on as a usable draft.
        if_node("Draft usable?", [880, -100], "={{ $json.text.trim() }}", "string", "notStartsWith", "NEEDS_HUMAN"),
        noop("Notify reviewer", [1100, -200]),
        node(
            "Review draft",
            "n8n-nodes-base.wait",
            1.1,
            [1320, -200],
            {
                "resume": "form",
                "formTitle": "Review the reply",
                "formDescription": "=Customer: {{ $('Find FAQ entries').first().json.email }}\n\nQuestion: {{ $('Find FAQ entries').first().json.question }}\n\nDraft:\n{{ $('Draft reply').first().json.text }}",
                "formFields": {
                    "values": [
                        {
                            "fieldLabel": "Decision",
                            "fieldType": "dropdown",
                            "fieldOptions": {"values": [{"option": "Send"}, {"option": "Escalate"}]},
                            "requiredField": True,
                        },
                        {"fieldLabel": "Edited reply", "fieldType": "textarea", "placeholder": "Leave empty to send the draft as it is"},
                    ]
                },
                "options": {},
            },
            webhookId=nid("form2-review-webhook"),
        ),
        if_node("Send it?", [1540, -200], "={{ $json.Decision }}", "string", "equals", "Send"),
        code("Final reply", [1760, -280], FINAL_JS),
        noop("Send reply", [1980, -280]),
        noop("Escalate to a person", [1980, 120]),
    ]
    c = conn(
        ("Webhook: new question", "Find FAQ entries"),
        ("Find FAQ entries", "Any FAQ match?"),
        ("Any FAQ match?", "Draft reply", "main", 0),
        ("Any FAQ match?", "Escalate to a person", "main", 1),
        ("Chat model", "Draft reply", "ai_languageModel"),
        ("Draft reply", "Draft usable?"),
        ("Draft usable?", "Notify reviewer", "main", 0),
        ("Draft usable?", "Escalate to a person", "main", 1),
        ("Notify reviewer", "Review draft"),
        ("Review draft", "Send it?"),
        ("Send it?", "Final reply", "main", 0),
        ("Send it?", "Escalate to a person", "main", 1),
        ("Final reply", "Send reply"),
    )
    return finish("Draft support replies from your FAQ with an LLM and human review", "i02Support00001", nodes, c, test)


# --------------------------------------------------------------------------
# 3. RSS items to reviewed drafts
# --------------------------------------------------------------------------

POST_SYSTEM = """You write short posts for a team's internal newsletter from articles in an RSS feed.
For the article given, write 60-100 words: what it is about and why it may matter to the reader.
Plain language, no hype, no emojis, no hashtags. Do not claim anything the title and summary do not say.
End with the link on its own line."""

POST_TEXT = """=Title: {{ $json.title }}
Link: {{ $json.link }}
Summary: {{ ($json.contentSnippet || $json.content || '').slice(0, 1500) }}"""

SAVE_JS = r"""// What gets saved: the reviewer's edit if there is one, the draft otherwise.
const review = $input.first().json;
const item = $('Loop over items').first().json;
const draft = $('Draft post').first().json.text;
const edited = String(review['Edited text'] ?? '').trim();
return [{ json: { title: item.title, link: item.link, text: edited || draft, editedByReviewer: edited.length > 0 } }];"""


def template_rss(test=False):
    slug = "rss-drafts"
    first = "Run manually (test)" if test else "Every morning"
    nodes = [
        sticky(
            "About this workflow",
            [-600, -320],
            "## Turn RSS items into reviewed drafts\n\n"
            "Every morning the workflow reads a feed, keeps only items it has not seen before (at most 3 a "
            "day), and drafts a short post for each. Each draft waits for a person to approve, edit or skip "
            "it, one at a time, before it is saved.\n\n"
            "**Setup**\n"
            "1. *Read feed*: your RSS or Atom URL.\n"
            "2. *Chat model*: an **OpenAI** credential; for another OpenAI-compatible provider set its "
            "**Base URL** (ending in `/v1`) and the model id it serves.\n"
            "3. Replace *Notify reviewer* with Slack or email and send `{{ $execution.resumeFormUrl }}`.\n"
            "4. Replace *Save draft* with your CMS, Notion or Google Docs node.\n\n"
            "The first run treats every current item as new; *Only new items* remembers links from then on. "
            "More than 3 new items in a day: the extra ones are skipped, not queued (feeds list newest first, "
            "so the newest 3 are kept). Raise *At most 3 a day* for a busy feed.\n\n"
            "Optional: [using this with Kunavo](" + UTM.format(slug=slug) + ").",
            w=540,
            h=500,
        ),
        (
            node(first, "n8n-nodes-base.manualTrigger", 1, [0, 0], {})
            if test
            else node(
                first,
                "n8n-nodes-base.scheduleTrigger",
                1.2,
                [0, 0],
                {"rule": {"interval": [{"field": "days", "triggerAtHour": 8}]}},
            )
        ),
        node("Read feed", "n8n-nodes-base.rssFeedRead", 1.2, [220, 0], {"url": "https://blog.n8n.io/rss/", "options": {}}),
        node(
            "Only new items",
            "n8n-nodes-base.removeDuplicates",
            2,
            [440, 0],
            {"operation": "removeItemsSeenInPreviousExecutions", "dedupeValue": "={{ $json.link }}", "options": {}},
        ),
        node("At most 3 a day", "n8n-nodes-base.limit", 1, [660, 0], {"maxItems": 3}),
        node("Loop over items", "n8n-nodes-base.splitInBatches", 3, [880, 0], {"options": {}}),
        chain("Draft post", [1100, 100], POST_TEXT, POST_SYSTEM),
        model("Chat model", [1100, 320]),
        noop("Notify reviewer", [1320, 100]),
        node(
            "Approve draft",
            "n8n-nodes-base.wait",
            1.1,
            [1540, 100],
            {
                "resume": "form",
                "formTitle": "Approve this draft",
                "formDescription": "={{ $('Loop over items').first().json.title }}\n\n{{ $('Draft post').first().json.text }}",
                "formFields": {
                    "values": [
                        {
                            "fieldLabel": "Decision",
                            "fieldType": "dropdown",
                            "fieldOptions": {"values": [{"option": "Approve"}, {"option": "Skip"}]},
                            "requiredField": True,
                        },
                        {"fieldLabel": "Edited text", "fieldType": "textarea", "placeholder": "Leave empty to keep the draft"},
                    ]
                },
                "options": {},
            },
            webhookId=nid("form3-approve-webhook"),
        ),
        if_node("Approved?", [1760, 100], "={{ $json.Decision }}", "string", "equals", "Approve"),
        code("Prepare draft", [1980, 0], SAVE_JS),
        noop("Save draft", [2200, 0]),
        noop("Skipped", [1980, 220]),
    ]
    c = conn(
        (first, "Read feed"),
        ("Read feed", "Only new items"),
        ("Only new items", "At most 3 a day"),
        ("At most 3 a day", "Loop over items"),
        ("Loop over items", "Draft post", "main", 1),
        ("Chat model", "Draft post", "ai_languageModel"),
        ("Draft post", "Notify reviewer"),
        ("Notify reviewer", "Approve draft"),
        ("Approve draft", "Approved?"),
        ("Approved?", "Prepare draft", "main", 0),
        ("Approved?", "Skipped", "main", 1),
        ("Prepare draft", "Save draft"),
        ("Save draft", "Loop over items"),
        ("Skipped", "Loop over items"),
    )
    return finish("Turn RSS items into reviewed drafts with an LLM and an approval step", "i02Rss000000001", nodes, c, test)


TEST_NOTIFY_JS = "// TEST COPY ONLY: expose the review link so the test can open it.\nreturn $input.all().map((i) => ({ json: { ...i.json, reviewUrl: $execution.resumeFormUrl } }));"


def finish(name, wid, nodes, connections, test):
    for n in nodes:
        if test and n["name"] == "Notify reviewer":
            n["type"] = "n8n-nodes-base.code"
            n["typeVersion"] = 2
            n["parameters"] = {"jsCode": TEST_NOTIFY_JS}
    for n in nodes:
        if n["type"] == "@n8n/n8n-nodes-langchain.lmChatOpenAi" and test:
            n["credentials"] = TEST_CRED
    wf = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
        "meta": {"templateCredsSetupCompleted": False},
        "pinData": {},
    }
    if test:
        wf["id"] = wid
        wf["name"] = "[test] " + name
        wf["active"] = False
    return wf


os.makedirs(REPO, exist_ok=True)
for fn, builder in [
    ("01-extract-and-validate.json", template_extract),
    ("02-support-replies-from-faq.json", template_support),
    ("03-rss-to-reviewed-drafts.json", template_rss),
]:
    with open(os.path.join(REPO, fn), "w") as f:
        json.dump(builder(False), f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(SCRATCH, "test-" + fn), "w") as f:
        json.dump(builder(True), f, indent=2, ensure_ascii=False)
print("written")
