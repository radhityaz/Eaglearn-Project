// Clean Dashboard - Minimal JavaScript
console.log('Dashboard loaded - Clean design mode');

// Simple navigation handler
document.addEventListener('DOMContentLoaded', function() {
  const navItems = document.querySelectorAll('.nav-item');
  
  navItems.forEach(item => {
    item.addEventListener('click', function() {
      navItems.forEach(nav => nav.classList.remove('active'));
      this.classList.add('active');
      console.log('Navigation clicked:', this.textContent.trim());
    });
  });
  
  // Badge toggle handlers
  const badges = document.querySelectorAll('.badge');
  badges.forEach(badge => {
    badge.addEventListener('click', function() {
      const container = this.parentElement;
      const badges = container.querySelectorAll('.badge');
      badges.forEach(b => {
        b.classList.remove('badge-primary');
        b.classList.add('badge-default');
      });
      this.classList.remove('badge-default');
      this.classList.add('badge-primary');
      console.log('Filter selected:', this.textContent.trim());
    });
  });
});
