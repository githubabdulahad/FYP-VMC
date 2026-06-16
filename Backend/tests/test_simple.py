from coding.evidence_extractor import EvidenceExtractor

soap = {
    'subjective': 'Pain for 3 months',
    'objective': 'BP 140/90',
    'assessment': 'Chronic pain acute exacerbation', 
    'plan': 'CT scan'
}

ev = EvidenceExtractor.extract_evidence(soap)
print('Evidence extraction working')
print('Diagnoses found:', len(ev["diagnoses"]))
print('Procedures found:', len(ev["procedures"]))
print('Symptoms found:', len(ev["symptoms"]))
print('Findings found:', len(ev["findings"]))
