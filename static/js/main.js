/* GroupSathi - Main JavaScript */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.gs-alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add animation to dashboard cards on load
    const cards = document.querySelectorAll('.gs-dash-card');
    cards.forEach(function (card, index) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(function () {
            card.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 60);
    });

    // File input preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function (input) {
        input.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                const previewId = input.getAttribute('data-preview');
                if (previewId) {
                    reader.onload = function (ev) {
                        const preview = document.getElementById(previewId);
                        if (preview) {
                            preview.src = ev.target.result;
                            preview.style.display = 'block';
                        }
                    };
                    reader.readAsDataURL(file);
                }
            }
        });
    });

    // Calculator tab switching
    const calcTabs = document.querySelectorAll('.gs-calc-tab');
    const calcForms = document.querySelectorAll('.gs-calc-form');
    calcTabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            calcTabs.forEach(function (t) { t.classList.remove('active'); });
            calcForms.forEach(function (f) { f.style.display = 'none'; });
            tab.classList.add('active');
            const target = document.getElementById(tab.getAttribute('data-target'));
            if (target) target.style.display = 'block';
        });
    });

    // Number-only input enforcement
    const numInputs = document.querySelectorAll('input[data-numeric]');
    numInputs.forEach(function (input) {
        input.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    });

    // Confirm actions with SweetAlert2
    const confirmBtns = document.querySelectorAll('[data-confirm]');
    confirmBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const message   = this.getAttribute('data-confirm');
            const icon      = this.getAttribute('data-confirm-icon') || 'warning';
            const targetUrl = this.getAttribute('href');
            const self      = this;

            if (typeof Swal !== 'undefined') {
                const confirmColor = (icon === 'error') ? '#E17055' : '#6C5CE7';
                const titles = { warning: 'Confirm Action', error: 'Confirm Deletion', info: 'Confirm', question: 'Are you sure?', success: 'Confirm' };

                Swal.fire({
                    title              : titles[icon] || 'Confirm Action',
                    text               : message,
                    icon               : icon,
                    showCancelButton   : true,
                    confirmButtonColor : confirmColor,
                    cancelButtonColor  : '#636e72',
                    confirmButtonText  : 'Yes, proceed',
                    cancelButtonText   : 'Cancel',
                    backdrop           : 'rgba(15,23,42,0.6)'
                }).then((result) => {
                    if (result.isConfirmed) {
                        if (targetUrl && targetUrl !== '#') {
                            window.location.href = targetUrl;
                        } else if (self.closest('form')) {
                            self.closest('form').submit();
                        }
                    }
                });
            } else {
                if (confirm(message)) {
                    if (targetUrl && targetUrl !== '#') {
                        window.location.href = targetUrl;
                    } else if (this.closest('form')) {
                        this.closest('form').submit();
                    }
                }
            }
        });
    });
});
