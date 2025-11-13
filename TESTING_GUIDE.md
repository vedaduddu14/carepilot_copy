# Testing Guide - Pro-Pilot

## Quick Access URLs for Testing

### Option 1: Direct Test Route (⚡ FASTEST - Skips Survey)
```
http://127.0.0.1:8080/test/Airline/?pwd=491062
http://127.0.0.1:8080/test/Hotel/?pwd=491062
http://127.0.0.1:8080/test/Mobile/?pwd=491062
```

**What it does:**
- Creates a new session
- Skips the pre-task survey completely
- Takes you directly to the chat interface
- Uses the `studyQueue` configuration from `config.py`

---

### Option 2: Normal Flow (With Survey)
```
http://127.0.0.1:8080/launch/?pwd=491062
```

**What it does:**
- Shows the launch page
- Requires filling out the pre-task survey
- Then proceeds to chat interface
- Used for actual research studies

---

### Option 3: Direct Chat URL (Manual Configuration)
```
http://127.0.0.1:8080/index/<session_id>?name=TestUser&domain=Airline&category=Service%20Quality&grateful=0&ranting=1&expression=1&civil=0&info=1&emo=1
```

**What it does:**
- Goes directly to a chat with specific parameters
- Requires a valid `session_id` (must be created via `/test/` or `/chat/` first)
- Useful for testing specific customer behavior combinations

---

## Available Scenarios

| Scenario | Description |
|----------|-------------|
| `Airline` | Airline service complaints |
| `Hotel` | Hotel service complaints |
| `Mobile` | Mobile device service complaints |

---

## Customer Behavior Parameters

Configure customer personality via URL parameters:

| Parameter | Values | Description |
|-----------|--------|-------------|
| `grateful` | 0 or 1 | 0 = frustrated, 1 = appreciative |
| `ranting` | 0 or 1 | 0 = calm, 1 = venting emotions |
| `expression` | 0 or 1 | 0 = neutral, 1 = expressive |
| `civil` | 0 or 1 | 0 = rude/disrespectful, 1 = polite |
| `info` | 0 or 1 | Show informational support (Response hints, Troubleshooting) |
| `emo` | 0 or 1 | Show emotional support (Reframing, Perspective, Sentiment) |

---

## Example Test Scenarios

### Test 1: Difficult Customer with Full Support
```
http://127.0.0.1:8080/test/Airline/?pwd=491062
```
Default: Frustrated, ranting, expressive customer with varying support settings

### Test 2: Polite Customer (Manual)
After visiting `/test/Airline/?pwd=491062`, modify the URL:
```
?grateful=1&ranting=0&expression=0&civil=1&info=1&emo=1
```

### Test 3: Emotional Support Only
```
?grateful=0&ranting=1&expression=1&civil=0&info=0&emo=1
```

### Test 4: No Support (Baseline)
```
?grateful=0&ranting=1&expression=1&civil=0&info=0&emo=0
```

---

## Password

The test password is defined in `config.py`:
```
ADMIN_PWD = "491062"
```

Always append `?pwd=491062` to access routes.

---

## Client Queue

The default study queue is configured in `config.py` under `studyQueue[]`.

For quick testing with different domains/names, the system uses `randomQueue` which includes:
- Luis H (Airline)
- Jamal K (Hotel)
- Maria N (Airline)
- Elijah P (Hotel)
- Anna Z (Hotel)
- Samantha K (Hotel)

---

## Support Types Displayed

When `info=1` and/or `emo=1`, you'll see these cards in the right sidebar:

### Emotional Support (`emo=1`)
- "You might be thinking" - Negative thoughts representative might have
- "Be Mindful of Your Emotions" - Cognitive reframing
- "Put Yourself in the Client's Shoes" - Customer perspective
- "Client's Sentiment" - Real-time sentiment analysis

### Informational Support (`info=1`)
- "Response Suggestions" - Hints for responding (not full answers)
- "Guidance for Complaint Resolution" - Troubleshooting steps

---

## Pro Tips

1. **Fastest testing**: Use `/test/<scenario>/?pwd=491062`
2. **Test specific behaviors**: Modify URL parameters after loading
3. **Skip clients**: Click the red dog icon (top left)
4. **End conversation**: Click the yellow cat icon (top left)
5. **View queue**: Left sidebar shows upcoming clients

---

## Common URLs (Copy & Paste)

```bash
# Quick airline test
http://127.0.0.1:8080/test/Airline/?pwd=491062

# Quick hotel test
http://127.0.0.1:8080/test/Hotel/?pwd=491062

# Normal flow with survey
http://127.0.0.1:8080/launch/?pwd=491062
```
