# 🧠 ADK Agent Engine + OAuth - Learnings & Retrospective

This document captures the architectural decisions, API integration gotchas, OAuth credential negotiation patterns, and debugging solutions discovered while building and upgrading the **ADK Agent Engine + OAuth Google Drive & Slides Reader** demo.

---

## 🎯 Executive Summary

Integrating OAuth 2.0 with Google ADK agents for enterprise Workspace data (Google Drive, Docs, Sheets, Slides) requires handling environments with differing credential injection models (Local ADK Web UI vs Production Gemini Enterprise vs API Microservices) while respecting strict Google API scope constraints.

---

## 🚧 Key Technical Challenges & Solutions

### Challenge 1: Google Slides Export Failure (`text/plain` HTTP 400)
- **The Issue**: Calling Google Drive API v3 `files().export(fileId=file_id, mimeType="text/plain")` works for Google Docs (`application/vnd.google-apps.document`), but fails with `HTTP 400 Bad Request: Export format text/plain not supported` when called on Google Slides presentations (`application/vnd.google-apps.presentation`).
- **Solution**: Integrated the **Google Slides API v1** (`build("slides", "v1", credentials=creds)`).
  - Used `slides_service.presentations().get(presentationId=file_id)` to parse slide shapes, text frames, titles, text runs, and bullet points into structured Markdown.
  - Added fallback handling to PDF export if Slides API structure is incomplete.

---

### Challenge 2: OAuth Scope Mismatch (`drive.apps.readonly` vs `drive.readonly`)
- **The Issue**: Users attempting to authenticate with tokens acquired for app configuration (`https://www.googleapis.com/auth/drive.apps.readonly`) were rejected by Google Drive API with `HttpError 403: SCOPE_NOT_PERMITTED`.
- **Solution**:
  - Explicitly declared required scopes: `https://www.googleapis.com/auth/drive.readonly` and `https://www.googleapis.com/auth/presentations.readonly`.
  - Added detailed HttpError JSON parsing in `read_drive_file` to surface clear scope mismatch explanations directly in the user presentation interface.

---

### Challenge 3: Multi-Environment OAuth Credential Negotiation (`negotiate_creds`)
- **The Issue**: Credentials arrive differently across runtimes (Gemini Enterprise injects tokens as `temp:<AUTH_ID>` in `tool_context.state`, local ADK Web UI uses code exchange, and FastAPI microservice uses session tokens).
- **Solution**: Implemented a 4-Stage Resolution Engine:
  - **Stage 1**: Check `tool_context.state` for cached or injected token string/dict (`google-drive-auth` or `temp:google-drive-auth`).
  - **Stage 2**: Check environment variables (`OAUTH_ACCESS_TOKEN` / `GOOGLE_OAUTH_TOKEN` / `DRIVE_OAUTH_TOKEN`).
  - **Stage 3**: Check `tool_context.get_auth_response()` for ADK OAuth flow exchange.
  - **Stage 4**: Return `auth_required` status with Google OAuth 2.0 authorization redirect URL.

---

### Challenge 4: Uvicorn Port Bind Conflicts
- **The Issue**: Hardcoding `port=8080` caused uvicorn boot crashes (`Errno 98 address already in use`) when the Demo Factory main dashboard was running concurrently.
- **Solution**: Implemented dynamic port resolution `int(os.environ.get("DEMO_PORT", os.environ.get("PORT", "8085")))`.

---

## 📋 Engineering Checklist for Workspace OAuth Demos

- [x] **Drive Export Compatibility**: Use `Google Slides API v1` (`slides.v1`) for presentations instead of `drive.v3 export(text/plain)`.
- [x] **Explicit Scopes**: Ensure OAuth tokens include `https://www.googleapis.com/auth/drive.readonly`.
- [x] **Session Persistence**: Maintain lightweight `SessionToolContext` with token state across requests.
- [x] **Dual-Mode Serving**: Provide offline simulation fallbacks in `app/simulation.py` for offline sales presentations.
- [x] **Error Diagnostics**: Extract `e.content` JSON from `HttpError` exceptions to display exact permission details.
- [x] **CI/CD Quality Gate**: Maintain 100% test pass rate in `make test` and rubric score $\ge 85\%$ in `make eval`.
