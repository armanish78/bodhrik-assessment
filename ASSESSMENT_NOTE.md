# Assessment Note

This document addresses some of the architectural decisions and production safety concerns for this project.

## Schema and Normalization

The database schema revolves around `User`, `Session`, and `Evaluation`. 

A key decision was how to link a parent to a session. Initially, it might seem simple to match a `child_name` string on the user to a `child_name` on the session. However, string matching is a weak and unreliable way to enforce data ownership. If two different families have a child with the same name, they could accidentally (or maliciously) access each other's sessions.

To fix this, I used a direct `parent_id` foreign key on the `Session` model. This creates a strict relational link to the `User` table, ensuring accurate role-based access control (RBAC). The tradeoff is that `child_name` remains as a simple string column on the session. While we could have fully normalized this into a separate `Student` table, doing so would add unnecessary complexity for a small assessment project. Storing the name directly on the session keeps things simple while still fully satisfying the security and RBAC requirements.

## Adding a Fourth Role

Right now, RBAC is handled manually inside the route functions (for example, checking `if current_user.role == "teacher"`). This works perfectly fine for just three roles.

However, if we introduced a fourth role—like a `principal` who needs read-only access to all sessions—repeating these `if` statements in every endpoint would quickly become messy and hard to maintain. To handle more roles cleanly, we would need to move away from checking roles in the route body. Instead, we could centralize permissions into a mapping (e.g., mapping roles to specific abilities like `read:any_session`) and use a FastAPI dependency to enforce those permissions before the route even runs.

## Production Safety

This project was built as an assessment prototype. Before it could be used in production, several gaps need addressing:

1. **Authentication**: Trusting an `X-User-ID` header is fine for local testing, but a real system needs proper authentication (like securely managed session cookies or tokens) to verify user identity.
2. **Secrets**: Database credentials are currently hardcoded defaults. These need to be injected securely via environment variables and managed properly.
3. **Database Migrations**: Generating tables on startup with SQLAlchemy is unsafe for live data. A migration tool is necessary to safely track and apply schema changes.
4. **Queue Reliability**: The Redis list serves as a great simple queue for this assessment, but a production system would need a proper background worker setup to handle retries and failed jobs without losing data.
5. **Observability**: The application is missing structured logging and error tracking, which are essential for monitoring a live backend.
