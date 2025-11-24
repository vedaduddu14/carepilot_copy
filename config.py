'''
A single file for string literals that are being used across files.
This ensures that we only need to make changes in one location to reflect it across multiple scripts.
Reduces risk of errors when changing code or introducing new types.
'''
import random
import copy

ADMIN_PWD = "491062"

TYPE_EMO_THOUGHT = "You might be thinking"
TYPE_EMO_SHOES = "Put Yourself in the Client's Shoes"
TYPE_EMO_REFRAME = "Be Mindful of Your Emotions"
TYPE_SENTIMENT = "Client's Sentiment"
TYPE_INFO_CUE = "Response Suggestions"
TYPE_INFO_GUIDE = "Guidance for Complaint Resolution"

SUPPORT_TYPE_STRINGS = {
    "TYPE_EMO_THOUGHT" : TYPE_EMO_THOUGHT,
    "TYPE_EMO_SHOES" : TYPE_EMO_SHOES,
    "TYPE_EMO_REFRAME" : TYPE_EMO_REFRAME,
    "TYPE_SENTIMENT" : TYPE_SENTIMENT,
    "TYPE_INFO_CUE" : TYPE_INFO_CUE,
    "TYPE_INFO_GUIDE": TYPE_INFO_GUIDE
}

### Only for testing/debugging
randomQueue = [
    { "id": 1, "name": "Luis H", "domain": "Airline" , "grateful": 0, "ranting": 0, "expression":0, "civil": 0, "info": 1, "emo": 1},
    { "id": 2, "name": "Jamal K", "domain": "Hotel", "grateful": 1, "ranting": 0, "expression": 1, "civil": 1, "info": 1, "emo": 0},
    { "id": 3, "name": "Maria N", "domain": "Airline",  "grateful": 1, "ranting": 1, "expression": 1, "civil": 1, "info": 0, "emo": 1},
    { "id": 4, "name": "Elijah P", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 0, "info": 0, "emo": 0},
    { "id": 5, "name": "Anna Z", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 1, "info": 0, "emo": 1},
    { "id": 6, "name": "Samantha K", "domain": "Hotel" , "grateful": 0, "ranting": 1, "expression":0, "civil": 1, "info": 0, "emo": 1}
]

'''
For actual study scenario - 2 ROUNDS DESIGN
Round 1: Client WITHOUT AI (info=0, emo=0) - Baseline
Round 2: Client WITH treatment (info/emo based on assignment)

All clients: "grateful": 0, "ranting": 1, "expression":1, "civil": 0 (uncivil/mad)
Same difficulty for both rounds
'''
studyQueue = [
    # Round 1 Client - NO AI (will be forced to info=0, emo=0 regardless of assignment)
    { "id": 1, "round": 1, "grateful": 0, "ranting": 1, "expression":1, "civil": 0, "info": 0, "emo": 0},

    # Round 2 Client - WITH treatment (info/emo set based on treatment assignment)
    { "id": 2, "round": 2, "grateful": 0, "ranting": 1, "expression":1, "civil": 0, "info": 0, "emo": 0}
]

complaintTypes = [
    "Service Quality",
    "Product Issues",
    "Pricing and Charges",
    "Policy",
    "Resolution"
]

def get_study_queue(scenario):
    """
    Generate study queue with 2 clients (1 per round)
    Both clients use same scenario, same difficulty
    """
    names = [client['name'] for client in randomQueue]
    random.shuffle(names)
    random.shuffle(complaintTypes)

    # Only 2 clients now (one per round)
    for client_id in range(len(studyQueue)):
        client_name = names[client_id % len(names)]
        complaint_type = complaintTypes[client_id % len(complaintTypes)]

        studyQueue[client_id]['category'] = complaint_type
        studyQueue[client_id]['name'] = client_name
        studyQueue[client_id]['domain'] = scenario
        studyQueue[client_id]['avatar'] = "https://avatar.iran.liara.run/username?username="+client_name.replace(' ','+')

    return copy.deepcopy(studyQueue)
