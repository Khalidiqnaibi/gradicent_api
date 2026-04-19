# Insecure Direct Object Reference (IDOR) in `/api/gaia/compute`

> **Allows unauthorized access to user activity logs**

| Field | Details |
|---|---|
| **Researchers** | Ameer Salhab, Lieth Ghanim |
| **Severity** |  High |
| **Vulnerability Type** | Insecure Direct Object Reference (IDOR) |
| **Affected Endpoint** | `GET /api/gaia/compute` |

---

## 1. Title

**Insecure Direct Object Reference (IDOR) in `/api/gaia/compute` allows unauthorized access to user activity logs.**

---

## 2. Summary

The endpoint `/api/gaia/compute` accepts a `user_id` parameter and returns sensitive activity logs **without verifying ownership of the requested resource**.

An authenticated attacker can trivially modify the `user_id` value to retrieve **other users' internal activity logs**, resulting in unauthorized data exposure. No authorization check is enforced server-side to confirm the requesting user is entitled to view the requested resource.

---

## 3. Affected Endpoint

```
GET /api/gaia/compute
```

The vulnerable parameter in this request is **`user_id`**. The server accepts any user-supplied value for this parameter and returns the corresponding user's data without verifying that the caller owns or has permission to access that resource.

---

## 4. Proof of Concept (PoC)

### Step 1 — Legitimate Request

A normal authenticated request is made with the caller's own `user_id`:

```http
GET /api/gaia/compute?user_id=<YOUR_USER_ID>
Authorization: Bearer <valid_token>
```

**Expected Response:** `200 OK`

The response includes the authenticated user's own data:

- User activity logs (logins, searches, analytics, client actions)
- ROI metrics
- Behavioral timestamps

---

### Step 2 — Exploit: Parameter Tampering

By simply substituting a different user's ID into the same request:

```http
GET /api/gaia/compute?user_id=<VICTIM_USER_ID>
Authorization: Bearer <valid_token>
```

**Actual Response:** `200 OK`

The server returns the **victim user's** logs without any authorization check. There is no ownership validation — the only requirement is a valid authentication token, not access to the specific resource.

> **Example response (abridged):**
> ```json
> {
>   "user_id": "<VICTIM_USER_ID>",
>   "activity_logs": [...],
>   "roi_metrics": {...},
>   "timestamps": [...]
> }
> ```

---

## 5. Impact

This vulnerability exposes the following sensitive data belonging to any user on the platform:

| Exposed Data | Description |
|---|---|
| **Activity Logs** | Login history, search queries, analytics usage |
| **Business Actions** | Client creation events, internal workflow actions |
| **ROI Metrics** | Financial and performance indicators |
| **Behavioral Timestamps** | Precise timestamps of all user interactions |

### Real-World Attack Scenarios

- **User Profiling** — Attackers can build detailed behavioral profiles of target users by enumerating activity patterns over time.
- **Phishing & Social Engineering** — Knowledge of login times, active sessions, and business activity allows attackers to craft highly targeted and convincing attacks.
- **Competitive Intelligence** — Business actions and ROI metrics can be exfiltrated by malicious actors (including competitors) to gain an unfair advantage.
- **Privilege Escalation Reconnaissance** — Internal workflow visibility can help attackers identify high-value accounts to target next.

---

## 6. Severity

**High** — This is a confirmed, exploitable security flaw requiring only a valid authentication token and knowledge of another user's ID (which may itself be enumerable or predictable). It violates fundamental access control principles and directly exposes sensitive user data at scale.

This vulnerability maps to:
- [OWASP A01:2021 – Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [CWE-639: Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)

---

## 7. Recommended Remediation

1. **Server-side ownership check** — Before returning any resource, verify that the authenticated user's identity matches the `user_id` being requested (or that the caller holds an explicit admin/delegation privilege).

   ```python
   # Pseudocode example
   if request.user.id != requested_user_id and not request.user.is_admin:
       return 403 Forbidden
   ```

2. **Avoid direct object references in public APIs** — Consider using indirect references (e.g., tokens or scoped session identifiers) rather than raw internal IDs.

3. **Implement access control tests** — Add automated authorization tests that verify a user from Group A cannot access resources belonging to Group B.

4. **Audit logging** — Log all access to this endpoint with the requesting user's identity so anomalous enumeration can be detected.

---

*Report prepared by Ameer Salhab & Lieth Ghanim*