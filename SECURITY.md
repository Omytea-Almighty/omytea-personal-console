# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.3.x | ✅ Yes — current |
| 0.2.x | ⚠️ Best-effort only |
| < 0.2 | ❌ No |

## Reporting a vulnerability

If you find a security issue:

1. **Do NOT open a public GitHub issue.** Public issues are crawled by attackers.
2. **Email** [lewxam0102+omytea-security@gmail.com](mailto:lewxam0102+omytea-security@gmail.com) with:
   - A clear description of the issue
   - Steps to reproduce (commands, click sequence, etc.)
   - Your assessment of severity and any known impact
   - Your preferred name for credit (or "anonymous" if you prefer)
3. **Wait for acknowledgement** — we aim to respond within 72 hours.
4. **Coordinated disclosure**: please give us a reasonable window to ship a fix before public disclosure. We will work with you on a timeline that balances user safety with operational reality.

## Threat model

The Personal Future Console runs **locally** by default:

- The Streamlit server binds to `127.0.0.1` only (loopback). It does not accept connections from your local network.
- LLM inference happens via local Ollama unless you explicitly configure a cloud backend.
- The SQLite database (`~/.omytea-personal-console/predictions.db`) is on your filesystem.
- The Console does not transmit data to any third party.

In this default posture, the threat model is dominated by:

- Other processes on the same machine that could read the SQLite DB or memory
- Vision-LLM hallucinations (a content-safety concern, not a vulnerability per se)
- Vulnerabilities in upstream dependencies (Streamlit, Ollama, OpenCV, etc.)

We treat the following as in-scope vulnerabilities for this project:

- Code execution from a maliciously crafted video file (e.g., OpenCV decoder issues)
- SQL injection in `storage.py` (we use parameterized queries; please report any path that isn't parameterized)
- Path traversal from user-controlled filenames
- Streamlit server binding to a non-loopback interface unintentionally (please file even if you can't exploit it)
- The PyInstaller bundle exposing capabilities beyond what the source app would (escalation surface)
- Privacy regressions (data leaving the device without user consent)

We treat the following as **out of scope** unless you have a concrete proof-of-concept:

- DoS via large video upload (the file-size cap exists but is intentionally generous)
- Spoofing the local 127.0.0.1 binding on a multi-user system (this is an OS-level concern)
- Vulnerabilities in upstream dependencies that we can't easily fix without an upstream release

## What you'll get back

- An acknowledgement of the report
- An assessment of severity (Critical / High / Medium / Low)
- A timeline target for the fix
- Credit in the release notes when the fix ships (unless you prefer anonymity)

## What we **won't** do

- We do not offer a bug bounty (this is a personal-scale project).
- We will not threaten legal action for good-faith research.
- We will not publish your contact information without your consent.

Thanks for helping keep the Console safe.
