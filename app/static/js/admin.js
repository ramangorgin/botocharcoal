// Admin Panel JavaScript

// Preloader
window.addEventListener('load', function() {
    const preloader = document.getElementById('adminPreloader');
    const publicPreloader = document.getElementById('preloader');
    const el = preloader || publicPreloader;
    if (el) {
        el.classList.add('admin-preloader--hidden');
        setTimeout(() => {
            el.remove();
        }, 500);
    }
});

// Sidebar Toggle (Mobile)
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('adminSidebar');

if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('admin-sidebar--open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 1024) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('admin-sidebar--open');
            }
        }
    });
}

// Persian Toast Notifications
function showPersianToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
        error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
        warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`
    };

    const toast = document.createElement('div');
    toast.className = `admin-toast admin-toast--${type} admin-fade-in`;
    toast.innerHTML = `
        <div class="admin-toast__icon">${icons[type] || icons.info}</div>
        <div class="admin-toast__content">
            <div class="admin-toast__message">${message}</div>
        </div>
        <button class="admin-toast__close" type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;

    const closeBtn = toast.querySelector('.admin-toast__close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Auto-dismiss alerts on login page
document.addEventListener('DOMContentLoaded', function() {
    const errorAlerts = document.querySelectorAll('.admin-login-card__error');
    errorAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Password toggle
    const passwordInput = document.getElementById('password');
    const passwordToggle = document.getElementById('passwordToggle');
    
    if (passwordInput && passwordToggle) {
        passwordToggle.addEventListener('click', function() {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                this.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
            } else {
                passwordInput.type = 'password';
                this.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
            }
        });
    }
});

// SweetAlert2 Confirmation Helpers
async function confirmDelete(title = 'حذف', message = 'آیا مطمئن هستید؟') {
    const result = await Swal.fire({
        title: title,
        text: message,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc2626',
        cancelButtonColor: '#6b7280',
        confirmButtonText: 'بله، حذف شود',
        cancelButtonText: 'لغو'
    });
    return result.isConfirmed;
}

async function confirmAction(title = 'تایید', message = 'آیا مطمئن هستید؟') {
    const result = await Swal.fire({
        title: title,
        text: message,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#E65100',
        cancelButtonColor: '#6b7280',
        confirmButtonText: 'بله، انجام شود',
        cancelButtonText: 'لغو'
    });
    return result.isConfirmed;
}

// Auto-slug generation
const titleInput = document.getElementById('title');
const slugInput = document.getElementById('slug');

if (titleInput && slugInput && !slugInput.value) {
    titleInput.addEventListener('input', function() {
        if (!slugInput.value) {
            slugInput.value = this.value
                .toLowerCase()
                .replace(/[^\w\s\u200D\u0600-\u06FF]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();
        }
    });
}

// Form Validation
const forms = document.querySelectorAll('form[data-validate]');
forms.forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.style.borderColor = '#EF4444';
                
                if (!field.nextElementSibling?.classList.contains('admin-form-error')) {
                    const error = document.createElement('small');
                    error.className = 'admin-form-error';
                    error.style.color = '#EF4444';
                    error.style.fontSize = '0.75rem';
                    error.textContent = 'این فیلد الزامی است';
                    field.parentNode.appendChild(error);
                }
            } else {
                field.style.borderColor = '';
                const error = field.nextElementSibling?.classList?.contains('admin-form-error');
                if (error && field.nextElementSibling) {
                    field.nextElementSibling.remove();
                }
            }
        });

        if (!isValid) {
            e.preventDefault();
            showPersianToast('لطفاً تمام فیلدهای الزامی را پر کنید', 'warning');
        }
    });
});

// Confirm before leaving form with unsaved changes
let formChanged = false;
const postForm = document.getElementById('postForm');
if (postForm) {
    postForm.addEventListener('input', () => {
        formChanged = true;
    });

    window.addEventListener('beforeunload', function(e) {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    postForm.addEventListener('submit', () => {
        formChanged = false;
    });
}

// Table row hover effects
const tableRows = document.querySelectorAll('.admin-table__row');
tableRows.forEach(row => {
    row.addEventListener('mouseenter', function() {
        this.style.backgroundColor = 'var(--color-charcoal-light)';
    });
    row.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '';
    });
});

// Auto-dismiss toasts after timeout
document.addEventListener('click', function(e) {
    if (e.target.closest('.admin-toast__close')) {
        const toast = e.target.closest('.admin-toast');
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-100%)';
        setTimeout(() => toast.remove(), 300);
    }
});

// Persian number converter
function toPersianNum(num) {
    const persianDigits = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
    return String(num).replace(/[0-9]/g, d => persianDigits[parseInt(d)]);
}

// Convert all numbers in dashboard stats to Persian
document.addEventListener('DOMContentLoaded', function() {
    // Convert stat card values
    document.querySelectorAll('.admin-stat-card__value').forEach(el => {
        const text = el.textContent.trim();
        if (/^\d+$/.test(text)) {
            el.textContent = toPersianNum(text);
        }
    });

    // Convert table index column numbers to Persian
    document.querySelectorAll('.admin-table__cell--number').forEach(el => {
        const text = el.textContent.trim();
        if (/^\d+$/.test(text)) {
            el.textContent = toPersianNum(text);
        }
    });
});
