from flask import Flask, send_from_directory
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import os, json

from agents import *

from langchain_core.messages import AIMessage, HumanMessage
from langchain.schema import messages_from_dict, messages_to_dict
from sentiment import analyze_sentiment_decision

import config as common

# DISABLED MongoDB - Using JSON file storage only
# try:
#     from pymongo import MongoClient
#     USE_MONGODB = True
# except ImportError:
#     USE_MONGODB = False
USE_MONGODB = False

# Import JSON-based database
from json_db import JSONClient

from dotenv import load_dotenv
from uuid import uuid4
import datetime
from flask_session import Session
load_dotenv("project.env")

DB_NAME = "test"

print(os.getenv("AZURE_OPENAI_ENDPOINT"))

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = 'your_secret_key1'  # Required for session to work
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

### Session storage
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)

### Database - JSON file storage only (MongoDB disabled)
print("📁 Using JSON file storage for data")
client = JSONClient(db_dir='data')
db = client.flask_db

# Collections
chat_post_task = db.chat_post_task
chat_history_collection = db.chat_history
chat_client_info = db.chat_client_info
chat_in_task = db.chat_in_task
chat_pre_task = db.chat_pre_task
summative_writing = db.summative_writing
summative_scoring = db.summative_scoring

# New collection for experimental design
participants = db.participants  # Stores treatment assignment and session info

sender_agent = None
chat_history = [
]

# clientQueue = common.randomQueue.copy()
clientQueue = []

# Wrap agent instantiation to handle missing Azure credentials
try:
    sender_initial = agent_sender_fewshot_twitter_categorized()
    sender_agent = mAgentCustomer()
    # perspective / thoughts

    # reframing
    emo_agent = mAgentER()
    # shoes
    ep_agent = mAgentEP()
    info_agent = mAgentInfo()
    trouble_agent = mAgentTrouble()
    print("✓ All AI agents initialized")
except Exception as e:
    print(f"⚠️  Could not initialize AI agents (will use mock responses): {e}")
    sender_initial = None
    sender_agent = None
    emo_agent = None
    ep_agent = None
    info_agent = None
    trouble_agent = None



@app.route('/')
def hello():
    return render_template('launch.html')

@app.route('/launch/')
def launch():
    # Password authentication removed - direct access
    return render_template('launch.html')

@app.route('/chat/<scenario>/')
def start_chat(scenario):
    # Password authentication removed - direct access

    clientQueue = common.get_study_queue(scenario)
    client = clientQueue.pop(0)  # First client (Round 1)
    session_id = str(uuid4())   ### unique to each user/participant/representative
    current_client = client

    # Initialize session with round tracking
    session[session_id] = {}
    session[session_id]['current_client'] = current_client
    session[session_id]['client_queue'] = clientQueue
    session[session_id]['current_round'] = 1  # Start at Round 1
    session[session_id]['scenario'] = scenario  # Store scenario
    session[session_id]['treatment_group'] = None  # Will be assigned after pre-task survey
    session[session_id]['round1_completed'] = False
    session[session_id]['round2_completed'] = False

    # Store participant info in MongoDB
    participants.insert_one({
        "session_id": session_id,
        "scenario": scenario,
        "treatment_group": None,  # Will be assigned after quota-based randomization
        "start_time": datetime.datetime.now(datetime.timezone.utc),
        "round1_completed": False,
        "round2_completed": False
    })

    clientParam = f"?name={client['name']}&domain={client['domain']}&category={client['category']}&grateful={client['grateful']}&ranting={client['ranting']}&expression={client['expression']}&civil={client['civil']}&info={client['info']}&emo={client['emo']}"

    return redirect(url_for('getPreSurvey', session_id=session_id) + clientParam)

@app.route('/summative/phase1/get-tsv/')
def get_tsv():
    return send_from_directory('', 'phase1_scenarios.tsv')

# End-point for summative survey
@app.route('/summative/phase1/writing/')
def start_writing():
    val_prolific = request.args.get('PROLIFIC_PID')
    session[val_prolific] = 0
    return render_template('summative_survey.html')

@app.route('/store-summative-writing/<prolific_id>/', methods=['POST'])
def store_summative_writing(prolific_id):
    if prolific_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    data['prolific_id'] = prolific_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        # result = summative_writing.insert_one(data)
        # if result.inserted_id:
        #     session[prolific_id] += 1
        #     return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
        if True:
            return jsonify({"message": "Survey data received (no storage)"}), 200
        else:
            return jsonify({"message": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/summative/phase1/complete/<prolific_id>/', methods=['GET'])
def complete_summative_writing(prolific_id):
    completion_count = session[prolific_id]
    if prolific_id not in session or completion_count < 6:
        return jsonify({"message": "Invalid session or session expired"}), 400

    redirect_url = "https://app.prolific.co/submissions/complete?cc=C19F0ZME"
    return jsonify({"url": redirect_url})

@app.route('/summative/phase2/get-tsv/<filetype>/')
def get_tsv2(filetype):
    if filetype == 'scenarios':
        return send_from_directory('', 'phase1_scenarios.tsv')
    elif filetype == 'ai_msgs':
        # Read TSV file and remove newline in the "coworker_empathetic_msg" column


        return send_from_directory('', 'empathetic_msgs_ai_v2.tsv')
    elif filetype == 'human_msgs':
        return send_from_directory('', 'empathetic_msg_human.tsv')
@app.route('/summative/phase2/writing/')
def start_scoring():
    val_prolific = request.args.get('PROLIFIC_PID')
    session[val_prolific] = 0
    return render_template('summative_survey_p2.html')

@app.route('/store-summative-scoring/<prolific_id>/', methods=['POST'])
def store_summative_scoring(prolific_id):
    if prolific_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    data['prolific_id'] = prolific_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        # result = summative_scoring.insert_one(data)
        # if result.inserted_id:
        #     session[prolific_id] += 1
        #     return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
        if True:
            return jsonify({"message": "Survey data received (no storage)"}), 200
        else:
            return jsonify({"message": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/summative/phase2/complete/<prolific_id>/', methods=['GET'])
def complete_summative_scoring(prolific_id):
    completion_count = session[prolific_id]
    if prolific_id not in session or completion_count < 10:
        return jsonify({"message": "Invalid session or session expired"}), 400

    redirect_url = "https://app.prolific.co/submissions/complete?cc=C19F0ZME"
    return jsonify({"url": redirect_url})


# End-point to test the pre-survey HTML
@app.route('/pre-task-survey/<session_id>/')
def getPreSurvey(session_id):
    if session_id not in session:
        return "Invalid session", 401
    return render_template('pre_task_survey.html', session_id=session_id)


@app.route('/store-pre-task-survey/<session_id>/', methods=['POST'])
def storePreSurvey(session_id):
    print(f"DEBUG: Received session_id: {session_id}")
    print(f"DEBUG: Session keys: {list(session.keys())}")
    print(f"DEBUG: session_id in session: {session_id in session}")

    if session_id in session:

        data = request.get_json()
        if not data:
            return jsonify({"message": "No data received"}), 400

        clientParam = "?"+data.get('client_param', '')

        # Convert string values into integers (skip client_param)
        for k in list(data.keys()):
            if k != "client_param":
                try:
                    data[k] = int(data[k])
                except (ValueError, TypeError):
                    # Skip if can't convert to int
                    pass

        # Calculate Suppression Score from emotion regulation questions
        q1 = data.get('emotion_reg_q1', 0)
        q2 = data.get('emotion_reg_q2', 0)
        q3 = data.get('emotion_reg_q3', 0)

        supp_score = (q1 + q2 + q3) / 3.0
        emotion_regulation_type = "Suppressor" if supp_score >= 4.5 else "NonSuppressor"

        # Store calculated values
        data['suppression_score'] = supp_score
        data['emotion_regulation_type'] = emotion_regulation_type

        # Print emotion regulation calculation
        print("\n" + "="*60, flush=True)
        print("RANDOMIZATION - Emotion Regulation Calculation:", flush=True)
        print(f"  Q1: {q1}, Q2: {q2}, Q3: {q3}", flush=True)
        print(f"  Suppression Score: {supp_score:.2f}", flush=True)
        print(f"  Type: {emotion_regulation_type}", flush=True)
        print("="*60, flush=True)

        # Check quota availability and assign treatment
        # Quotas: 4 treatments x 2 types = 8 cells, each needs 30 participants
        treatments = ["control", "information", "emotion", "both"]
        quota_per_cell = 30

        # Get current counts from MongoDB
        print(f"\nChecking Quotas for {emotion_regulation_type}:", flush=True)
        available_treatments = []
        for treatment in treatments:
            count = participants.count_documents({
                "treatment_group": treatment,
                "emotion_regulation_type": emotion_regulation_type,
                "screened_out": {"$ne": True}  # Don't count screened-out participants
            })
            print(f"  {treatment}: {count}/{quota_per_cell} participants", flush=True)
            if count < quota_per_cell:
                available_treatments.append(treatment)

        # If no slots available, screen out
        if len(available_treatments) == 0:
            print(f"\n⚠️  SCREENING OUT: All quotas full for {emotion_regulation_type}", flush=True)
            print("="*60 + "\n", flush=True)
            # Mark participant as screened out
            participants.update_one(
                {"session_id": session_id},
                {"$set": {
                    "screened_out": True,
                    "emotion_regulation_type": emotion_regulation_type,
                    "suppression_score": supp_score,
                    "screen_out_time": datetime.datetime.now(datetime.timezone.utc)
                }}
            )
            # Save pre-task survey data
            data.pop('client_param', None)
            data['session_id'] = session_id
            data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
            chat_pre_task.insert_one(data)

            # Return screening-out URL (Prolific link or custom page)
            screen_out_url = "https://app.prolific.com/submissions/complete?cc=SCREENED_OUT"
            return jsonify({
                "message": "Study quota full for your profile",
                "screened_out": True,
                "next_url": screen_out_url
            }), 200

        # Randomly assign to one of the available treatments
        import random
        assigned_treatment = random.choice(available_treatments)

        print(f"\n✅ TREATMENT ASSIGNED: {assigned_treatment}", flush=True)
        print(f"   Session ID: {session_id}", flush=True)
        print("="*60 + "\n", flush=True)

        # Update session with treatment assignment
        session[session_id]['treatment_group'] = assigned_treatment

        # Update participant record in MongoDB
        participants.update_one(
            {"session_id": session_id},
            {"$set": {
                "treatment_group": assigned_treatment,
                "emotion_regulation_type": emotion_regulation_type,
                "suppression_score": supp_score,
                "assignment_time": datetime.datetime.now(datetime.timezone.utc)
            }}
        )

        # Remove client_param from data to save (it's not survey data)
        data.pop('client_param', None)

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

        try:
            result = chat_pre_task.insert_one(data)
            if result.inserted_id:
                # Return JSON with next URL instead of redirect (for fetch API)
                next_url = url_for('index', session_id=session_id) + clientParam
                return jsonify({
                    "message": "Survey data saved successfully",
                    "id": str(result.inserted_id),
                    "assigned_treatment": assigned_treatment,
                    "emotion_regulation_type": emotion_regulation_type,
                    "next_url": next_url
                }), 200
            else:
                return jsonify({"message": "Failed to save data"}), 500
        except Exception as e:
            print(f"Error saving pre-task survey: {e}")
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/index/<session_id>')
def index(session_id):
    if session_id in session:
        current_client = session[session_id]['current_client']
    else:
        current_client = 'Guest'

    return render_template('index_chat.html', session_id=session_id, current_client=current_client, common_strings=common.SUPPORT_TYPE_STRINGS)


@app.route('/get-reply/<session_id>/', methods=['GET','POST'])
def getReply(session_id):
    if session_id not in session:
        return "Invalid session", 401
    clientQueue = session[session_id]['client_queue']
    if request.method == 'GET':
        val_name = request.args.get('name')
        val_domain = request.args.get('domain')
        val_category = request.args.get('category')
        val_grateful = request.args.get('grateful')
        val_ranting = request.args.get('ranting')
        val_expression = request.args.get('expression')
        val_civil = request.args.get('civil')
        show_info = request.args.get('info')
        show_emo = request.args.get('emo')

        # Apply treatment based on round
        current_round = session[session_id].get('current_round', 1)
        treatment_group = session[session_id].get('treatment_group', 'control')

        if current_round == 1:
            # FORCE Round 1 to have NO AI support
            show_info = '0'
            show_emo = '0'
        elif current_round == 2:
            # Apply treatment for Round 2
            if treatment_group == 'control':
                show_info = '0'
                show_emo = '0'
            elif treatment_group == 'information':
                show_info = '1'
                show_emo = '0'
            elif treatment_group == 'emotion':
                show_info = '0'
                show_emo = '1'
            elif treatment_group == 'both':
                show_info = '1'
                show_emo = '1'
            else:
                # Default to control if no treatment assigned
                show_info = '0'
                show_emo = '0'

        complaint_parameters = {
            "domain": val_domain,
            "category": val_category,
            "is_grateful": 'grateful' if val_grateful==1 else 'NOT grateful',
            "is_ranting": 'ranting' if val_ranting==1 else 'NOT ranting',
            "is_expression": 'expressive' if val_expression==1 else 'NOT expressive'
        }

        # Try to use Azure OpenAI, fall back to mock if connection fails
        try:
            response = sender_initial.invoke(complaint_parameters)
            # Post-process: Extract only the first complaint (stop at "Category:" if model over-generates)
            if "Category:" in response:
                response = response.split("Category:")[0].strip()
            # Also stop at double newlines
            if "\n\n" in response:
                response = response.split("\n\n")[0].strip()
        except Exception as e:
            # Mock initial complaint based on domain and category
            print(f"⚠️  Azure OpenAI failed, using mock client complaint: {str(e)[:100]}")
            mock_complaints = {
                "hotel": {
                    "reservation": "I'm absolutely furious! I made a reservation at your hotel three months ago for my anniversary, and now you're telling me you have no record of it? This is completely unacceptable! I need this sorted out RIGHT NOW!",
                    "Pricing and Charges": "What kind of operation are you running?! I just checked my credit card statement and you charged me TWICE for my room! And there's an extra $300 charge I never authorized! This is ridiculous!",
                    "Service Quality": "I can't believe the terrible service at your hotel! The room was dirty, nobody answered when I called the front desk, and housekeeping never showed up. For the price I'm paying, this is absolutely unacceptable!"
                },
                "airlines": {
                    "reservation": "This is unbelievable! I booked my flight two weeks ago and now you're saying my reservation doesn't exist?! I have a confirmation number and everything! I need to get on a flight TODAY!",
                    "Pricing and Charges": "I am so angry right now! You charged my card three times for the same ticket! My bank account is overdrawn because of your incompetence! I want a full refund immediately!",
                    "Service Quality": "Your airline is the worst! My flight was delayed for 6 hours with no explanation, my luggage is lost, and nobody can help me! I missed my important meeting because of you!"
                }
            }

            # Get appropriate mock complaint or use a default
            domain_complaints = mock_complaints.get(val_domain, mock_complaints["hotel"])
            response = domain_complaints.get(val_category,
                "I am extremely upset with your service! This is completely unacceptable and I demand this be fixed immediately!")

        client_id = str(uuid4())
        current_client = session[session_id]['current_client']
        session[session_id][client_id] = {"current_client": current_client, "domain": val_domain, "category": val_category, "civil": val_civil, "chat_history": []}
        session[session_id][client_id]["chat_history"] = messages_to_dict([AIMessage(content="Client: "+response)])
        

        turn_number = len(session[session_id][client_id]["chat_history"])
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        chat_client_info.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "client_name":val_name,
            "domain": val_domain,
            "category": val_category,
            "grateful": val_grateful,
            "ranting": val_ranting,
            "expression": val_expression,
            "civil": val_civil,
            "emo": show_emo,
            "timestamp": timestamp
        })

        # Inserting first complaint message
        chat_history_collection.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "sender": "client",
            "receiver": "representative",
            "message": response.strip(),
            "timestamp": timestamp
        })


    elif request.method == 'POST':
        prompt = request.json.get("prompt")
        client_id = request.json.get("client_id")
        show_info = request.json.get("show_info")
        show_emo = request.json.get("show_emo")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        # Try to use Azure OpenAI, fall back to mock if connection fails
        try:
            result = sender_agent.invoke({"input": prompt, "chat_history": chat_history, "civil": session[session_id][client_id]["civil"]})
            response = result
            # Post-process: Extract only the first response (stop at "Representative:" if model over-generates)
            if "Representative:" in response:
                response = response.split("Representative:")[0].strip()
            if "Customer:" in response:
                # Take only the first customer response
                response = response.split("Customer:")[0].strip()
            # Also stop at excessive newlines
            if "\n\n" in response:
                response = response.split("\n\n")[0].strip()
        except Exception as e:
            # Simple mock conversation logic
            print(f"⚠️  Azure OpenAI failed, using mock client response: {str(e)[:100]}")
            turn_count = len(chat_history) // 2
            prompt_lower = prompt.lower()

            # Check if rep is trying to end conversation
            if any(word in prompt_lower for word in ['resolve', 'solution', 'help', 'fix', 'refund', 'compensate']):
                if turn_count >= 3:
                    # End conversation after 3+ turns if rep offers solution
                    response = "Fine, I suppose that's acceptable. I'll wait to hear back from you. FINISH:999"
                else:
                    # Still angry if less than 3 turns
                    response = "Well, that's a start, but I'm still very upset about this whole situation! What else are you going to do about it?"
            elif turn_count >= 5:
                # Force end after 5 turns
                response = "Alright, I appreciate you trying to help. I'll give this one more chance. FINISH:999"
            else:
                # Generic frustrated responses
                mock_responses = [
                    "That's not good enough! I need a better solution than that!",
                    "I'm still not satisfied with this answer. What else can you do for me?",
                    "This is taking way too long. Can't you just fix this right now?",
                    "I don't understand why this is so complicated. Just make it right!",
                    "I've been a loyal customer for years and this is how you treat me?"
                ]
                response = mock_responses[turn_count % len(mock_responses)]

        chat_history.extend([HumanMessage(content="Representative: "+prompt), AIMessage(content="Client: "+response)])
        session[session_id][client_id]["chat_history"] = messages_to_dict(chat_history)

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        # Insert representative response
        chat_history_collection.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number - 1,
            "sender": "representative",
            "receiver": "client",
            "message": prompt.strip(),
            "timestamp": timestamp
        })

        # Insert client reply to the response
        chat_history_collection.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "sender": "client",
            "receiver": "representative",
            "message": response.strip(),
            "timestamp": timestamp
        })

    return jsonify({
        "client": client_id,
        "message": response,
        "show_info": show_info,
        "show_emo": show_emo,
        "clientQueue": clientQueue

    })

@app.route('/update-clientQueue/<session_id>/')
def update_client_queue(session_id):
    """Called after conversation ends - redirect to Q2 (round survey)"""
    if session_id not in session:
        return "Invalid session", 401

    # NEW FLOW: Instead of going to next client, go to Q2 (round survey)
    # Q2 will handle moving to the next round
    new_url = url_for('getRoundSurvey', session_id=session_id)

    return jsonify({"url": new_url})

# End-point to test the survey HTML
@app.route('/post-task-survey/<session_id>/')
def getSurvey(session_id):
    """LEGACY: Post-client survey (was shown after each client)"""
    if session_id not in session:
        return "Invalid session", 401
    return render_template('feedback.html', session_id=session_id)

@app.route('/final-survey/<session_id>/')
def getPostTaskSurvey(session_id):
    """Q3: Final post-task survey (shown after both rounds complete)"""
    if session_id not in session:
        return "Invalid session or session expired", 401

    treatment_group = session[session_id].get('treatment_group', 'control')
    return render_template('final_survey.html', session_id=session_id, treatment_group=treatment_group)

@app.route('/store-final-survey/<session_id>/', methods=['POST'])
def storeFinalSurvey(session_id):
    """Store Q3 final survey responses"""
    if session_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    data['session_id'] = session_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    try:
        # Store in new collection for final surveys
        result = db.final_surveys.insert_one(data)

        # Update participant completion status
        participants.update_one(
            {"session_id": session_id},
            {"$set": {
                "study_completed": True,
                "completion_time": datetime.datetime.now(datetime.timezone.utc)
            }}
        )

        # Return success with next URL to complete page
        return jsonify({
            "message": "Final survey saved successfully",
            "next_url": f"/complete/?session_id={session_id}"
        }), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/store-survey/<session_id>/', methods=['POST'])
def storePostSurvey(session_id):
    if session_id in session:
        data = request.get_json()
        reverseLabels = ["support_effective", "support_helpful", "support_beneficial",
                         "support_adequate", "support_sensitive", "support_caring",
                         "support_understanding", "support_supportive"]
        for k in data:  # Convert string values into integers

            if k != "client_id":
                data[k] = int(data[k])

            if k in reverseLabels:
                data[k] = data[k] * (-1)
                
        if not data:
            return jsonify({"message": "No data received"}), 400

        data['session_id'] = session_id
        data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

        try:
            result = chat_post_task.insert_one(data)
            if result.inserted_id:
                return jsonify({"message": "Survey data saved successfully", "id": str(result.inserted_id)}), 200
            else:
                return jsonify({"message": "Failed to save data"}), 500
        except Exception as e:
            return jsonify({"message": str(e)}), 500
    else:
        return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/store-trouble-feedback/<session_id>/',methods=['POST'])
def storeTroubleFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate")) * -1
        support_type = request.json.get ("type")

        turn_number = len(session[session_id][client_id]["chat_history"])//2+1
        timestamp = datetime.datetime.now(datetime.timezone.utc)
    
        query = {
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": support_type
        }
        update = {
            "$set":{
                "user_feedback": rating,
                "timestamp_feedback": timestamp,
            }
        }
        res = chat_in_task.update_one(query, update)
        if res.matched_count == 0:
            return jsonify({"message": "No existing record found to update"}), 404
        return jsonify({"message": "Trouble feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/store-sentiment-feedback/<session_id>/',methods=['POST'])
def storeSentimentFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate")) * -1
        support_type = request.json.get ("type")

        turn_number = len(session[session_id][client_id]["chat_history"])//2+1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        query = {
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": support_type
        }
        update = {
            "$set":{
                "user_feedback": rating,
                "timestamp_feedback": timestamp,
            }
        }
        res = chat_in_task.update_one(query, update)
        if res.matched_count == 0:
            return jsonify({"message": "No existing record found to update"}), 404
        return jsonify({"message": "Sentiment feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/store-emo-feedback/<session_id>/', methods=['POST'])
def storeEmoFeedback(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        rating = int(request.json.get("rate")) * -1    # helpful-unhelpful scale is reversed
        support_type = request.json.get("type")

        turn_number = len(session[session_id][client_id]["chat_history"]) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        query = {
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": support_type
        }
        update = {
            "$set": {
                "user_feedback": rating,
                "timestamp_feedback": timestamp,
            }
        }

        res = chat_in_task.update_one(query, update)
        if res.matched_count == 0:
            return jsonify({"message": "No existing record found to update"}), 404
        return jsonify({"message": "Feedback received"}), 200
    return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/get-emo-support/<session_id>/', methods=['POST'])
def getEmoSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        support_type = request.json.get("type")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        if support_type=="TYPE_EMO_REFRAME":
            # Try to use Azure OpenAI, fall back to mock if connection fails
            try:
                response_cw_emo = emo_agent.invoke({'complaint':reply, "chat_history": chat_history})
                thought = response_cw_emo['thought']
                reframe = response_cw_emo['reframe']
            except Exception as e:
                print(f"⚠️  Azure OpenAI failed, using mock emotional reframing: {str(e)[:100]}")
                thought = "The client seems very frustrated and upset about their situation. They're expressing legitimate concerns and want to be heard."
                reframe = "Try to acknowledge their feelings first: 'I understand how frustrating this must be for you.' Show empathy before moving to solutions."
            # Thought
            chat_in_task.insert_one({
                "session_id": session_id,
                "client_id": client_id,
                "turn_number": turn_number,
                "support_type": "TYPE_EMO_THOUGHT",
                "support_content": thought.strip(),
                "timestamp_arrival":timestamp
            })
            # Reframe
            chat_in_task.insert_one({
                "session_id": session_id,
                "client_id": client_id,
                "turn_number": turn_number,
                "support_type": "TYPE_EMO_REFRAME",
                "support_content": reframe.strip(),
                "timestamp_arrival": timestamp
            })
            return jsonify({
                "message": {
                    'thought':thought,
                    'reframe': reframe
                }
            })
        elif support_type=="TYPE_EMO_SHOES":
            # Try to use Azure OpenAI, fall back to mock if connection fails
            try:
                response_cw_emo = ep_agent.invoke({'complaint':reply, "chat_history": chat_history})
                response = response_cw_emo
            except Exception as e:
                print(f"⚠️  Azure OpenAI failed, using mock empathy perspective: {str(e)[:100]}")
                response = "Imagine being in their position - they've likely had to spend time and energy dealing with this issue, and now they feel let down. Try to validate their experience before offering solutions."
            chat_in_task.insert_one({
                "session_id": session_id,
                "client_id": client_id,
                "turn_number": turn_number,
                "support_type": "Put Yourself in the Client's Shoes",
                "support_content": response.strip(),
                "timestamp_arrival": timestamp
            })
            return jsonify({
                "message": response
            })
        else:
            return jsonify({"error": "Invalid support_type"}), 400

    return jsonify({"error": "Invalid session_id"}), 400

@app.route('/sentiment/<session_id>/', methods=['POST'])
def sentiment(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        turn_number = len(session[session_id][client_id]["chat_history"]) // 2 + 1

        # Perform sentiment analysis
        # sentiment_category = analyze_sentiment_transformer(reply)
        sentiment_category = analyze_sentiment_decision(reply)

        chat_in_task.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": "TYPE_SENTIMENT",
            "support_content": sentiment_category,
            "timestamp_arrival": timestamp
        })

        return jsonify({'message': sentiment_category})
    else:
        return jsonify({"error": "Invalid session_id"}), 400



@app.route('/get-info-support/<session_id>/', methods=['POST'])
def getInfoSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        # support_type = request.json.get("type")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        # Try to use Azure OpenAI, fall back to mock if connection fails
        try:
            response_cw_info = info_agent.invoke({'domain': session[session_id][client_id]["domain"],'message':reply, 'sender':'client', "chat_history": chat_history})
        except Exception as e:
            # Generic helpful suggestions based on domain - MUST BE AN ARRAY
            print(f"⚠️  Azure OpenAI failed, using mock informational support: {str(e)[:100]}")
            domain = session[session_id][client_id]["domain"]
            if domain == "hotel":
                response_cw_info = [
                    "Apologize for the inconvenience",
                    "Offer to check the reservation system immediately",
                    "Suggest alternative solutions (different room, refund, compensation)"
                ]
            elif domain == "airlines":
                response_cw_info = [
                    "Express understanding of the urgency",
                    "Check booking system for the confirmation",
                    "Explore rebooking options on next available flight"
                ]
            else:
                response_cw_info = [
                    "Acknowledge the issue",
                    "Gather necessary details",
                    "Explain steps to resolve"
                ]

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        chat_in_task.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": "TYPE_INFO_CUE",
            "support_content": response_cw_info,
            "timestamp_arrival": timestamp
        })
        return jsonify({
            "message": response_cw_info
        })
    return jsonify({"message": "Invalid session or session expired"}), 400


@app.route('/get-trouble-support/<session_id>/', methods=['POST'])
def getTroubleSupport(session_id):
    if session_id in session:
        client_id = request.json.get("client_id")
        reply = request.json.get("client_reply")
        # support_type = request.json.get("type")

        retrieve_from_session = json.loads(json.dumps(session[session_id][client_id]["chat_history"]))
        chat_history = messages_from_dict(retrieve_from_session)

        # Try to use Azure OpenAI, fall back to mock if connection fails
        try:
            response_cw_trouble = trouble_agent.invoke({'domain': session[session_id][client_id]["domain"],'message':reply, 'sender':'client', "chat_history": chat_history})
            response = response_cw_trouble
        except Exception as e:
            # Mock troubleshooting guidance
            print(f"⚠️  Azure OpenAI failed, using mock troubleshooting support: {str(e)[:100]}")
            domain = session[session_id][client_id]["domain"]
            if domain == "hotel":
                response = ["Check reservation system for booking confirmation", "Verify payment processing status", "Review room availability for alternative options", "Prepare compensation offer per hotel policy"]
            elif domain == "airlines":
                response = ["Check flight booking system for confirmation number", "Review seat availability on alternative flights", "Check baggage tracking system if applicable", "Prepare rebooking options and compensation per airline policy"]
            else:
                response = ["Verify customer account and transaction history", "Check system logs for any processing errors", "Review company policy for this type of issue", "Prepare resolution options and next steps"]

        turn_number = len(chat_history) // 2 + 1
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        chat_in_task.insert_one({
            "session_id": session_id,
            "client_id": client_id,
            "turn_number": turn_number,
            "support_type": "TYPE_INFO_GUIDE",
            "support_content": response,
            "timestamp_arrival": timestamp
        })

        return jsonify({
            "message": response
        })
    return jsonify({"message": "Invalid session or session expired"}), 400

@app.route('/conversation_history/')
def conversation_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Session ID is missing", 400
    return render_template('conversation_history.html', session_id=session_id)

@app.route('/round-survey/<session_id>/')
def getRoundSurvey(session_id):
    """Display Q2 end-of-round questionnaire"""
    if session_id not in session:
        return "Invalid session or session expired", 400

    round_number = session[session_id]['current_round']
    return render_template('round_survey.html', session_id=session_id, round_number=round_number)

@app.route('/store-round-survey/<session_id>/', methods=['POST'])
def storeRoundSurvey(session_id):
    """Store Q2 end-of-round survey responses"""
    if session_id not in session:
        return jsonify({"message": "Invalid session or session expired"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received"}), 400

    round_number = data.get('round')
    data['session_id'] = session_id
    data['timestamp'] = datetime.datetime.now(datetime.timezone.utc)

    # Store in new collection for round surveys
    try:
        result = db.round_surveys.insert_one(data)

        # Update round completion status
        if round_number == 1:
            session[session_id]['round1_completed'] = True
            participants.update_one(
                {"session_id": session_id},
                {"$set": {"round1_completed": True, "round1_completion_time": datetime.datetime.now(datetime.timezone.utc)}}
            )
            # Move to Round 2
            session[session_id]['current_round'] = 2
            # Get next client from queue
            if len(session[session_id]['client_queue']) > 0:
                next_client = session[session_id]['client_queue'].pop(0)
                session[session_id]['current_client'] = next_client
                # Redirect to chat for Round 2
                next_url = url_for('index', session_id=session_id)
            else:
                return jsonify({"message": "No more clients in queue"}), 500
        else:  # Round 2 completed
            session[session_id]['round2_completed'] = True
            participants.update_one(
                {"session_id": session_id},
                {"$set": {"round2_completed": True, "round2_completion_time": datetime.datetime.now(datetime.timezone.utc)}}
            )
            # Redirect to Q3 (final post-task survey)
            next_url = url_for('getPostTaskSurvey', session_id=session_id)

        return jsonify({"message": "Survey saved successfully", "next_url": next_url}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/complete/')
def complete():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Session ID is missing", 400
    return render_template('complete.html', session_id=session_id)

@app.route('/history/<session_id>/<client_id>/')
def getClientHistory(session_id, client_id):
    chat_history = list(chat_history_collection.find({"session_id": session_id, "client_id": client_id}, {"_id": 0}))
    return jsonify({"chat_history": chat_history})

@app.route('/history/<session_id>/')
def getClientList(session_id):
    clients_info = list(chat_client_info.find({"session_id": session_id}, {"_id": 0, "client_name": 1, "client_id": 1, "category":1}))
    return jsonify({"clients_info": clients_info})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
#%%








