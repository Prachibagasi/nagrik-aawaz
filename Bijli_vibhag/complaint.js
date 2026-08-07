const API_BASE_URL = 'http://127.0.0.1:8000/api/v1/departments/bijli';
let complaintsCache = [];

window.addEventListener('load', function () {
    loadComplaints();
});

async function loadComplaints() {
    try {
        const response = await fetch(`${API_BASE_URL}/complaints/`);
        if (!response.ok) {
            throw new Error('Failed to load complaints from backend.');
        }
        complaintsCache = await response.json();
        renderComplaints();
        updateStats();
    } catch (error) {
        console.error(error);
        complaintsCache = [];
        const list = document.getElementById('complaintsList');
        if (list) {
            list.innerHTML = '<p class="no-complaints">Unable to load complaints from backend. Make sure the backend server is running at http://localhost:8000.</p>';
        }
        updateStats();
    }
}

// =============================================
// COMPLAINT FILE KARNA
// =============================================
function resetForm() {
    document.getElementById('accountNo').value    = '';
    document.getElementById('consumerName').value = '';
    document.getElementById('district').value     = '';
    document.getElementById('email').value        = '';
    document.getElementById('complaintType').value= '';
    document.getElementById('description').value  = '';
    document.getElementById('mobile').value       = '';
}

function validateMobile(mobile) {
    return /^\d{10}$/.test(mobile);
}

async function fileComplaint() {
    const accountNo     = document.getElementById('accountNo').value.trim();
    const consumerName  = document.getElementById('consumerName').value.trim();
    const district      = document.getElementById('district').value.trim();
    const email         = document.getElementById('email').value.trim();
    const complaintType = document.getElementById('complaintType').value;
    const description   = document.getElementById('description').value.trim();
    const mobile        = document.getElementById('mobile').value.trim();

    if (!consumerName || !district || !complaintType || !description || !mobile) {
        alert('Please fill all required fields before submitting.');
        return;
    }

    if (!validateMobile(mobile)) {
        alert('Please enter a valid 10-digit mobile number.');
        return;
    }

    const payload = {
        name: consumerName,
        mobile: mobile,
        category: complaintType,
        district: district,
        description: description,
        accountNo: accountNo,
        email: email,
        location: ''
    };

    try {
        const response = await fetch(`${API_BASE_URL}/complaints/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            const message = data.error || JSON.stringify(data);
            alert('Submission failed: ' + message);
            return;
        }

        complaintsCache.unshift(data);
        renderComplaints();
        updateStats();
        resetForm();
        alert('Complaint filed successfully!\nYour Complaint ID: ' + data.id);
    } catch (error) {
        console.error(error);
        alert('Unable to submit complaint. Confirm backend is running at http://localhost:8000.');
    }
}

// =============================================
// COMPLAINTS LIST RENDER KARNA
// =============================================
function renderComplaints() {
    const list = document.getElementById('complaintsList');

    if (!complaintsCache || complaintsCache.length === 0) {
        list.innerHTML = '<p class="no-complaints">No complaints filed yet.</p>';
        return;
    }

    list.innerHTML = complaintsCache.map(function(c) {
        const statusClass = c.status === 'Resolved' ? 'status-resolved' : 'status-pending';
        const displayType = c.category || c.type || 'Complaint';
        const dateText = c.filed || c.date || '';

        return `
            <div class="complaint-card">
                <div class="card-top">
                    <span class="complaint-id">${c.id}</span>
                    <span class="complaint-status ${statusClass}">${c.status}</span>
                </div>
                <p class="card-type">${displayType}</p>
                <p class="card-desc">${c.description}</p>
                <div class="card-bottom">
                    <span>Account: ${c.accountNo || 'N/A'}</span>
                    <span>Date: ${dateText}</span>
                </div>
            </div>
        `;
    }).join('');
}

// =============================================
// STATS UPDATE KARNA
// =============================================
function updateStats() {
    const total    = complaintsCache.length;
    const resolved = complaintsCache.filter(c => c.status === 'Resolved').length;
    const pending  = complaintsCache.filter(c => c.status === 'Pending').length;

    document.getElementById('totalCount').textContent    = total;
    document.getElementById('pendingCount').textContent  = pending;
    document.getElementById('resolvedCount').textContent = resolved;
}