// =============================================
// HAMBURGER MENU TOGGLE
// =============================================
function toggleMenu() {
  const nav = document.querySelector('.h2_vertical_2');
  nav.classList.toggle('open');
}

// Bahar click karne par menu band ho jaye
document.addEventListener('click', function(e) {
  const nav = document.querySelector('.h2_vertical_2');
  const hamburger = document.getElementById('hamburger');
  if (!nav.contains(e.target) && !hamburger.contains(e.target)) {
    nav.classList.remove('open');
  }
});