/* EduMentor – main.js */

// ─── Sidebar Toggle ───────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', function(e) {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  if (sidebar && hamburger &&
      !sidebar.contains(e.target) &&
      !hamburger.contains(e.target) &&
      window.innerWidth <= 768) {
    sidebar.classList.remove('open');
  }
});

// ─── Toast Notification ───────────────
function showToast(message, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ─── Tab navigation helper ─────────────
function switchTab(tab) {
  const loginForm   = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginTab    = document.getElementById('loginTab');
  const registerTab = document.getElementById('registerTab');
  if (loginForm)    loginForm.classList.toggle('hidden',    tab !== 'login');
  if (registerForm) registerForm.classList.toggle('hidden', tab !== 'register');
  if (loginTab)    loginTab.classList.toggle('active',    tab === 'login');
  if (registerTab) registerTab.classList.toggle('active', tab === 'register');
}

// ─── Keyboard shortcuts ────────────────
document.addEventListener('keydown', function(e) {
  // Tab key in code editor inserts spaces
  const editor = document.getElementById('codeEditor');
  if (editor && document.activeElement === editor && e.key === 'Tab') {
    e.preventDefault();
    const start = editor.selectionStart;
    const end   = editor.selectionEnd;
    editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
    editor.selectionStart = editor.selectionEnd = start + 4;
  }
});

// ─── Animate stat cards on page load ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.stat-card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.07}s`;
    card.classList.add('fade-in');
  });
  document.querySelectorAll('.card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.04}s`;
    card.classList.add('fade-in');
  });
});
