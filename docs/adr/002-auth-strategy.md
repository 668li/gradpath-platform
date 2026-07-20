# ADR-002: Authentication Strategy

## Status
Accepted

## Date
2026-07-11

## Context
GradPath requires secure authentication supporting:
- Email/password login for primary users
- Optional third-party OAuth (WeChat, GitHub)
- WebSocket connections with token verification
- Admin role-based access control
- Rate limiting per user/IP

## Decision
We implement JWT-based authentication with the following design:

### Token Structure
- **Access Token**: 30-minute expiry, contains user_id and role
- **Refresh Token**: 7-day expiry, stored in database for revocation
- **Algorithm**: HS256 with configurable SECRET_KEY (minimum 32 chars in production)

### Flow
```
POST /api/auth/login
  → Validate credentials
  → Issue access_token + refresh_token
  
GET /api/auth/me
  → Verify access_token via Authorization: Bearer header
  → Return user profile
  
POST /api/auth/refresh
  → Validate refresh_token
  → Issue new access_token
  
WS /ws/{user_id}?token=<access_token>
  → Verify token on connect
  → Confirm user_id matches token subject
```

### Security Measures
- Passwords hashed with bcrypt (via passlib)
- Rate limiting via slowapi (per-IP for unauthenticated, per-user for authenticated)
- Security headers middleware (HSTS, X-Frame-Options, CSP)
- CORS restricted to configured origins

### Role-Based Access
- `user`: Standard platform access
- `admin`: Crawler management, system configuration
- Route-level dependency: `get_admin_user()` checks role

## Consequences

### Positive
- Stateless access tokens enable horizontal scaling
- Refresh token rotation prevents long-lived session abuse
- JWT verification is fast (no database hit for access tokens)
- WebSocket auth via query token avoids complex handshake

### Negative
- JWT cannot be revoked immediately (mitigated by short expiry + refresh rotation)
- SECRET_KEY management critical (rotation requires all instances to share new key)

### Risks
- Token theft via XSS (mitigated by HttpOnly cookies not used for API tokens; frontend must store securely)
- Refresh token database growth (mitigated by cleanup job)
