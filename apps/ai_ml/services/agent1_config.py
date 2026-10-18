"""Agent1 department routing, authority metadata, and dummy portal mapping."""

from django.conf import settings

AUTHORITY_MAP = {
    "Electricity": "UPCL (Uttarakhand Power Corporation Limited)",
    "Water": "Jal Sansthan (Uttarakhand Jal Sansthan)",
    "PWD": "PWD (Public Works Department)",
    "Education": "District Education Officer (DEO)",
    "Other": "District Collectorate Grievance Cell",
}

AUTHORITY_DETAILS = {
    "Electricity": {
        "designation": "The Executive Engineer",
        "office": "UPCL (Uttarakhand Power Corporation Limited)",
        "address": "UPCL Divisional Office, Dehradun, Uttarakhand",
    },
    "Water": {
        "designation": "The Executive Engineer",
        "office": "Jal Sansthan (Uttarakhand Jal Sansthan)",
        "address": "Jal Sansthan Division Office, Dehradun, Uttarakhand",
    },
    "PWD": {
        "designation": "The Executive Engineer",
        "office": "Public Works Department (PWD)",
        "address": "PWD Division Office, Dehradun, Uttarakhand",
    },
    "Education": {
        "designation": "The District Education Officer (DEO)",
        "office": "District Education Office",
        "address": "District Education Office, Dehradun, Uttarakhand",
    },
    "Other": {
        "designation": "The District Magistrate",
        "office": "District Collectorate Grievance Cell",
        "address": "District Collectorate, Dehradun, Uttarakhand",
    },
}

NAGRIK_CATEGORY_MAP = {
    "Electricity": "Electricity",
    "Water": "Water Supply",
    "PWD": "Roads & Potholes",
    "Education": "Education",
    "Other": "Other",
}

VALID_ZONES = [
    "Dehradun", "Haridwar", "Nainital", "Almora", "Pauri Garhwal",
    "Tehri Garhwal", "Uttarkashi", "Chamoli", "Rudraprayag",
    "Pithoragarh", "Bageshwar", "Champawat", "US Nagar", "Udham Singh Nagar",
]

BIJLI_TYPE_MAP = {
    "No Power Supply": "No Power Supply",
    "Voltage Issue": "Voltage Issue",
    "Wrong Bill": "Wrong Bill",
    "Meter Fault": "Meter Fault",
    "Street Light": "Street Light Issue",
    "Billing Dispute": "Wrong Bill",
    "Meter Issue": "Meter Fault",
}

JAL_TYPE_MAP = {
    "Water Supply Disruption": "Water Supply Disruption",
    "Pipe Leakage / Burst": "Pipe Leakage / Burst",
    "Billing Dispute": "Billing Dispute",
    "Water Quality Issue": "Water Quality Issue",
    "New Water Connection": "New Water Connection",
    "Low Water Pressure": "Low Water Pressure",
    "Meter Issue": "Meter Issue",
    "Sewage / Drainage Problem": "Sewage / Drainage Problem",
}

PWD_CATEGORY_MAP = {
    "Road Pothole": "Road Damage / Pothole",
    "Encroachment on Road": "Encroachment on Road",
    "Drainage / Waterlogging": "Drainage / Waterlogging",
    "Bridge Condition": "Bridge Condition",
    "Streetlight / Road Marking": "Streetlight / Road Marking",
    "Government Building Issue": "Government Building Issue",
    "Illegal Road Cutting": "Illegal Road Cutting",
    "Contractor Negligence": "Contractor Negligence",
    "Corruption / Bribery": "Corruption / Bribery",
    "Garbage / Sanitation Issue": "Other",
    "Other Request": "Other",
}

EDUCATION_CATEGORY_MAP = {
    "Teacher Transfer / Posting Issue": "Teacher Transfer / Posting Issue",
    "Salary / Pay Dispute": "Salary / Pay Dispute",
    "School Infrastructure Problem": "School Infrastructure Problem",
    "Mid-Day Meal Complaint": "Mid-Day Meal Complaint",
    "Examination Related": "Examination Related",
    "Scholarship / Fee Issue": "Scholarship / Fee Issue",
    "Admission Problem": "Admission Problem",
    "Text Book / Material Unavailability": "Text Book / Material Unavailability",
    "Digital Device / Internet Connectivity": "Digital Device / Internet Connectivity",
    "Digital Device / Internet Issue": "Digital Device / Internet Connectivity",
    "Teacher Misconduct": "Teacher Misconduct",
    "RTI Related": "RTI Related",
}


def normalise_zone(raw: str) -> str:
    raw_lower = (raw or "").lower()
    for z in VALID_ZONES:
        if z.lower() in raw_lower or raw_lower in z.lower():
            return z
    return "Dehradun"


def portal_base() -> str:
    return getattr(settings, "DEPARTMENT_PORTAL_BASE", "http://127.0.0.1:5500").rstrip("/")


def department_portal_config(department: str) -> dict:
    """Return portal metadata for a classified Agent1 department."""
    base = portal_base()
    dept = department or "Other"
    if dept == "Electricity":
        return {
            "key": "bijli",
            "name": "UPCL — Electricity (Bijli Vibhag)",
            "portal_url": f"{base}/Bijli_vibhag/complaint.html",
            "api_path": "/departments/bijli/complaints/",
        }
    if dept == "Water":
        return {
            "key": "jal",
            "name": "Uttarakhand Jal Sansthan",
            "portal_url": f"{base}/jal%20vibhag/index.html",
            "api_path": "/departments/jal/complaints/",
        }
    if dept == "PWD":
        return {
            "key": "pwd",
            "name": "Public Works Department (PWD)",
            "portal_url": f"{base}/pwd/complaint.html",
            "api_path": "/departments/pwd/complaints/",
        }
    if dept == "Education":
        return {
            "key": "shiksha",
            "name": "Directorate of School Education",
            "portal_url": f"{base}/shiksha_vibhag/index.html",
            "api_path": "/departments/shiksha/complaints/",
        }
    return {
        "key": "pwd",
        "name": "District Collectorate (default routing demo → PWD portal)",
        "portal_url": f"{base}/pwd/complaint.html",
        "api_path": "/api/v1/departments/pwd/complaints/",
    }


def build_form_payload(
    department: str,
    subcategory: str,
    english_text: str,
    complaint_id: str,
    *,
    complainant_name: str = "The Complainant",
    mobile: str = "",
    email: str = "",
    district: str = "Dehradun",
    location: str = "",
) -> dict:
    """Map Agent1 classification to dummy-portal form fields."""
    zone = normalise_zone(district or location)
    mobile_clean = mobile if mobile and len(mobile) == 10 and mobile.isdigit() else "9999999999"
    email_clean = (email or "").strip()
    loc = location or zone
    desc = (english_text or "")[:500]
    header = f"[Nagrik Awaaz {complaint_id}] "
    full_desc = header + desc

    dept = department or "Other"
    if dept == "Electricity":
        cat = BIJLI_TYPE_MAP.get(subcategory, subcategory if subcategory in BIJLI_TYPE_MAP.values() else "Other")
        return {
            "portal_key": "bijli",
            "name": complainant_name,
            "mobile": mobile_clean,
            "district": zone,
            "category": cat,
            "description": full_desc,
            "accountNo": "",
            "email": email_clean,
            "location": loc,
            "nagrik_complaint_id": complaint_id,
        }
    if dept == "Water":
        cat = JAL_TYPE_MAP.get(subcategory, subcategory if subcategory in JAL_TYPE_MAP.values() else "Other Request")
        return {
            "portal_key": "jal",
            "accountNo": "N/A",
            "name": complainant_name,
            "mobile": mobile_clean,
            "zone": zone,
            "type": cat,
            "description": full_desc,
            "email": email_clean,
            "nagrik_complaint_id": complaint_id,
        }
    if dept == "Education":
        cat = EDUCATION_CATEGORY_MAP.get(subcategory, subcategory if subcategory in EDUCATION_CATEGORY_MAP.values() else "Other")
        return {
            "portal_key": "shiksha",
            "name": complainant_name,
            "mobile": mobile_clean,
            "district": zone,
            "category": cat,
            "school": "",
            "description": full_desc,
            "email": email_clean,
            "nagrik_complaint_id": complaint_id,
        }
    # PWD + Other default
    cat = PWD_CATEGORY_MAP.get(subcategory, subcategory if subcategory in PWD_CATEGORY_MAP.values() else "Other")
    return {
        "portal_key": "pwd",
        "name": complainant_name,
        "mobile": mobile_clean,
        "district": zone,
        "category": cat,
        "location": loc,
        "description": full_desc,
        "email": email_clean,
        "nagrik_complaint_id": complaint_id,
    }
