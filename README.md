# screenshot-to-ticket

`shot-ticket` drafts a structured bug ticket from a single screenshot. It prints markdown or JSON. It does not file the ticket anywhere.

The default model path is a vision model on a local [Ollama](https://ollama.com) server. No API key is required for that path. An OpenAI-compatible vision endpoint is opt-in, and the screenshot is sent to whatever host you configure.

## In the owner's words

I wanted a private scratchpad that turns a screenshot into a ticket draft I can edit before anything gets filed.

## What it does

You point the CLI at a PNG, JPEG, or WebP screenshot of a failure. The tool checks the file, sends it to a vision model with a fixed prompt, and turns the model's JSON into a ticket draft:

- title
- steps to reproduce
- expected result
- actual result
- a severity guess
- environment notes
- the on-screen text the model claims it could read
- fields that still need confirmation

Markdown headings are rendered locally, so the file shape does not depend on the model inventing a template.

## Why local-first

Screenshots pick up customer data, session tokens, internal URLs, and unreleased UI. The default path sends the image only to Ollama on your machine (`http://127.0.0.1:11434`). The tool never posts to Jira, GitHub Issues, or any other tracker. You get a draft on stdout or in a file you choose.

If you set the OpenAI-compatible provider, that choice sends the image to the host in `SHOT_TICKET_BASE_URL`. That is off unless you turn it on.

## Install

From a clone of this repository (the sample images live here, not in a wheel):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`pip install -e .` is enough to run the CLI. The `[dev]` extra adds pytest.

The installable project name is `screenshot-to-ticket`. The console script is `shot-ticket`. `python -m shot_ticket` runs the same CLI.

## Pull a vision model

Ollama must be running. The desktop app usually starts the server for you. Otherwise:

```bash
ollama serve
```

The default model is `llava`, a commonly published vision model:

```bash
ollama pull llava
```

`llama3.2-vision` is a reasonable upgrade when you have the disk and memory. Pass it explicitly:

```bash
ollama pull llama3.2-vision
shot-ticket draft --model llama3.2-vision --image samples/login-error.png
```

Smaller vision models follow the JSON schema less reliably. If a live run fails because the reply is not a ticket object, switch models. The CLI does not silently retry with a second model.

## Quickstart

Dry-run checks the image and prints metadata. It does not call a model, so it works before Ollama is installed:

```bash
shot-ticket draft --image samples/login-error.png --dry-run
shot-ticket draft --image samples/checkout-total.png --dry-run --format json
```

A live draft (requires `ollama serve` and `ollama pull llava`):

```bash
shot-ticket draft --image samples/login-error.png --out ticket.md
shot-ticket draft --image samples/checkout-total.png --format json --out ticket.json
```

Without `--out`, the draft is written to stdout and nothing is written to disk.

The two files in `samples/` are synthetic FixtureApp screens drawn by `scripts/make_samples.py`. They are portfolio fixtures: a made-up product, no third-party branding, and no personal data. `login-error.png` is a sign-in form with a visible failure banner and no error code. `checkout-total.png` is a cart whose total did not calculate.

## CLI

```text
shot-ticket draft --image PATH [--out PATH] [--format markdown|json] [--dry-run]
                  [--model NAME] [--provider ollama|openai] [--base-url URL]
```

| Flag | Meaning |
| --- | --- |
| `--image` | PNG, JPEG, or WebP screenshot. Required. |
| `--out` | Write the draft to this file. The parent directory must already exist. |
| `--format` | `markdown` (default) or `json`. |
| `--dry-run` | Validate the image and print metadata. Do not call a model. |
| `--model` | Overrides `SHOT_TICKET_MODEL`. |
| `--provider` | `ollama` (default) or `openai` for an OpenAI-compatible chat endpoint. |
| `--base-url` | Overrides `SHOT_TICKET_BASE_URL`. |

Exit codes: `0` success, `2` usage or a bad image, `1` configuration, network, or model output that is not a ticket.

There is no API-key flag. Pass the key through the environment so it does not show up in the command line.

## Environment variables

Command-line flags win over these variables.

| Variable | Default | Role |
| --- | --- | --- |
| `SHOT_TICKET_PROVIDER` | `ollama` | `ollama` or `openai`. |
| `SHOT_TICKET_MODEL` | `llava` on Ollama | Model name. Required when the provider is `openai`. |
| `SHOT_TICKET_BASE_URL` | `http://127.0.0.1:11434` for Ollama, `https://api.openai.com/v1` for `openai` | Server origin. Ollama's value is the server root, with no `/api` suffix. An OpenAI-compatible value includes `/v1`. |
| `SHOT_TICKET_API_KEY` | unset | Bearer token, sent only to the OpenAI-compatible provider. Ollama does not receive it. Local servers that do not check a key can leave this unset. |
| `SHOT_TICKET_TIMEOUT` | `180` | HTTP timeout in seconds. |
| `SHOT_TICKET_JSON_MODE` | `true` | Ask the server for a JSON object (`format: json` on Ollama, `response_format` on OpenAI-compatible APIs). Set `false` if a server rejects that field. |

Ollama, the path you get with no configuration:

```bash
shot-ticket draft --image samples/login-error.png
```

A local OpenAI-compatible server (LM Studio, vLLM, llama.cpp, or similar) that speaks `POST /v1/chat/completions` and accepts an image URL:

```bash
export SHOT_TICKET_PROVIDER=openai
export SHOT_TICKET_BASE_URL=http://127.0.0.1:8080/v1
export SHOT_TICKET_MODEL=your-vision-model
shot-ticket draft --image samples/login-error.png
```

Hosted OpenAI, which sends the screenshot off the machine:

```bash
export SHOT_TICKET_PROVIDER=openai
export SHOT_TICKET_MODEL=gpt-4o
export SHOT_TICKET_API_KEY=sk-...
shot-ticket draft --image samples/login-error.png
```

The hosted base URL defaults to `https://api.openai.com/v1`. Do not set that provider for screenshots you are not willing to upload.

## Supported images

| Type | Extensions |
| --- | --- |
| PNG | `.png` |
| JPEG | `.jpg`, `.jpeg` |
| WebP | `.webp` |

The extension and the file contents must agree. A GIF renamed to `.png` is rejected. Files larger than 15 MB are rejected. The CLI does not read PDF, video, GIF, or multi-image sequences.

## What the model is allowed to say

The system prompt forbids inventing UI text, error codes, or stack traces that are not visible and legible in the image. If a detail is blurry, cropped, or absent, the model is told to mark it `unknown` and say it needs confirmation. Severity is a guess from visible impact, or `unknown` when impact is unclear. The file name is not sent to the model, so a name like `login-error.png` is not treated as evidence.

The draft still needs a human. Vision models miss text and sometimes ignore instructions. The "Visible text" and "Needs confirmation" sections are there so you can check the screenshot before you trust a line. The tool does not claim it reproduced the bug.

## Output

Markdown is the default. This is the local renderer applied to a hand-built draft, so you can see the shape. It is not a live model response:

```markdown
# Sign-in failed on FixtureApp

> Draft only, from `login-error.png`. shot-ticket did not file this anywhere. Severity is a guess. If a line says unknown or needs confirmation, check the screenshot before you trust it.

**Severity (guess):** medium (guess — confirm)
**Screenshot:** login-error.png · PNG · 960×600

## Steps to reproduce

1. Open the FixtureApp sign-in screen.
2. Enter an email and password.
3. Choose Sign in.

## Expected

unknown — needs confirmation

## Actual

A banner reads: Sign-in failed. Check the email and password.

## Environment notes

- unknown — needs confirmation

## Visible text

Only strings the model claims are legible in the image:

- Sign-in failed. Check the email and password.
- Sign in

## Needs confirmation

- expected result
- browser and operating system

---

Draft file only. Review it before copying into an issue tracker.
```

JSON is the same ticket object plus a `screenshot` block added by the tool (file name, format, pixel size). Keys the model adds beyond the schema are dropped. The model is not asked for a stack trace field, and none is invented at render time.

Dry-run JSON is only file metadata (`dry_run`, `model_called`, dimensions, media type). It is not a ticket.

## Out of scope

- PDF and video. Supported inputs are PNG, JPEG, and WebP only.
- Filing the draft. Nothing is posted to Jira, GitHub Issues, Linear, or email. A future hook that uploads a draft is intentionally not part of this tool.
- Multi-screenshot tickets, cropping, or a redaction UI.
- Spawning `ollama serve` for you. The server has to be up before a live draft.

## Tests without Ollama

The suite mocks the vision client. It checks image validation, the ticket schema, the no-fabrication prompt, both HTTP payload shapes, the CLI, and dry-run. It does not start Ollama and does not need a network.

```bash
pytest
```

## Layout

```text
src/shot_ticket/    CLI, prompt, schema, Ollama and OpenAI-compatible clients
samples/            synthetic FixtureApp screenshots
scripts/make_samples.py
tests/              offline pytest suite
```

## License

MIT. See [LICENSE](LICENSE).
