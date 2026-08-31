import React from 'react';
import { Info } from 'lucide-react';

/**
 * InstructionBanner — Step-contextual guidance banner.
 * Per change record item #31: "How to Use" removed from every adjudication banner.
 * Banners are focused ONLY on the current clinical task.
 * Help is available under Governance & Tools > User Guide.
 */
export default function InstructionBanner({ step }) {
  const instructions = {
    1: {
      title: "Step 1 of 4: Select an Assigned Patient",
      description: "Choose a QC-approved, pseudonymised participant assigned to your independent review queue. RealTime imports are managed only in the Monitor/QC Portal."
    },
    2: {
      title: "Step 2 of 4: Review Clinical Evidence & System Derivation",
      description: "Review the blood pressure timeline, laboratory results, proteinuria assessments, and ISSHP 2021 automated derivation findings. Verify all source documents before proceeding."
    },
    3: {
      title: "Step 3 of 4: Approve Clinical Narrative & Record Adjudication (FORM-ADJ-15A/15B)",
      description: "Review and edit the structured case narrative. Record your final clinical diagnosis, onset classification, severity, and certainty level. Sign to lock the adjudication record."
    },
    4: {
      title: "Step 4 of 4: Adjudication Records Signed & Locked",
      description: "Your visit adjudications are signed and locked for concordance checking. Finalized cases can be downloaded for eTMF filing, or you can return to Step 1 for the next case."
    }
  };

  const current = instructions[step] || instructions[1];

  return (
    <div className="instruction-banner">
      <div className="instruction-icon">
        <Info size={20} />
      </div>
      <div className="instruction-content" style={{ flex: 1 }}>
        <h3>{current.title}</h3>
        <p>{current.description}</p>
      </div>
    </div>
  );
}
