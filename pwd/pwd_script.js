// ===== SLIDER =====
let current = 0;
const total = 5;
const track = document.getElementById('sliderTrack');
const dots = document.querySelectorAll('.dot');

function goTo(index) {
  current = (index + total) % total;
  track.style.transform = `translateX(-${current * 100}%)`;
  dots.forEach((d, i) => d.classList.toggle('active', i === current));
}

document.getElementById('prevBtn').onclick = () => goTo(current - 1);
document.getElementById('nextBtn').onclick = () => goTo(current + 1);

// Auto-advance every 4.5 seconds
setInterval(() => goTo(current + 1), 4500);


// ===== TABS =====
function switchTab(btn, tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}