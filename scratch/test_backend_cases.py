import os
import sys
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.history_parser import process_history_row, compute_risk_summary, parse_php_serialized_instances

class MockParticipant:
    def __init__(self):
        self.id = 1
        self.blinded_subject_id = "SUBJ-001"

class MockBatch:
    def __init__(self):
        self.id = 1
        self.filename = "test.csv"

def run_test():
    print("--- Testing Missing Data (# - No) ---")
    res1 = parse_php_serialized_instances("#1 - s:6:\"# - No\";")
    print(f"Parsed '# - No': {res1}")
    
    print("\n--- Testing Gravidity Mapping (Nulligravida Bug) ---")
    fields = [
        type('obj', (object,), {'field_key': 'has_participant_had_any_previous_pregnancies', 'value': 'No', 'domain': 'test'}),
        type('obj', (object,), {'field_key': 'if_yes_how_many_previous_pregnancies', 'value': None, 'domain': 'test'}),
        type('obj', (object,), {'field_key': 'age', 'value': '25', 'domain': 'test'})
    ]
    summary = compute_risk_summary(fields)
    print(f"Gravidity when No previous pregnancies: {summary.get('gravidity')}")
    print(f"Demographic Opening: {summary.get('demographic_opening')}")

    fields2 = [
        type('obj', (object,), {'field_key': 'has_participant_had_any_previous_pregnancies', 'value': 'Yes', 'domain': 'test'}),
        type('obj', (object,), {'field_key': 'if_yes_how_many_previous_pregnancies', 'value': '2', 'domain': 'test'}),
        type('obj', (object,), {'field_key': 'number_of_live_births', 'value': '2', 'domain': 'test'}),
        type('obj', (object,), {'field_key': 'age', 'value': '30', 'domain': 'test'})
    ]
    summary2 = compute_risk_summary(fields2)
    print(f"Gravidity when 2 previous pregnancies: {summary2.get('gravidity')}")
    print(f"Demographic Opening: {summary2.get('demographic_opening')}")
    
    print("\nAll backend cases executed successfully.")

if __name__ == "__main__":
    run_test()
