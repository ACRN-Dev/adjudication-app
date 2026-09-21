import sys

filepath = r'c:\Automation\Adjudication app\backend\api\adjudication.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_sig = '''@router.post("/{subject_id}/submit")
def submit_adjudication(
    subject_id: str,
    sub: ReviewerSubmission,
    db: Session = Depends(get_db),
):
    """
    Submit a blinded adjudication determination for a specific visit.
    subject_id is the BLINDED case reference (e.g. ADJ-E2E-001).
    """'''

new_sig = '''def _process_single_submission(subject_id: str, sub: ReviewerSubmission, db: Session):'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    
    # Remove db.commit() from _process_single_submission
    content = content.replace('    db.commit()\n\n    return {\n', '    return {\n')
    
    new_endpoint = '''
@router.post("/{subject_id}/submit")
def submit_adjudication(
    subject_id: str,
    sub: ReviewerSubmission,
    db: Session = Depends(get_db),
):
    if not sub.differential_diagnosis or not sub.differential_diagnosis.strip():
        raise HTTPException(status_code=422, detail="Differential diagnosis is required.")

    if sub.is_overall_first:
        results = []
        for onset in sub.per_visit_onset:
            single_sub = sub.model_copy(deep=True) if hasattr(sub, "model_copy") else sub.copy(deep=True)
            single_sub.is_overall_first = False
            single_sub.visit_number = onset.visit_number
            single_sub.meets_criteria = onset.meets_criteria
            if onset.meets_criteria:
                single_sub.diagnosis = onset.diagnosis or sub.diagnosis
                single_sub.onset_class = onset.onset_class or sub.onset_class
            else:
                single_sub.diagnosis = DiagnosisCode.NOT_PE
                single_sub.onset_class = OnsetClass.NOT_YET_CLASSIFIABLE
                
            res = _process_single_submission(subject_id, single_sub, db)
            results.append(res)
        db.commit()
        return {"status": "success", "results": results}
    else:
        res = _process_single_submission(subject_id, sub, db)
        db.commit()
        return res
'''
    target = '@router.get("/{subject_id}")'
    if target in content:
        content = content.replace(target, new_endpoint + '\n' + target)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Refactor successful!")
    else:
        print("Could not find get_adjudication_status endpoint.")
else:
    print("Could not find submit_adjudication signature.")
