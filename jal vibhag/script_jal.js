/* ============================================================
   script.js — Uttarakhand Jal Sansthan Website JavaScript
   ============================================================ */

// ============================================================
// COMPLAINTS DROPDOWN — now just opens dashboard directly
// ============================================================

document.addEventListener('click', function (e) {
  var nav = document.getElementById('complaintsNav');
  if (nav && !nav.contains(e.target)) {
    nav.classList.remove('open');
  }
});

// ============================================================
// DASHBOARD — OPEN / CLOSE
// ============================================================

function openDashboard() {
  var nav = document.getElementById('complaintsNav');
  if (nav) nav.classList.remove('open');

  var overlay = document.getElementById('dashboardOverlay');
  if (!overlay) return;
  overlay.classList.add('show');
  document.body.style.overflow = 'hidden';

  renderComplaints();
  updateStats();
}

function closeDashboard() {
  var overlay = document.getElementById('dashboardOverlay');
  if (overlay) overlay.classList.remove('show');
  document.body.style.overflow = '';
}

function overlayClickClose(e) {
  var overlay = document.getElementById('dashboardOverlay');
  if (overlay && e.target === overlay) closeDashboard();
}

// ============================================================
// TAB SWITCHING
// ============================================================

var TAB_IDS = ['tab-file', 'tab-list', 'tab-track'];

function switchTab(btn, tabId) {
  document.querySelectorAll('.dash-tab').forEach(function (t) {
    t.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
  TAB_IDS.forEach(function (id) {
    var p = document.getElementById(id);
    if (p) p.style.display = 'none';
  });
  var active = document.getElementById(tabId);
  if (active) active.style.display = 'block';
}

// ============================================================
// FILE COMPLAINT (localStorage)
// ============================================================

function fileComplaint() {
  var accountNo     = document.getElementById('fc_accountNo').value.trim();
  var consumerName  = document.getElementById('fc_name').value.trim();
  var complaintType = document.getElementById('fc_type').value;
  var description   = document.getElementById('fc_desc').value.trim();
  var mobile        = document.getElementById('fc_mobile').value.trim();
  var zone          = document.getElementById('fc_zone').value;

  if (!accountNo || !consumerName || !complaintType || !description || !mobile || !zone) {
    showFormMsg('Please fill all required fields.', 'error');
    return;
  }

  var complaintId = 'UJS-' + Date.now().toString().slice(-6);
  var today = new Date().toLocaleDateString('en-IN');

  var complaint = {
    id:          complaintId,
    accountNo:   accountNo,
    name:        consumerName,
    type:        complaintType,
    description: description,
    mobile:      mobile,
    zone:        zone,
    date:        today,
    status:      'Pending'
  };

  var existing = JSON.parse(localStorage.getItem('ujs_complaints') || '[]');
  existing.push(complaint);
  localStorage.setItem('ujs_complaints', JSON.stringify(existing));

  // reset form
  ['fc_accountNo','fc_name','fc_desc','fc_mobile'].forEach(function(id){
    document.getElementById(id).value = '';
  });
  document.getElementById('fc_type').value = '';
  document.getElementById('fc_zone').value = '';

  showFormMsg('✅ Complaint filed! Your ID: <b>' + complaintId + '</b>. SMS confirmation will be sent to your mobile.', 'success');

  renderComplaints();
  updateStats();
}

function showFormMsg(msg, type) {
  var el = document.getElementById('fc_msg');
  el.innerHTML = msg;
  el.className = 'fc-msg fc-msg-' + type;
  el.style.display = 'block';
  setTimeout(function(){ el.style.display = 'none'; }, 6000);
}

// ============================================================
// RENDER COMPLAINTS LIST
// ============================================================

function renderComplaints() {
  var complaints = JSON.parse(localStorage.getItem('ujs_complaints') || '[]');
  var list = document.getElementById('cl_list');
  if (!list) return;

  if (complaints.length === 0) {
    list.innerHTML = '<p class="cl-empty">No complaints filed yet.</p>';
    return;
  }

  var reversed = complaints.slice().reverse();
  list.innerHTML = reversed.map(function(c) {
    var statusClass = c.status === 'Resolved' ? 'cl-badge-resolved' : 'cl-badge-pending';
    return '<div class="cl-card">' +
      '<div class="cl-card-top">' +
        '<span class="cl-id">' + c.id + '</span>' +
        '<span class="cl-badge ' + statusClass + '">' + c.status + '</span>' +
      '</div>' +
      '<p class="cl-type">' + c.type + '</p>' +
      '<p class="cl-desc">' + c.description + '</p>' +
      '<div class="cl-bottom">' +
        '<span>Zone: ' + c.zone + '</span>' +
        '<span>Acct: ' + c.accountNo + '</span>' +
        '<span>Date: ' + c.date + '</span>' +
      '</div>' +
    '</div>';
  }).join('');
}

// ============================================================
// UPDATE STATS
// ============================================================

function updateStats() {
  var complaints = JSON.parse(localStorage.getItem('ujs_complaints') || '[]');
  var total    = complaints.length;
  var resolved = complaints.filter(function(c){ return c.status === 'Resolved'; }).length;
  var pending  = total - resolved;

  var t = document.getElementById('stat_total');
  var p = document.getElementById('stat_pending');
  var r = document.getElementById('stat_resolved');
  if (t) t.textContent = total;
  if (p) p.textContent = pending;
  if (r) r.textContent = resolved;
}

// ============================================================
// TRACK COMPLAINT
// ============================================================

function trackComplaint() {
  var query = document.getElementById('track_input').value.trim().toUpperCase();
  var resultEl = document.getElementById('track_result');
  if (!query) { resultEl.innerHTML = '<p class="cl-empty">Enter a Complaint ID or Mobile Number.</p>'; resultEl.style.display='block'; return; }

  var complaints = JSON.parse(localStorage.getItem('ujs_complaints') || '[]');
  var found = complaints.filter(function(c){
    return c.id.toUpperCase().includes(query) || c.mobile.includes(query);
  });

  if (found.length === 0) {
    resultEl.innerHTML = '<p class="cl-empty">No complaint found for: <b>' + query + '</b></p>';
    resultEl.style.display='block';
    return;
  }

  resultEl.innerHTML = found.map(function(c){
    var statusClass = c.status === 'Resolved' ? 'cl-badge-resolved' : 'cl-badge-pending';
    return '<div class="cl-card cl-card-track">' +
      '<div class="cl-card-top">' +
        '<span class="cl-id">' + c.id + '</span>' +
        '<span class="cl-badge ' + statusClass + '">' + c.status + '</span>' +
      '</div>' +
      '<p class="cl-type">' + c.type + '</p>' +
      '<p class="cl-desc">' + c.description + '</p>' +
      '<div class="cl-meta-grid">' +
        '<div><b>Name</b><br>' + c.name + '</div>' +
        '<div><b>Account</b><br>' + c.accountNo + '</div>' +
        '<div><b>Zone</b><br>' + c.zone + '</div>' +
        '<div><b>Mobile</b><br>' + c.mobile + '</div>' +
        '<div><b>Filed On</b><br>' + c.date + '</div>' +
        '<div><b>Status</b><br>' + c.status + '</div>' +
      '</div>' +
      '<div class="track-timeline">' +
        '<div class="tl-item tl-done"><span class="tl-dot"></span><span>Complaint Registered — ' + c.date + '</span></div>' +
        '<div class="tl-item tl-done"><span class="tl-dot"></span><span>Acknowledged by Division</span></div>' +
        '<div class="tl-item ' + (c.status==='Resolved'?'tl-done':'tl-pending') + '"><span class="tl-dot"></span><span>' + (c.status==='Resolved'?'Resolved & Closed':'Awaiting Field Assignment') + '</span></div>' +
      '</div>' +
    '</div>';
  }).join('');
  resultEl.style.display='block';
}

// ============================================================
// KEYBOARD — Escape closes dashboard
// ============================================================

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    var overlay = document.getElementById('dashboardOverlay');
    if (overlay && overlay.classList.contains('show')) closeDashboard();
  }
});