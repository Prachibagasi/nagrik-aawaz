/* ============================================================
   script.js — Dept. of School Education, Uttarakhand
   ============================================================ */

// ============================================================
// HERO SLIDER
// ============================================================

var sliderIndex   = 0;
var sliderTotal   = 5;
var sliderTimer   = null;

function updateSlider() {
  var container = document.getElementById('slidesContainer');
  if (container) container.style.transform = 'translateX(-' + (sliderIndex * 100) + '%)';

  var dots = document.querySelectorAll('.dot');
  dots.forEach(function(d, i) {
    d.classList.toggle('active', i === sliderIndex);
  });
}

function moveSlider(dir) {
  sliderIndex = (sliderIndex + dir + sliderTotal) % sliderTotal;
  updateSlider();
  resetSliderTimer();
}

function goToSlide(n) {
  sliderIndex = n;
  updateSlider();
  resetSliderTimer();
}

function resetSliderTimer() {
  clearInterval(sliderTimer);
  sliderTimer = setInterval(function() { moveSlider(1); }, 5500);
}

// Start auto-play
document.addEventListener('DOMContentLoaded', function() {
  resetSliderTimer();
});

// ============================================================
// HORIZONTAL CARD SCROLL
// ============================================================

var trackPositions = {};

function scrollCards(trackId, dir) {
  var track = document.getElementById(trackId);
  if (!track) return;

  if (!trackPositions[trackId]) trackPositions[trackId] = 0;

  var cardWidth = 280; // approximate card + gap
  var step = cardWidth * 2;
  var maxScroll = track.scrollWidth - track.parentElement.offsetWidth;

  trackPositions[trackId] += dir * step;
  trackPositions[trackId] = Math.max(0, Math.min(trackPositions[trackId], maxScroll));

  track.style.transform = 'translateX(-' + trackPositions[trackId] + 'px)';
}

// ============================================================
// MOBILE NAV
// ============================================================

function toggleMobileMenu() {
  var navList = document.querySelector('.nav-list');
  if (navList) navList.classList.toggle('open');
}

// ============================================================
// HOLIDAY CALENDAR
// ============================================================

var calYear  = 2025;
var calMonth = 3; // 0-indexed: April = 3

// Holidays for 2025 (month 0-indexed, day)
var holidays2025 = [
  { month: 0,  day: 1,  name: 'New Year\'s Day' },
  { month: 0,  day: 14, name: 'Makar Sankranti' },
  { month: 0,  day: 26, name: 'Republic Day' },
  { month: 2,  day: 14, name: 'Holi (First Day)' },
  { month: 2,  day: 15, name: 'Holi' },
  { month: 3,  day: 6,  name: 'Ram Navami' },
  { month: 3,  day: 14, name: 'Ambedkar Jayanti' },
  { month: 3,  day: 18, name: 'Good Friday' },
  { month: 4,  day: 1,  name: 'Labour Day' },
  { month: 4,  day: 12, name: 'Buddha Purnima' },
  { month: 6,  day: 6,  name: 'Eid ul-Adha' },
  { month: 7,  day: 15, name: 'Independence Day' },
  { month: 8,  day: 5,  name: 'Teachers\' Day' },
  { month: 8,  day: 16, name: 'Eid-e-Milad' },
  { month: 9,  day: 2,  name: 'Gandhi Jayanti' },
  { month: 9,  day: 2,  name: 'Dussehra' },
  { month: 9,  day: 20, name: 'Diwali' },
  { month: 10, day: 5,  name: 'Govardhan Puja' },
  { month: 10, day: 15, name: 'Guru Nanak Jayanti' },
  { month: 11, day: 25, name: 'Christmas Day' },
  { month: 11, day: 31, name: 'New Year\'s Eve' }
];

var monthNames = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
];

function isHoliday(year, month, day) {
  if (year !== 2025) return null;
  for (var i = 0; i < holidays2025.length; i++) {
    if (holidays2025[i].month === month && holidays2025[i].day === day) return holidays2025[i];
  }
  return null;
}

function renderCalendar() {
  var label   = document.getElementById('calMonthLabel');
  var daysDiv = document.getElementById('calDays');
  var hList   = document.getElementById('holidaysList');
  if (!label || !daysDiv) return;

  label.textContent = monthNames[calMonth] + ' ' + calYear;

  // Remove old day cells (keep headers)
  var oldCells = daysDiv.parentElement.querySelectorAll('.cal-day');
  oldCells.forEach(function(c) { c.remove(); });

  var firstDay    = new Date(calYear, calMonth, 1).getDay(); // 0=Sun
  var daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  var today       = new Date();
  var grid        = daysDiv.parentElement; // .cal-grid

  // Empty cells
  for (var e = 0; e < firstDay; e++) {
    var empty = document.createElement('div');
    empty.className = 'cal-day empty';
    grid.appendChild(empty);
  }

  // Day cells
  var monthHolidays = [];
  for (var d = 1; d <= daysInMonth; d++) {
    var cell    = document.createElement('div');
    var dow     = new Date(calYear, calMonth, d).getDay();
    var holiday = isHoliday(calYear, calMonth, d);
    var isToday = (today.getFullYear() === calYear && today.getMonth() === calMonth && today.getDate() === d);

    var classes = ['cal-day'];
    if (isToday)  classes.push('today');
    else if (holiday) classes.push('holiday');
    else if (dow === 0 || dow === 6) classes.push('weekend');

    cell.className = classes.join(' ');
    cell.textContent = d;
    if (holiday) cell.title = holiday.name;
    grid.appendChild(cell);

    if (holiday) monthHolidays.push({ day: d, name: holiday.name });
  }

  // Holiday list
  if (hList) {
    if (monthHolidays.length === 0) {
      hList.innerHTML = '<div class="holiday-entry"><span class="h-name">No holidays this month</span></div>';
    } else {
      hList.innerHTML = monthHolidays.map(function(h) {
        return '<div class="holiday-entry">' +
          '<span class="h-name">' + h.name + '</span>' +
          '<span class="h-date">' + monthNames[calMonth].slice(0,3) + ' ' + h.day + '</span>' +
        '</div>';
      }).join('');
    }
  }
}

function changeMonth(dir) {
  calMonth += dir;
  if (calMonth > 11) { calMonth = 0; calYear++; }
  if (calMonth < 0)  { calMonth = 11; calYear--; }
  renderCalendar();
}

// Init calendar
document.addEventListener('DOMContentLoaded', function() {
  // Set to current month
  var now = new Date();
  calYear  = now.getFullYear();
  calMonth = now.getMonth();
  renderCalendar();
});

// ============================================================
// COMPLAINT DASHBOARD
// ============================================================

var CD_TABS = ['cdt-file', 'cdt-list', 'cdt-track'];

function openComplaintDashboard() {
  var overlay = document.getElementById('cdOverlay');
  if (!overlay) return;
  overlay.classList.add('show');
  document.body.style.overflow = 'hidden';
  cdUpdateStats();
  cdRenderList();
}

function closeComplaintDashboard() {
  var overlay = document.getElementById('cdOverlay');
  if (overlay) overlay.classList.remove('show');
  document.body.style.overflow = '';
}

function overlayClose(e) {
  var overlay = document.getElementById('cdOverlay');
  if (overlay && e.target === overlay) closeComplaintDashboard();
}

function cdSwitchTab(btn, tabId) {
  document.querySelectorAll('.cd-tab').forEach(function(t) { t.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  CD_TABS.forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  var panel = document.getElementById(tabId);
  if (panel) panel.style.display = 'block';

  if (tabId === 'cdt-list') cdRenderList();
}

// -- FILE COMPLAINT --
function cdFileComplaint() {
  var name   = document.getElementById('cf_name').value.trim();
  var mobile = document.getElementById('cf_mobile').value.trim();
  var cat    = document.getElementById('cf_cat').value;
  var dist   = document.getElementById('cf_dist').value;
  var desc   = document.getElementById('cf_desc').value.trim();

  if (!name || !mobile || !cat || !dist || !desc) {
    cdShowMsg('Please fill all required fields (marked with *).', 'error');
    return;
  }

  var id = 'DSE-' + new Date().getFullYear() + '-' + Date.now().toString().slice(-6);
  var today = new Date().toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });

  var complaint = {
    id:       id,
    name:     name,
    mobile:   mobile,
    email:    document.getElementById('cf_email').value.trim(),
    empid:    document.getElementById('cf_empid').value.trim(),
    cat:      cat,
    dist:     dist,
    school:   document.getElementById('cf_school').value.trim(),
    desc:     desc,
    date:     today,
    status:   'Pending'
  };

  var list = JSON.parse(localStorage.getItem('dse_complaints') || '[]');
  list.push(complaint);
  localStorage.setItem('dse_complaints', JSON.stringify(list));

  cdResetForm();
  cdShowMsg('✅ Complaint registered! Your ID: <strong>' + id + '</strong>. An SMS confirmation will be sent to your mobile number.', 'success');
  cdUpdateStats();
}

function cdResetForm() {
  ['cf_name','cf_mobile','cf_email','cf_empid','cf_school','cf_desc'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.value = '';
  });
  var cat = document.getElementById('cf_cat'); if (cat) cat.value = '';
  var dist = document.getElementById('cf_dist'); if (dist) dist.value = '';
}

function cdShowMsg(html, type) {
  var el = document.getElementById('cd_msg');
  if (!el) return;
  el.innerHTML = html;
  el.className = 'cd-msg cd-msg-' + type;
  el.style.display = 'block';
  setTimeout(function() { el.style.display = 'none'; }, 7000);
}

// -- RENDER LIST --
function cdRenderList() {
  var list = JSON.parse(localStorage.getItem('dse_complaints') || '[]');
  var container = document.getElementById('cd_complaints_list');
  if (!container) return;

  if (list.length === 0) {
    container.innerHTML = '<p class="cd-empty">📭 No complaints filed yet. Use the "File Complaint" tab to register one.</p>';
    return;
  }

  var reversed = list.slice().reverse();
  container.innerHTML = reversed.map(function(c) {
    var badgeClass = c.status === 'Resolved' ? 'cd-badge-resolved' : 'cd-badge-pending';
    return '<div class="cd-card">' +
      '<div class="cd-card-top">' +
        '<span class="cd-cid">' + c.id + '</span>' +
        '<span class="cd-badge ' + badgeClass + '">' + c.status + '</span>' +
      '</div>' +
      '<div class="cd-card-type">' + c.cat + '</div>' +
      '<div class="cd-card-desc">' + c.desc + '</div>' +
      '<div class="cd-card-meta">' +
        '<span>📍 ' + c.dist + '</span>' +
        '<span>👤 ' + c.name + '</span>' +
        '<span>📅 ' + c.date + '</span>' +
      '</div>' +
    '</div>';
  }).join('');
}

// -- UPDATE STATS --
function cdUpdateStats() {
  var list = JSON.parse(localStorage.getItem('dse_complaints') || '[]');
  var total    = list.length;
  var resolved = list.filter(function(c) { return c.status === 'Resolved'; }).length;
  var pending  = total - resolved;

  var t = document.getElementById('cd_total');
  var p = document.getElementById('cd_pending');
  var r = document.getElementById('cd_resolved');
  if (t) t.textContent = total;
  if (p) p.textContent = pending;
  if (r) r.textContent = resolved;
}

// -- TRACK COMPLAINT --
function cdTrackComplaint() {
  var query  = document.getElementById('cd_track_input').value.trim().toUpperCase();
  var result = document.getElementById('cd_track_result');
  if (!result) return;

  if (!query) {
    result.innerHTML = '<p class="cd-empty">Please enter a Complaint ID or Mobile Number.</p>';
    result.style.display = 'block';
    return;
  }

  var list = JSON.parse(localStorage.getItem('dse_complaints') || '[]');
  var found = list.filter(function(c) {
    return c.id.toUpperCase().includes(query) || c.mobile.includes(query);
  });

  if (found.length === 0) {
    result.innerHTML = '<p class="cd-empty">❌ No complaint found for: <strong>' + query + '</strong><br>Please check the ID or mobile number and try again.</p>';
    result.style.display = 'block';
    return;
  }

  result.innerHTML = found.map(function(c) {
    var badgeClass = c.status === 'Resolved' ? 'cd-badge-resolved' : 'cd-badge-pending';
    var tl3Class   = c.status === 'Resolved' ? 'cd-tl-done' : 'cd-tl-wait';
    var tl3Text    = c.status === 'Resolved' ? '✅ Resolved & Closed' : '⏳ Awaiting Assignment to Officer';
    return '<div class="cd-card" style="border-left:4px solid var(--gold);">' +
      '<div class="cd-card-top">' +
        '<span class="cd-cid">' + c.id + '</span>' +
        '<span class="cd-badge ' + badgeClass + '">' + c.status + '</span>' +
      '</div>' +
      '<div class="cd-card-type">' + c.cat + '</div>' +
      '<div class="cd-card-desc">' + c.desc + '</div>' +
      '<div class="cd-meta-grid">' +
        '<div><b>Name</b><br>' + c.name + '</div>' +
        '<div><b>District</b><br>' + c.dist + '</div>' +
        '<div><b>Mobile</b><br>' + c.mobile + '</div>' +
        '<div><b>Filed On</b><br>' + c.date + '</div>' +
        '<div><b>Status</b><br>' + c.status + '</div>' +
        '<div><b>School</b><br>' + (c.school || '—') + '</div>' +
      '</div>' +
      '<div class="cd-timeline">' +
        '<div class="cd-tl-item cd-tl-done"><div class="cd-tl-dot"></div>Complaint Registered — ' + c.date + '</div>' +
        '<div class="cd-tl-item cd-tl-done"><div class="cd-tl-dot"></div>Acknowledged by District Education Office</div>' +
        '<div class="cd-tl-item ' + tl3Class + '"><div class="cd-tl-dot"></div>' + tl3Text + '</div>' +
      '</div>' +
    '</div>';
  }).join('');
  result.style.display = 'block';
}

// -- ESC to close --
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var overlay = document.getElementById('cdOverlay');
    if (overlay && overlay.classList.contains('show')) closeComplaintDashboard();
  }
});