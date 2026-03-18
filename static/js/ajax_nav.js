// AJAX Navigation Script
// Handles smooth transitions for Filters, Pagination, and Month Navigation

document.addEventListener('DOMContentLoaded', () => {
    // Top Loading Bar
    const loadingBar = document.createElement('div');
    loadingBar.id = 'ajax-loading-bar';
    loadingBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        width: 0%;
        background: var(--primary-color, #4f46e5);
        z-index: 9999;
        transition: width 0.3s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    `;
    document.body.appendChild(loadingBar);

    function showLoading() {
        loadingBar.style.width = '30%';
        loadingBar.style.opacity = '1';
    }

    function finishLoading() {
        loadingBar.style.width = '100%';
        setTimeout(() => {
            loadingBar.style.opacity = '0';
            setTimeout(() => {
                loadingBar.style.width = '0%';
            }, 300);
        }, 300);
    }

    // Smart Cache
    const pageCache = new Map();

    function updateContent(doc, url) {
        // Containers to update
        const selectors = [
            '.content-wrapper', // Main content area
            // Fallbacks
            '.table-container',
            '.month-nav',
            '.filter-bar',
            '.pagination-container'
        ];

        // Specific handling for main wrapper
        const newMain = doc.querySelector('.content-wrapper');
        const oldMain = document.querySelector('.content-wrapper');

        let updated = false;

        if (newMain && oldMain) {
            // Optimization: Only update if content is different
            if (oldMain.innerHTML !== newMain.innerHTML) {
                oldMain.innerHTML = newMain.innerHTML;
                updated = true;
            }
        } else {
            // Fallback
            selectors.forEach(selector => {
                if (selector === '.content-wrapper') return;
                const newContent = doc.querySelector(selector);
                const oldContent = document.querySelector(selector);

                if (newContent && oldContent) {
                    if (oldContent.innerHTML !== newContent.innerHTML) {
                        oldContent.innerHTML = newContent.innerHTML;
                        updated = true;
                    }
                }
            });
        }

        // Execute Scripts found in the new content
        // We do this after all DOM updates
        const scripts = doc.querySelectorAll('script');
        scripts.forEach(oldScript => {
            // Check if this script is inside one of our updated containers
            // For simplicity, we mostly care about block content scripts
            // But checking parenthood in a parsed doc vs live doc is tricky.
            // Let's assume user puts page-specific scripts in {% block content %} which is inside content-wrapper.
            // We just execute NON-SRC scripts (inline) that contain specific keywords or all of them?
            // Executing global scripts (jquery, etc) again is bad.
            // We filter for scripts that do not have 'src' attribute (inline)
            // AND are likely page specific.

            if (!oldScript.src) {
                const newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                newScript.textContent = oldScript.textContent;

                // Wrap in IIFE to avoid 'Identifier has already been declared' for let/const
                // But we need to expose functions.
                // Best strategy: Just run it. If template uses 'let' globally, it needs to be fixed in template.
                document.body.appendChild(newScript);
                document.body.removeChild(newScript);
            }
        });

        // Re-execute standard scripts or update active states
        updateActiveSidebarState(url);

        return updated;
    }

    function updateActiveSidebarState(url) {
        let path;
        if (url) {
            try {
                // Handle both absolute and relative URLs
                path = new URL(url, window.location.origin).pathname;
            } catch (e) {
                path = window.location.pathname;
            }
        } else {
            path = window.location.pathname;
        }
        const links = document.querySelectorAll('.sidebar-nav .nav-item');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href === path || (href !== '/' && path.startsWith(href))) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    // Main Update Function
    async function fetchAndUpdate(url, pushState = true) {
        // 1. Check Cache (Instant Load)
        const cachedDoc = pageCache.get(url);
        if (cachedDoc) {
            updateContent(cachedDoc, url);
            if (pushState) window.history.pushState({}, '', url);
            // Don't return! Continue to background fetch (revalidate) to ensure data is fresh.
            // We skip 'showLoading()' to make it feel instant.
        } else {
            showLoading(); // Only show bar if not in cache
        }

        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const html = await response.text();

            // Parse HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Save to Cache
            pageCache.set(url, doc);

            // Update DOM (if new data differs)
            updateContent(doc, url);

            // Update URL if we haven't done it yet (uncached case)
            if (pushState && !cachedDoc) {
                window.history.pushState({}, '', url);
            }

        } catch (error) {
            console.error('AJAX Nav Error:', error);
            // Fallback to full reload if we had no cache and network failed
            if (!cachedDoc) window.location.href = url;
        } finally {
            finishLoading();
        }
    }

    // Event Delegation
    document.body.addEventListener('click', (e) => {
        // Find closest anchor tag
        const link = e.target.closest('a');
        if (!link) return;

        // Check if it's a target for AJAX
        // 1. Pagination links
        // 2. Month Nav links
        // 3. Filter reset links
        // 4. Sidebar links
        if (
            link.closest('.pagination') ||
            link.closest('.month-nav') ||
            link.closest('.sidebar-nav') ||
            (link.closest('.filter-bar') && link.classList.contains('btn-outline'))
        ) {
            // Check if same origin and not a hash link
            if (link.origin === window.location.origin && !link.href.includes('#')) {
                e.preventDefault();
                fetchAndUpdate(link.href);
            }
        }
    });

    // Delegated Form Submit for Filter Bar
    document.body.addEventListener('submit', (e) => {
        const form = e.target.closest('form.filter-bar') || e.target.closest('form');
        if (form) {
            // If it's a GET search, utilize AJAX
            if (form.method.toUpperCase() === 'GET' && form.classList.contains('filter-bar')) {
                e.preventDefault();
                const url = new URL(form.action);
                const formData = new FormData(form);
                const params = new URLSearchParams(formData);

                // Merge existing params if needed
                url.search = params.toString();

                // Invalidate cache for this search results
                // pageCache.delete(url.toString());

                fetchAndUpdate(url.toString());
            } else {
                // If it's a POST (Add/Edit) or non-filter GET, just clear cache to keep things fresh
                pageCache.clear();
            }
        }
    });

    // Also handle 'change' events on selects in the filter bar (auto-submit)
    document.body.addEventListener('change', (e) => {
        const select = e.target.closest('form.filter-bar select');
        const inputDate = e.target.closest('form.filter-bar input[type="date"]');

        if (select || inputDate) {
            const form = (select || inputDate).form;
            if (form) {
                // Trigger the submit handler above
                form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            }
        }
    });

    // Handle Back Button
    window.addEventListener('popstate', () => {
        fetchAndUpdate(window.location.href, false);
    });
});
