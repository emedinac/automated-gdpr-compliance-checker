"""
GDPR article definitions used as the compliance checklist.
Each article has: id, title, key_requirements, risk_keywords.
"""

GDPR_ARTICLES = [
    {
        "id": "Art.5",
        "title": "Principles of processing personal data",
        "requirements": [
            "Data must be processed lawfully, fairly, and transparently",
            "Data collected for specified, explicit, and legitimate purposes",
            "Data minimisation: only data necessary for the purpose",
            "Data must be accurate and kept up to date",
            "Storage limitation: not kept longer than necessary",
            "Integrity and confidentiality: appropriate security measures",
        ],
        "risk_keywords": [
            "collect", "process", "store", "retain", "personal data",
            "indefinitely", "unlimited", "any purpose",
        ],
    },
    {
        "id": "Art.6",
        "title": "Lawfulness of processing",
        "requirements": [
            "Processing requires a legal basis: consent, contract, legal obligation, vital interests, public task, or legitimate interests",
            "Consent must be freely given, specific, informed, and unambiguous",
        ],
        "risk_keywords": [
            "consent", "agree", "legitimate interest", "legal basis",
            "implied consent", "opt-out", "pre-ticked",
        ],
    },
    {
        "id": "Art.7",
        "title": "Conditions for consent",
        "requirements": [
            "Consent must be demonstrable",
            "Request for consent must be clearly distinguishable",
            "Data subject can withdraw consent at any time",
            "Withdrawal must be as easy as giving consent",
        ],
        "risk_keywords": [
            "withdraw", "revoke", "consent", "opt-out", "unsubscribe",
            "cannot withdraw", "irrevocable",
        ],
    },
    {
        "id": "Art.13",
        "title": "Information to be provided (direct collection)",
        "requirements": [
            "Identity and contact details of controller",
            "Contact details of DPO if applicable",
            "Purposes and legal basis of processing",
            "Recipients or categories of recipients",
            "Retention period",
            "Rights of data subject",
        ],
        "risk_keywords": [
            "privacy policy", "controller", "dpo", "data protection officer",
            "retention", "third party", "share", "recipients",
        ],
    },
    {
        "id": "Art.17",
        "title": "Right to erasure ('right to be forgotten')",
        "requirements": [
            "Data subject can request deletion of personal data",
            "Controller must delete without undue delay when data is no longer necessary",
            "Must inform third parties of erasure request",
        ],
        "risk_keywords": [
            "delete", "erasure", "remove", "forget", "right to be forgotten",
            "cannot delete", "non-deletable",
        ],
    },
    {
        "id": "Art.20",
        "title": "Right to data portability",
        "requirements": [
            "Data subject has right to receive their data in structured, machine-readable format",
            "Right to transmit data to another controller",
        ],
        "risk_keywords": [
            "portability", "export", "download", "transfer", "machine-readable",
        ],
    },
    {
        "id": "Art.25",
        "title": "Data protection by design and by default",
        "requirements": [
            "Privacy by design implemented in systems",
            "Only necessary data processed by default",
            "Technical and organisational measures implemented",
        ],
        "risk_keywords": [
            "by design", "by default", "privacy by design", "technical measures",
            "organisational measures", "pseudonymisation",
        ],
    },
    {
        "id": "Art.28",
        "title": "Processor obligations",
        "requirements": [
            "Processors must act only on controller instructions",
            "Data Processing Agreement (DPA) required",
            "Sub-processors require prior written authorisation",
        ],
        "risk_keywords": [
            "processor", "sub-processor", "data processing agreement", "dpa",
            "third party processor", "vendor", "subcontractor",
        ],
    },
    {
        "id": "Art.32",
        "title": "Security of processing",
        "requirements": [
            "Appropriate technical and organisational security measures",
            "Encryption and pseudonymisation where appropriate",
            "Ability to ensure ongoing confidentiality, integrity, availability",
            "Regular testing and evaluation of security measures",
        ],
        "risk_keywords": [
            "security", "encryption", "pseudonymisation", "breach",
            "access control", "backup", "ssl", "tls", "unencrypted",
        ],
    },
    {
        "id": "Art.33",
        "title": "Notification of personal data breach",
        "requirements": [
            "Breach must be notified to supervisory authority within 72 hours",
            "Processor must notify controller without undue delay",
        ],
        "risk_keywords": [
            "breach", "incident", "72 hours", "notify", "supervisory authority",
            "data leak",
        ],
    },
    {
        "id": "Art.44-49",
        "title": "Transfers to third countries",
        "requirements": [
            "Transfer to third countries only with adequate protection",
            "Adequacy decision, standard contractual clauses, or binding corporate rules required",
        ],
        "risk_keywords": [
            "transfer", "third country", "usa", "united states", "china",
            "standard contractual clauses", "scc", "adequacy", "binding corporate rules",
        ],
    },
]
