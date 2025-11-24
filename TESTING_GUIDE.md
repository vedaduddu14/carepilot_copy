# Testing Guide - Two-Round Study Design

## 🚀 How to Launch and Test

### 1. Start MongoDB (if not already running)
```bash
brew services start mongodb/brew/mongodb-community@8.0
```

### 2. Start Flask App
```bash
source venv/bin/activate
python app.py
```

The app will run on: http://localhost:8080

### 3. Access the Study
Navigate to: http://localhost:8080/launch/?pwd=491062

## 📋 Complete Flow Structure

```
1. Landing Page (/)
   ↓
2. Launch Page (/launch/?pwd=491062)
   - Select scenario (Hotel or Airlines)
   - **TESTING**: Select treatment group
   ↓
3. Pre-Task Survey (Q1) - /pre-task-survey/<session_id>/
   - Baseline measures
   - Dummy emotion regulation questions (TODO)
   ↓
4. ROUND 1 - WITHOUT AI
   - Chat with Client #1 (info=0, emo=0 - FORCED)
   - NO AI panels visible
   - Conversation ends with "FINISH:999"
   ↓
5. Q2 Round Survey - /round-survey/<session_id>/
   - 3 dummy questions
   - Button: "Continue to Round 2"
   ↓
6. ROUND 2 - WITH TREATMENT
   - Chat with Client #2
   - AI support based on selected treatment:
     * Control: info=0, emo=0 (no AI)
     * Information: info=1, emo=0 (left panel)
     * Emotion: info=0, emo=1 (right panel)
     * Both: info=1, emo=1 (both panels)
   ↓
7. Q2 Round Survey - /round-survey/<session_id>/
   - Same 3 dummy questions
   - Button: "Continue to Final Questions"
   ↓
8. Q3 Final Survey - /final-survey/<session_id>/
   - Questions for ALL participants
   - Conditional questions based on treatment:
     * AI groups: usefulness, trust, future use
     * Control group: hypothetical helpfulness
   ↓
9. Complete Page - /complete/?session_id=<session_id>
   - Exit survey link
```

## 🧪 Testing All 4 Treatment Paths

### Test 1: Control Group (No AI)
1. Go to launch page
2. Select **Control (No AI)**
3. Choose Hotel or Airlines
4. Complete flow
5. **Verify**: No AI panels in both Round 1 and Round 2

### Test 2: Information Support Only
1. Go to launch page
2. Select **Information Support Only**
3. Choose scenario
4. Complete flow
5. **Verify**:
   - Round 1: No AI panels
   - Round 2: LEFT panel visible (response suggestions + troubleshooting)

### Test 3: Emotional Support Only
1. Go to launch page
2. Select **Emotional Support Only**
3. Choose scenario
4. Complete flow
5. **Verify**:
   - Round 1: No AI panels
   - Round 2: RIGHT panel visible (sentiment + emotion reframing)

### Test 4: Both Supports
1. Go to launch page
2. Select **Both Supports**
3. Choose scenario
4. Complete flow
5. **Verify**:
   - Round 1: No AI panels
   - Round 2: BOTH panels visible

## 📊 Data Collection

All data is stored in MongoDB database `flask_db`:

### Collections:
- **participants**: Session metadata, treatment assignment, completion status
- **chat_pre_task**: Q1 pre-task survey responses
- **round_surveys**: Q2 end-of-round survey responses (2 per participant)
- **final_surveys**: Q3 final survey responses
- **chat_history**: All messages between rep and client
- **chat_client_info**: Client parameters for each conversation
- **chat_in_task**: AI support content and ratings
- **chat_post_task**: LEGACY (not used in new flow)

### View Data in MongoDB:
```bash
mongosh
use flask_db
db.participants.find().pretty()
db.round_surveys.find().pretty()
db.final_surveys.find().pretty()
```

## ⚠️ Known Limitations / TODO

1. **Q1 Pre-Task Survey**: Missing emotion regulation style questions (currently has dummy placeholder)
2. **Q2 Questions**: Dummy questions - need to be replaced with actual measures
3. **Q3 Questions**: Dummy questions - need to be replaced with actual measures
4. **Randomization**: Currently manual selection - needs automatic random assignment
5. **AI Credentials**: Azure OpenAI not configured - **MOCK RESPONSES ENABLED for testing flow**

## 🔧 What We Built Today

✅ 2-client queue (1 per round)
✅ Round tracking in sessions
✅ Q2 end-of-round questionnaire
✅ Q3 final questionnaire with conditional questions
✅ Flow logic: Chat → Q2 → Next Round
✅ Force Round 1 to have NO AI
✅ Apply treatment in Round 2 based on assignment
✅ Manual treatment selector for testing
✅ MongoDB data collection enabled
✅ **Mock AI responses for testing without Azure credentials**

## 🤖 Mock AI Mode (Testing Without Azure)

The application now includes **mock AI responses** that allow you to test the complete flow without Azure OpenAI credentials:

### What Gets Mocked:
- **Client initial complaint**: Domain-specific angry complaints (hotel/airlines)
- **Client ongoing responses**: Realistic frustrated responses that progress toward resolution
- **Emotional support (right panel)**: Generic empathy and reframing suggestions
- **Information support (left panel)**: Generic troubleshooting steps based on domain
- **Sentiment analysis**: Still uses local VADER model (no mocking needed)

### How It Works:
- When Azure OpenAI agents are unavailable, the app automatically falls back to mock responses
- Mock responses are logged to console with `⚠️` warnings
- Conversations automatically end after 3-5 turns with "FINISH:999"
- All data still gets saved to MongoDB normally

### Testing the Flow:
You can now test the entire flow structure without valid Azure credentials:
1. Q1 Pre-task survey ✅
2. Round 1 conversation (no AI panels) ✅
3. Q2 Round survey ✅
4. Round 2 conversation (with treatment AI panels) ✅
5. Q2 Round survey ✅
6. Q3 Final survey ✅
7. Complete page ✅

## 🎯 Next Steps

1. Add real emotion regulation questions to Q1
2. Replace dummy questions in Q2 and Q3
3. Implement automatic randomization (remove manual selector)
4. Configure Azure OpenAI credentials for actual AI responses
5. Test with actual AI agents running
6. Deploy for pilot testing
