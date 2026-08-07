// =============================
// DATA STORE (localStorage-backed)
// =============================
const STORAGE_KEY = 'pwd_complaints_uk';

// Seed data — realistic pre-filled complaints
const seedComplaints = [
  { id:'PWD-2026-00001', name:'Ramesh Kumar',     district:'Dehradun',         category:'Road Damage / Pothole',     location:'Ring Road near ISBT',          desc:'Large pothole causing accidents near ISBT bus stand.',                   status:'Resolved',    filed:'2026-01-05', updated:'2026-02-10', timeline:['Filed','Acknowledged','Inspection Done','Resolved'] },
  { id:'PWD-2026-00002', name:'Sunita Rawat',     district:'Haridwar',         category:'Drainage / Waterlogging',   location:'Rishikesh bypass NH-58',       desc:'Blocked drains causing severe waterlogging every rain.',                 status:'In Progress', filed:'2026-01-18', updated:'2026-03-02', timeline:['Filed','Acknowledged','Inspection Done'] },
  { id:'PWD-2026-00003', name:'Mohan Singh',      district:'Nainital',         category:'Bridge Condition',          location:'Bhowali-Ramgarh Road Bridge',  desc:'Bridge railing broken, dangerous for pedestrians.',                     status:'Pending',     filed:'2026-02-01', updated:'2026-02-01', timeline:['Filed'] },
  { id:'PWD-2026-00004', name:'Priya Bisht',      district:'Almora',           category:'Contractor Negligence',     location:'Almora-Ranikhet Highway',      desc:'Road work incomplete, contractor abandoned site mid-project.',           status:'In Progress', filed:'2026-02-14', updated:'2026-03-20', timeline:['Filed','Acknowledged'] },
  { id:'PWD-2026-00005', name:'Vikas Negi',       district:'Chamoli',          category:'Road Damage / Pothole',     location:'Badrinath National Highway',   desc:'Major road erosion after landslide, no repair done for 3 months.',       status:'In Progress', filed:'2026-02-20', updated:'2026-04-01', timeline:['Filed','Acknowledged','Inspection Done'] },
  { id:'PWD-2026-00006', name:'Kavita Pandey',    district:'Tehri Garhwal',    category:'Government Building Issue', location:'Tehri DC Office Complex',      desc:'Roof leakage in district office building causing damage to records.',    status:'Resolved',    filed:'2026-01-10', updated:'2026-03-15', timeline:['Filed','Acknowledged','Inspection Done','Resolved'] },
  { id:'PWD-2026-00007', name:'Ashok Dobhal',     district:'Pauri Garhwal',    category:'Encroachment on Road',      location:'Kotdwar Town Main Road',       desc:'Shops encroaching on road reducing width to half.',                      status:'Pending',     filed:'2026-03-05', updated:'2026-03-05', timeline:['Filed'] },
  { id:'PWD-2026-00008', name:'Reena Joshi',      district:'Uttarkashi',       category:'Illegal Road Cutting',      location:'Gangotri Highway km 42',       desc:'Unauthorised road cutting for construction without ROW permission.',     status:'Rejected',    filed:'2026-02-28', updated:'2026-03-10', timeline:['Filed','Acknowledged','Rejected'] },
  { id:'PWD-2026-00009', name:'Deepak Arya',      district:'Udham Singh Nagar',category:'Streetlight / Road Marking',location:'Rudrapur Bypass',             desc:'No road markings on newly built bypass causing night-time accidents.',   status:'Pending',     filed:'2026-03-18', updated:'2026-03-18', timeline:['Filed'] },
  { id:'PWD-2026-00010', name:'Geeta Bora',       district:'Dehradun',         category:'Road Damage / Pothole',     location:'Rajpur Road near Survey Chowk',desc:'Entire stretch of road damaged after rain, no repair for 2 months.',    status:'Resolved',    filed:'2026-01-22', updated:'2026-03-28', timeline:['Filed','Acknowledged','Inspection Done','Resolved'] },
  { id:'PWD-2026-00011', name:'Narendra Thapli',  district:'Haridwar',         category:'Corruption / Bribery',      location:'PWD Sub-Division Office',      desc:'Junior engineer demanding bribe for road cutting permission.',           status:'In Progress', filed:'2026-03-02', updated:'2026-04-10', timeline:['Filed','Acknowledged'] },
  { id:'PWD-2026-00012', name:'Anita Semwal',     district:'Chamoli',          category:'Bridge Condition',          location:'Joshimath-Badrinath Road',     desc:'Foot bridge over Alaknanda showing cracks, villagers afraid to use it.', status:'In Progress', filed:'2026-03-25', updated:'2026-04-15', timeline:['Filed','Acknowledged','Inspection Done'] },
];

function loadComplaints() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [...seedComplaints];
  } catch(e) { return [...seedComplaints]; }
}

function saveComplaints(list) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(list)); } catch(e) {}
}

let complaints = loadComplaints();
if (complaints.length < seedComplaints.length) {
  complaints = [...seedComplaints, ...complaints.filter(c => !seedComplaints.find(s => s.id === c.id))];
  saveComplaints(complaints);
}

// =============================
// STATS
// =============================
function updateStats() {
  document.getElementById('statTotal').textContent    = complaints.length;
  document.getElementById('statPending').textContent  = complaints.filter(c => c.status === 'Pending').length;
  document.getElementById('statProgress').textContent = complaints.filter(c => c.status === 'In Progress').length;
  document.getElementById('statResolved').textContent = complaints.filter(c => c.status === 'Resolved').length;
}
updateStats();

// =============================
// TAB SWITCHING
// =============================
function openTab(e, id) {
  document.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  e.currentTarget.classList.add('active');
  document.getElementById(id).classList.add('active');
  if (id === 'tab-public') renderTable();
}

// =============================
// GENERATE ID
// =============================
function generateID() {
  const maxN = complaints.reduce((max, c) => {
    const n = parseInt(c.id.split('-').pop());
    return isNaN(n) ? max : Math.max(max, n);
  }, 0);
  return 'PWD-2026-' + String(maxN + 1).padStart(5, '0');
}

// =============================
// SUBMIT COMPLAINT
// =============================
function submitComplaint() {
  const name     = document.getElementById('f-name').value.trim();
  const mobile   = document.getElementById('f-mobile').value.trim();
  const district = document.getElementById('f-district').value;
  const category = document.getElementById('f-category').value;
  const location = document.getElementById('f-location').value.trim();
  const desc     = document.getElementById('f-desc').value.trim();

  if (!name || !mobile || !district || !category || !location || !desc) {
    alert('Please fill in all required fields marked with *.');
    return;
  }
  if (!/^\d{10}$/.test(mobile)) {
    alert('Please enter a valid 10-digit mobile number.');
    return;
  }

  const id = generateID();
  const today = new Date().toISOString().split('T')[0];

  const complaint = {
    id, name, district, category, location, desc,
    status: 'Pending', filed: today, updated: today, timeline: ['Filed']
  };

  complaints.push(complaint);
  saveComplaints(complaints);
  updateStats();

  document.getElementById('generatedID').textContent = id;
  document.getElementById('submitToast').classList.add('show');

  // Clear form
  ['f-name', 'f-mobile', 'f-email', 'f-location', 'f-desc'].forEach(fid => {
    document.getElementById(fid).value = '';
  });
  document.getElementById('f-district').value = '';
  document.getElementById('f-category').value = '';
  document.getElementById('f-file').value = '';

  document.getElementById('submitToast').scrollIntoView({ behavior: 'smooth' });
}

// =============================
// TRACK COMPLAINT
// =============================
const timelineLabels = {
  'Filed':           { note: 'Complaint received and registered in the system.' },
  'Acknowledged':    { note: 'PWD office has acknowledged your complaint.' },
  'Inspection Done': { note: 'Field inspection carried out by PWD officer.' },
  'Resolved':        { note: 'Issue resolved. Please verify and provide feedback.' },
  'Rejected':        { note: 'Complaint could not be processed. Contact PWD office for details.' },
};

function badgeHtml(status) {
  const map = {
    'Pending':     'badge-pending',
    'In Progress': 'badge-progress',
    'Resolved':    'badge-resolved',
    'Rejected':    'badge-rejected'
  };
  return `<span class="badge ${map[status] || 'badge-pending'}">${status}</span>`;
}

function trackComplaint() {
  const id = document.getElementById('trackID').value.trim().toUpperCase();
  const resultDiv = document.getElementById('trackResult');

  if (!id) { alert('Please enter a Complaint ID.'); return; }

  const c = complaints.find(x => x.id.toUpperCase() === id);
  resultDiv.classList.add('show');

  if (!c) {
    resultDiv.innerHTML = `<div class="not-found">❌ No complaint found with ID <strong>${id}</strong>.<br/>Please check the ID and try again.</div>`;
    return;
  }

  const totalSteps = ['Filed', 'Acknowledged', 'Inspection Done', c.status === 'Rejected' ? 'Rejected' : 'Resolved'];
  const doneSteps = c.timeline || ['Filed'];

  const stepsHtml = totalSteps.map((step) => {
    const done = doneSteps.includes(step);
    const isCurrent = step === doneSteps[doneSteps.length - 1];
    const cls = isCurrent ? 'current' : (done ? 'done' : '');
    const info = timelineLabels[step] || {};
    return `<div class="t-step ${cls}">
      <div class="t-step-label">${step}</div>
      ${isCurrent ? `<div class="t-step-date">Last Updated: ${c.updated}</div>` : ''}
      ${done || isCurrent ? `<div class="t-step-note">${info.note || ''}</div>` : ''}
    </div>`;
  }).join('');

  resultDiv.innerHTML = `
    <div class="complaint-detail-card">
      <div class="complaint-detail-header">
        <h3>${c.id}</h3>
        ${badgeHtml(c.status)}
      </div>
      <div class="complaint-detail-body">
        <div class="detail-row"><span class="detail-label">Category</span><span class="detail-val">${c.category}</span></div>
        <div class="detail-row"><span class="detail-label">District</span><span class="detail-val">${c.district}</span></div>
        <div class="detail-row"><span class="detail-label">Location</span><span class="detail-val">${c.location}</span></div>
        <div class="detail-row"><span class="detail-label">Description</span><span class="detail-val">${c.desc}</span></div>
        <div class="detail-row"><span class="detail-label">Filed On</span><span class="detail-val">${c.filed}</span></div>
        <div class="detail-row"><span class="detail-label">Last Updated</span><span class="detail-val">${c.updated}</span></div>
      </div>
    </div>
    <div class="timeline">
      <div class="timeline-title">Progress Timeline</div>
      <div class="timeline-steps">${stepsHtml}</div>
    </div>`;
}

// =============================
// PUBLIC BOARD
// =============================
const PAGE_SIZE = 8;
let currentPage = 1;

function renderTable() {
  const search   = document.getElementById('pubSearch').value.toLowerCase();
  const status   = document.getElementById('pubStatus').value;
  const district = document.getElementById('pubDistrict').value;
  const category = document.getElementById('pubCategory').value;

  let filtered = complaints.filter(c => {
    const matchSearch = !search ||
      c.id.toLowerCase().includes(search) ||
      c.location.toLowerCase().includes(search) ||
      c.category.toLowerCase().includes(search) ||
      c.district.toLowerCase().includes(search);
    const matchStatus   = !status   || c.status === status;
    const matchDistrict = !district || c.district === district;
    const matchCategory = !category || c.category === category;
    return matchSearch && matchStatus && matchDistrict && matchCategory;
  });

  // Sort newest first
  filtered = filtered.slice().sort((a, b) => b.filed.localeCompare(a.filed));

  const total = filtered.length;
  const pages = Math.ceil(total / PAGE_SIZE) || 1;
  if (currentPage > pages) currentPage = 1;

  const paginated = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const tbody = document.getElementById('publicTableBody');
  if (paginated.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#aaa;">No complaints found matching the filters.</td></tr>`;
  } else {
    tbody.innerHTML = paginated.map(c => `
      <tr>
        <td>${c.id}</td>
        <td>${c.filed}</td>
        <td>${c.district}</td>
        <td>${c.category}</td>
        <td>${c.location}</td>
        <td>${badgeHtml(c.status)}</td>
        <td>${c.updated}</td>
      </tr>`).join('');
  }

  // Pagination
  const pag = document.getElementById('pagination');
  pag.innerHTML = '';
  for (let i = 1; i <= pages; i++) {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (i === currentPage ? ' active' : '');
    btn.textContent = i;
    btn.onclick = () => { currentPage = i; renderTable(); };
    pag.appendChild(btn);
  }
}

// Init public board on page load
renderTable();