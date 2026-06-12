/* Botocharcoal — Blog Detail Page Script */

// --- تبدیل اعداد به فارسی ---
function toPersian(n) {
    return String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

// --- محاسبه زمان مطالعه ---
(function() {
    try {
        var article = document.getElementById('article-body');
        if (article) {
            // Use textContent as primary (works in all browsers including JSDOM)
            var text = (article.textContent || article.innerText || '').trim();
            var words = text.length > 0 ? text.split(/\s+/).filter(function(w) { return w.length > 0; }).length : 0;
            var time = Math.max(1, Math.ceil(words / 200));
            var readTimeEl = document.getElementById('readTimeText');
            if (readTimeEl) {
                readTimeEl.textContent = toPersian(time) + ' دقیقه مطالعه';
            }
        }
    } catch (e) {
        console.warn('Reading time calculation failed:', e);
    }
})();

// --- تولید فهرست مطالب ---
(function() {
    try {
        var article = document.getElementById('article-body');
        var tocList = document.getElementById('tocList');
        if (article && tocList) {
            var headings = article.querySelectorAll('h2, h3');
            if (headings.length > 0) {
                for (var i = 0; i < headings.length; i++) {
                    var h = headings[i];
                    h.id = 'heading-' + i;
                    var li = document.createElement('li');
                    li.className = h.tagName === 'H3' ? 'toc-subitem' : 'toc-item';
                    var headingText = h.textContent || h.innerText || 'بدون عنوان';
                    li.textContent = headingText;
                    var a = document.createElement('a');
                    a.href = '#heading-' + i;
                    a.textContent = headingText;
                    li.innerHTML = '';
                    li.appendChild(a);
                    tocList.appendChild(li);
                }

                // اسکرول نرم TOC
                tocList.addEventListener('click', function (e) {
                    var a = e.target.closest('a');
                    if (!a) return;
                    e.preventDefault();
                    var target = document.querySelector(a.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            }
        }
    } catch (e) {
        console.warn('TOC generation failed:', e);
    }
})();

// --- نوار پیشرفت مطالعه ---
(function() {
    try {
        var bar = document.getElementById('progressBar');
        if (bar) {
            window.addEventListener('scroll', function () {
                var scrolled = document.documentElement.scrollTop;
                var total = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                if (total > 0) {
                    bar.style.width = (scrolled / total * 100) + '%';
                }
            });
        }
    } catch (e) {
        console.warn('Progress bar failed:', e);
    }
})();
