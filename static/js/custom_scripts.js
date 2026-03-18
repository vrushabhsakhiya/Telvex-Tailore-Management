/* Global Custom Scripts for Table Actions */
/* Handles Modals, Sidebar Profiles, and Form Logic */

// --- 1. Modal / Sidebar Toggle ---
function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    // Check if it's a Sidebar (has .sidebar-panel)
    const panel = modal.querySelector('.sidebar-panel');

    if (panel) {
        // Sidebar Logic
        if (!modal.classList.contains('active')) {
            modal.style.display = 'flex';

            // Check if opening Add Customer Modal - Reset it
            if (modalId === 'addCustomerModal' && !window.isEditing) {
                const form = modal.querySelector('form');
                if (form) form.reset();
                const idInput = document.getElementById('custIdInput');
                if (idInput) idInput.value = '';
                const title = document.getElementById('customerModalTitle');
                if (title) title.innerText = 'Add New Customer';
                const preview = document.getElementById('imagePreview');
                if (preview) {
                    preview.style.backgroundImage = 'none';
                    preview.innerHTML = '<i class="fa-solid fa-camera" style="font-size: 1.5rem; color: var(--text-secondary);"></i>';
                }
            }
            window.isEditing = false; // Reset flag

            // Small timeout to allow display:flex to apply before transition
            setTimeout(() => {
                modal.classList.add('active');
                document.body.style.overflow = 'hidden'; // Lock Body
            }, 10);
        } else {
            modal.classList.remove('active');
            document.body.style.overflow = 'auto'; // Unlock Body
            // Wait for transition to finish before hiding
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    } else {
        // Simple Modal Logic
        modal.classList.toggle('active');
    }
}


// --- 2. Customer Profile Logic (customers.html) ---
function openProfile(id) {
    toggleModal('profileSidebar');

    // Reset UI
    const nameEl = document.getElementById('profileName');
    const listEl = document.getElementById('measurementsList');
    if (nameEl) nameEl.innerText = "Loading...";
    if (listEl) listEl.innerHTML = '<p>Loading...</p>';

    // Fetch Data
    fetch('/customers/api/profile/' + id + '/')
        .then(response => response.json())
        .then(data => {
            window.currentCustomerData = data;
            if (document.getElementById('profileName')) {
                document.getElementById('profileName').innerText = data.name;
                document.getElementById('profileMobile').innerText = data.mobile + " (" + data.gender + ")";
                document.getElementById('profilePending').innerText = '₹' + data.total_pending;
                document.getElementById('profileOrdersCount').innerText = data.total_orders;
                const newMeasBtn = document.getElementById('profileNewMeasBtn');
                if (newMeasBtn) {
                    newMeasBtn.onclick = () => {
                        console.log("Navigating to Add Measurement: " + data.id);
                        window.location.href = "/measurement/add/" + data.id + "/";
                    };
                } else {
                    console.error("New Measurement Button not found in DOM");
                }

                // Profile Image
                // Profile Image / Placeholder Logic
                const imgEl = document.getElementById('profileImage');
                const placeholderEl = document.getElementById('profilePlaceholder');
                const genderIcon = document.getElementById('profileGenderIcon');

                if (imgEl && placeholderEl) {
                    if (data.photo) {
                        imgEl.src = data.photo.startsWith('http') || data.photo.startsWith('/') ? data.photo : "/static/" + data.photo;
                        imgEl.style.display = 'block';
                        placeholderEl.style.display = 'none';
                    } else {
                        imgEl.style.display = 'none';
                        placeholderEl.style.display = 'flex';

                        // Set Gender Styles
                        if (data.gender === 'female') {
                            placeholderEl.style.background = '#EC4899'; // Pink
                            if (genderIcon) genderIcon.className = 'fa-solid fa-person-dress';
                        } else {
                            placeholderEl.style.background = '#3B82F6'; // Blue
                            if (genderIcon) genderIcon.className = 'fa-solid fa-person';
                        }
                    }
                }
            }

            // Render Measurements
            const list = document.getElementById('measurementsList');
            if (list) {
                list.innerHTML = '';
                if (data.measurements.length === 0) {
                    list.innerHTML = '<p>No measurements saved yet.</p>';
                } else {
                    data.measurements.forEach(m => {
                        const item = document.createElement('div');
                        item.className = 'card';
                        item.style.padding = '1rem';
                        item.style.border = '1px solid var(--border-color)';

                        // Parse JSON data for display format
                        let measText = '';
                        if (typeof m.data === 'object' && m.data !== null) {
                            measText += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">';
                            for (let [key, val] of Object.entries(m.data)) {
                                measText += `
                                    <div style="background: var(--bg-color); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color); text-align: center; display: flex; flex-direction: column; justify-content: center; height: 100%;">
                                        <div style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">${key}</div>
                                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">${val}</div>
                                    </div>
                                `;
                            }
                            measText += '</div>';
                        } else {
                            measText = `<div style="padding: 0.75rem; background: var(--bg-color); border-radius: 6px;">${JSON.stringify(m.data)}</div>`;
                        }

                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem;">
                                <h5 style="font-weight: 700; font-size: 1.1rem; color: var(--primary-color); margin: 0; text-transform: capitalize;">
                                    <i class="fa-solid fa-scissors" style="margin-right: 0.5rem;"></i> ${m.category}
                                </h5>
                                <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); background: var(--bg-color); padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border-color);">${m.date}</span>
                            </div>
                            
                            <div style="margin-bottom: 1.2rem;">${measText}</div>
                            
                            ${m.remarks ? `
                                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.2rem; background: var(--bg-color); padding: 0.75rem 1rem; border-radius: 8px; border-left: 4px solid var(--warning-color); font-style: italic;">
                                    <i class="fa-solid fa-quote-left" style="margin-right: 8px; opacity: 0.5;"></i> ${m.remarks}
                                </div>` : ''}
                            
                            <div style="display: flex; gap: 0.75rem;">
                                <button type="button" class="btn btn-primary" 
                                    onclick="window.location.href='/measurement/add/${data.id}/?reuse_id=${m.id}'" 
                                    style="flex: 1; justify-content: center; padding: 0.8rem; font-size: 0.95rem; font-weight: 700; border-radius: 10px; gap: 0.6rem;">
                                    <i class="fa-solid fa-rotate-right"></i> Reuse Latest
                                </button>
                                <button type="button" class="btn btn-outline"
                                    onclick="deleteMeasurement('${m.id}', '${id}')"
                                    style="border: 1px solid rgba(239, 68, 68, 0.2); background: rgba(239, 68, 68, 0.05); color: #ef4444; width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; border-radius: 10px;"
                                    title="Delete Measurement">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </div>
                        `;
                        list.appendChild(item);
                    });
                }
            }
        })
        .catch(err => {
            console.error(err);
            if (listEl) listEl.innerHTML = '<p style="color: red;">Error loading profile.</p>';
        });
}


// --- 3. Order Management Logic (orders.html) ---
function openManageModal(id, status, total, advance, mode, start, delivery, creator, customerName, itemsText) {
    if (!document.getElementById('manage_order_id')) return;

    document.getElementById('manage_order_id').value = id;
    document.getElementById('manage_status').value = status;
    document.getElementById('manage_total').value = total == 'None' ? 0 : total;
    document.getElementById('manage_advance').value = advance == 'None' ? 0 : advance;
    document.getElementById('manage_mode').value = mode == 'None' ? '' : mode;

    // Info Display (New)
    if (document.getElementById('manage_info_customer')) {
        document.getElementById('manage_info_customer').innerText = customerName || 'Unknown';
        document.getElementById('manage_info_items').innerText = itemsText || 'No items';
    }

    // Dates & Creator (Hidden or Readonly now per user request, but keeping values populated)
    const startDateEl = document.getElementById('manage_start_date');
    if (startDateEl) startDateEl.value = start == 'None' ? '' : start;

    // Set Creator
    const creatorEl = document.getElementById('manage_created_by');
    if (creatorEl) creatorEl.value = creator == 'None' ? '' : creator;

    document.getElementById('manage_delivery_date').value = delivery == 'None' ? '' : delivery;

    // Set Min Delivery Date to Today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('manage_delivery_date').min = today;

    updateBalanceDisplay();
    toggleModal('manageModal');
}

function addFullPayment() {
    const total = parseFloat(document.getElementById('manage_total').value) || 0;
    if (total > 0) {
        document.getElementById('manage_advance').value = total;
        updateBalanceDisplay();
    }
}

function updateBalanceDisplay() {
    const totalInput = document.getElementById('manage_total');
    const advanceInput = document.getElementById('manage_advance');
    const balSpan = document.getElementById('calc_balance');

    if (!totalInput || !advanceInput || !balSpan) return;

    const total = parseFloat(totalInput.value) || 0;
    const advance = parseFloat(advanceInput.value) || 0;
    const bal = total - advance;

    balSpan.innerText = '₹' + bal;

    if (bal <= 0 && total > 0) {
        balSpan.style.color = 'var(--success-color)';
        balSpan.innerText += ' (Paid)';
    } else if (total == 0 && advance > 0) {
        balSpan.style.color = 'var(--success-color)';
        balSpan.innerText += ' (Credit)';
    } else {
        balSpan.style.color = 'var(--danger-color)';
    }
}


// --- 4. Bill Payment Logic (bills.html) ---
function openPaymentModal(id, total, advance, status, mode, start, delivery, creator, workStatus) {
    if (!document.getElementById('pay_order_id')) return;

    document.getElementById('pay_order_id').value = id;
    document.getElementById('pay_total').value = total;
    document.getElementById('pay_advance').value = advance;
    document.getElementById('pay_status').value = status;
    document.getElementById('pay_mode').value = mode == 'None' ? '' : mode;

    // Work Status (New)
    if (workStatus && document.getElementById('pay_work_status')) {
        document.getElementById('pay_work_status').value = workStatus;
    }

    // New Fields - Safe check
    const startEl = document.getElementById('pay_start_date');
    if (startEl) startEl.value = (start == 'None' || !start) ? '' : start;

    const deliveryEl = document.getElementById('pay_delivery_date');
    if (deliveryEl) deliveryEl.value = (delivery == 'None' || !delivery) ? '' : delivery;

    const creatorEl = document.getElementById('pay_created_by');
    if (creatorEl) creatorEl.value = (creator == 'None' || !creator) ? '' : creator;

    // Set Min Delivery Date
    if (deliveryEl) {
        const today = new Date().toISOString().split('T')[0];
        deliveryEl.min = today;
    }

    toggleModal('paymentModal');
}

function filterBills(status) {
    const rows = document.querySelectorAll('.bill-row');
    rows.forEach(row => {
        const rowStatus = row.getAttribute('data-status');
        if (status === 'all' || rowStatus === status) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}


// --- 5. Event Delegation for Inputs (Persist through AJAX) ---
document.addEventListener('input', (e) => {
    // Orders Balance Calculation
    if (e.target.id === 'manage_total' || e.target.id === 'manage_advance') {
        updateBalanceDisplay();
    }

    // Bills Auto Status Update
    if (e.target.id === 'pay_advance') {
        const total = parseFloat(document.getElementById('pay_total').value) || 0;
        const paid = parseFloat(e.target.value) || 0;
        const statusSelect = document.getElementById('pay_status');

        if (statusSelect) {
            if (paid >= total && total > 0) {
                statusSelect.value = 'Paid';
            } else if (paid > 0) {
                statusSelect.value = 'Half-Payment';
            } else {
                statusSelect.value = 'Pending';
            }
        }
    }
});

function deleteMeasurement(measureId, customerId) {
    if (!confirm('Are you sure you want to delete this measurement? This cannot be undone.')) return;

    // Get CSRF Token
    const csrfToken = window.CSRF_TOKEN || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;

    if (!csrfToken) {
        alert("Security Token missing. Please refresh the page.");
        return;
    }

    fetch(`/measurement/delete/${measureId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Refresh Profile
                openProfile(customerId);
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(err => {
            console.error(err);
            alert('An error occurred.');
        });
}

// Consolidated Edit Function (Handles both Table and Sidebar clicks)
function editCurrentCustomer(id, name, mobile, gender, city, area, notes, photo) {
    let data = {};
    if (id && typeof id !== 'undefined' && typeof name !== 'undefined') {
        // Called from Table with args
        data = { id, name, mobile, gender, city, area, notes, photo };
    } else if (window.currentCustomerData) {
        // Called from Sidebar without args
        data = window.currentCustomerData;
    } else {
        return;
    }

    window.isEditing = true; // Use flag to prevent reset in toggleModal

    // Fill Form matches names in customers.html
    // Inputs: name, mobile, city, area, notes, gender
    const modal = document.getElementById('addCustomerModal');
    const form = modal.querySelector('form');

    if (form) {
        const nameInput = form.querySelector('input[name="name"]');
        if (nameInput) nameInput.value = data.name;

        const mobileInput = form.querySelector('input[name="mobile"]');
        if (mobileInput) mobileInput.value = data.mobile;

        const cityInput = form.querySelector('input[name="city"]');
        if (cityInput) cityInput.value = data.city || '';

        const areaInput = form.querySelector('input[name="area"]');
        if (areaInput) areaInput.value = data.area || '';

        const notesInput = form.querySelector('textarea[name="notes"]');
        if (notesInput) notesInput.value = data.notes || '';

        const genderSelect = form.querySelector('select[name="gender"]');
        if (genderSelect) genderSelect.value = data.gender ? data.gender.toLowerCase() : 'male';

        document.getElementById('custIdInput').value = data.id;
    }

    const title = document.getElementById('customerModalTitle');
    if (title) title.innerText = 'Edit Customer';

    // Preview Image
    const preview = document.getElementById('imagePreview');
    if (preview) {
        if (data.photo) {
            preview.style.backgroundImage = 'url(' + data.photo + ')';
            preview.style.backgroundSize = 'cover';
            preview.innerHTML = '';
        } else {
            preview.style.backgroundImage = 'none';
            preview.innerHTML = '<i class="fa-solid fa-camera" style="font-size: 1.5rem; color: var(--text-secondary);"></i>';
        }
    }

    toggleModal('profileSidebar'); // Close Profile
    toggleModal('addCustomerModal'); // Open Edit
}

// Generic Delete for Table
function deleteCustomer(id) {
    if (!confirm('Are you sure you want to delete this customer?')) return;

    // Use Global CSRF if available, else fallback to DOM
    const csrfToken = window.CSRF_TOKEN || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;

    if (!csrfToken) {
        alert("Security Token missing. Please refresh the page.");
        return;
    }

    // Create form to submit POST
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/customers/delete/' + id + '/';

    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrfmiddlewaretoken';
    input.value = csrfToken;
    form.appendChild(input);

    document.body.appendChild(form);
    form.submit();
}

// Sidebar Delete
function deleteCurrentCustomer() {
    const data = window.currentCustomerData;
    if (!data) return;

    if (!confirm('Are you sure you want to delete ' + data.name + '? This will delete their orders and cannot be undone.')) return;

    const csrfToken = window.CSRF_TOKEN || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || document.querySelector('meta[name="csrf-token"]')?.content;

    if (!csrfToken) {
        alert("Security Token missing. Please refresh the page.");
        return;
    }

    // Dynamic Form Submit to use existing Delete Route
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/customers/delete/' + data.id + '/';

    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrfmiddlewaretoken';
    input.value = csrfToken;
    form.appendChild(input);

    document.body.appendChild(form);
    form.submit();
}


function openManageOrder(btn) {
    const d = btn.dataset;
    // Map data attributes to arguments of openManageModal
    // (id, status, total, advance, mode, start, delivery, creator, customerName, itemsText)
    openManageModal(d.id, d.status, d.total, d.advance, d.mode, d.start, d.delivery, d.creator, d.customer, d.items);
}

function navigateToPage(input) {
    const d = input.dataset;
    let url = `${d.baseUrl}?page=${input.value}`;
    if (d.month) url += `&month=${d.month}`;
    if (d.year) url += `&year=${d.year}`;
    if (d.q) url += `&q=${d.q}`;
    if (d.status) url += `&status=${d.status}`;
    if (d.deliveryDate) url += `&delivery_date=${d.deliveryDate}`; // dash-case to camelCase
    window.location.href = url;
}
