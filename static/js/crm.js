/**
 * Novem Controls CRM — Main JavaScript
 * Handles sidebar, attendance, notifications, call timer, location tracking.
 */

'use strict';

// ── CSRF Helper ─────────────────────────────────────────────────────────────
function getCookie(name) {
  const val = `; ${document.cookie}`;
  const parts = val.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

function csrfPost(url, data, callback, errorCallback) {
  const formData = new FormData();
  for (const key in data) formData.append(key, data[key]);
  fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: formData,
  })
  .then(r => r.json())
  .then(callback)
  .catch(errorCallback || (e => console.error(e)));
}

// ── Sidebar ─────────────────────────────────────────────────────────────────
(function() {
  const sidebar  = document.getElementById('sidebar');
  const toggle   = document.getElementById('sidebarToggle');
  const close    = document.getElementById('sidebarClose');
  const overlay  = document.getElementById('sidebarOverlay');
  const wrapper  = document.getElementById('mainWrapper');
  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('show');
    overlay.classList.add('show');
  }
  function closeSidebar() {
    sidebar.classList.remove('show');
    overlay.classList.remove('show');
  }

  if (toggle) toggle.addEventListener('click', () => {
    if (window.innerWidth >= 992) {
      // Desktop collapse
      const collapsed = sidebar.style.width === '70px';
      sidebar.style.width = collapsed ? 'var(--sidebar-width)' : '70px';
      wrapper.style.marginLeft = collapsed ? 'var(--sidebar-width)' : '70px';
      sidebar.querySelectorAll('.brand-wordmark, .brand-text, .user-info, .nav-section-label, .nav-item span, .sidebar-footer .nav-item span')
        .forEach(el => el.style.display = collapsed ? '' : 'none');
    } else {
      openSidebar();
    }
  });
  if (close)   close.addEventListener('click', closeSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);
})();

// ── Toast notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const icons = { success: 'bi-check-circle-fill', error: 'bi-exclamation-circle-fill',
                  warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#06b6d4' };
  const id = 'toast_' + Date.now();
  const html = `
    <div id="${id}" class="toast crm-toast show align-items-center" role="alert">
      <div class="d-flex align-items-center p-2">
        <i class="bi ${icons[type] || icons.info} me-2" style="color:${colors[type]||colors.info};font-size:16px"></i>
        <div class="toast-body p-0 flex-grow-1" style="color:#f8fafc;font-size:13.5px">${message}</div>
        <button type="button" class="btn-close btn-close-white ms-2" onclick="document.getElementById('${id}').remove()"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
  setTimeout(() => { const t = document.getElementById(id); if (t) t.remove(); }, 5000);
}

// ── Attendance Widget ────────────────────────────────────────────────────────
(function() {
  const statusEl   = document.getElementById('attStatus');
  const checkInBtn = document.getElementById('checkInBtn');
  const checkOutBtn= document.getElementById('checkOutBtn');
  if (!checkInBtn) return;

  // Load current status
  fetch('/attendance/status/')
    .then(r => r.json())
    .then(data => {
      if (data.is_checked_in) {
        statusEl.textContent = `In since ${data.check_in_time}`;
        statusEl.style.color = '#10b981';
        checkOutBtn.style.display = '';
      } else if (data.check_out_time) {
        statusEl.textContent = `Done — ${data.working_hours}`;
        statusEl.style.color = '#64748b';
      } else {
        statusEl.textContent = 'Not checked in';
        checkInBtn.style.display = '';
      }
    })
    .catch(() => statusEl.textContent = '');

  // Get geolocation then post
  function getLocationAndPost(url, onSuccess) {
    if (!navigator.geolocation) {
      return doPost(url, {}, onSuccess);
    }
    navigator.geolocation.getCurrentPosition(
      pos => doPost(url, {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        location_name: '',
      }, onSuccess),
      () => doPost(url, {}, onSuccess),
      { timeout: 8000 }
    );
  }

  function doPost(url, data, onSuccess) {
    csrfPost(url, data, onSuccess, err => showToast('Request failed.', 'error'));
  }

  if (checkInBtn) checkInBtn.addEventListener('click', () => {
    checkInBtn.disabled = true;
    checkInBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    getLocationAndPost('/attendance/check-in/', data => {
      if (data.status === 'checked_in') {
        statusEl.textContent = `In since ${data.time}`;
        statusEl.style.color = '#10b981';
        checkInBtn.style.display = 'none';
        checkOutBtn.style.display = '';
        showToast(data.message, 'success');
      } else {
        showToast(data.error || 'Check-in failed.', 'error');
        checkInBtn.disabled = false;
        checkInBtn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Check In';
      }
    });
  });

  if (checkOutBtn) checkOutBtn.addEventListener('click', () => {
    checkOutBtn.disabled = true;
    checkOutBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    getLocationAndPost('/attendance/check-out/', data => {
      if (data.status === 'checked_out') {
        statusEl.textContent = `Done — ${data.working_hours_display}`;
        statusEl.style.color = '#64748b';
        checkOutBtn.style.display = 'none';
        showToast(data.message, 'success');
      } else {
        showToast(data.error || 'Check-out failed.', 'error');
        checkOutBtn.disabled = false;
        checkOutBtn.innerHTML = '<i class="bi bi-box-arrow-right"></i> Check Out';
      }
    });
  });
})();

// ── Mark all notifications read ──────────────────────────────────────────────
(function() {
  const btn = document.getElementById('markAllRead');
  if (!btn) return;
  btn.addEventListener('click', () => {
    csrfPost('/notifications/mark-all-read/', {}, data => {
      document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
      const badge = document.querySelector('.notif-badge');
      if (badge) badge.remove();
      btn.style.display = 'none';
    });
  });
})();

// ── Call Timer ───────────────────────────────────────────────────────────────
let callTimerInterval = null;
let callStartTime     = null;
let activeCallId      = null;

function startCallTimer(callId, startedAt) {
  activeCallId  = callId;
  callStartTime = new Date(startedAt);
  const timerEl = document.getElementById('callTimer');
  if (!timerEl) return;

  function tick() {
    const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    const parts = [];
    if (h) parts.push(String(h).padStart(2,'0') + 'h');
    parts.push(String(m).padStart(2,'0') + 'm');
    parts.push(String(s).padStart(2,'0') + 's');
    timerEl.textContent = parts.join(' ');
  }
  tick();
  callTimerInterval = setInterval(tick, 1000);
}

function stopCallTimer() {
  if (callTimerInterval) clearInterval(callTimerInterval);
  callTimerInterval = null;
}

// ── Start Call ───────────────────────────────────────────────────────────────
function startCall(leadPk) {
  const btn = document.getElementById(`startCallBtn_${leadPk}`);
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }

  csrfPost(`/calling/start/${leadPk}/`, {}, data => {
    if (data.call_id) {
      // Show call active panel
      const panel = document.getElementById('callActivePanel');
      if (panel) {
        panel.style.display = '';
        startCallTimer(data.call_id, data.started_at);
      }
      document.querySelectorAll('.pre-call-action').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.during-call-action').forEach(el => el.style.display = '');
      showToast('Call started. Log the result when finished.', 'info');
    } else {
      showToast(data.error || 'Could not start call.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-telephone-fill"></i> Start Call'; }
    }
  }, () => {
    showToast('Network error.', 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-telephone-fill"></i> Start Call'; }
  });
}

// ── End Call ─────────────────────────────────────────────────────────────────
function endCall(callId) {
  const result  = document.getElementById('callResult')?.value;
  const notes   = document.getElementById('callNotes')?.value || '';
  const followUp= document.getElementById('callFollowUpDate')?.value || '';

  if (!result) { showToast('Please select a call result.', 'warning'); return; }

  const btn = document.getElementById('endCallBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...'; }

  csrfPost(`/calling/end/${callId}/`, { result, notes, follow_up_date: followUp }, data => {
    stopCallTimer();
    showToast(`Call ended. Duration: ${data.duration}`, 'success');
    setTimeout(() => location.reload(), 1500);
  }, () => {
    showToast('Failed to save call result.', 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = 'End Call & Save'; }
  });
}

// ── Location Tracking ────────────────────────────────────────────────────────
const LocationTracker = {
  watchId: null,
  sessionId: null,
  recordInterval: null,
  RECORD_INTERVAL_MS: 60000, // record every 60 seconds

  start() {
    if (!navigator.geolocation) {
      showToast('Geolocation is not supported by your browser.', 'error'); return;
    }
    csrfPost('/locations/track/start/', {}, data => {
      if (data.session_id) {
        this.sessionId = data.session_id;
        this._startWatch();
        this._updateUI(true);
        showToast('📍 Location tracking started. Your location is being recorded.', 'info');
      }
    });
  },

  stop() {
    csrfPost('/locations/track/stop/', {}, data => {
      this._stopWatch();
      this._updateUI(false);
      showToast('Location tracking stopped.', 'info');
    });
  },

  _startWatch() {
    this.watchId = navigator.geolocation.watchPosition(
      pos => this._onPosition(pos),
      err => this._onError(err),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 }
    );
    // Record periodically even without movement
    this.recordInterval = setInterval(() => {
      navigator.geolocation.getCurrentPosition(pos => this._record(pos));
    }, this.RECORD_INTERVAL_MS);
  },

  _stopWatch() {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }
    if (this.recordInterval) {
      clearInterval(this.recordInterval);
      this.recordInterval = null;
    }
  },

  _onPosition(pos) {
    this._record(pos);
    // Update live location display if on map page
    const latEl = document.getElementById('myLat');
    const lngEl = document.getElementById('myLng');
    const accEl = document.getElementById('myAcc');
    if (latEl) latEl.textContent = pos.coords.latitude.toFixed(6);
    if (lngEl) lngEl.textContent = pos.coords.longitude.toFixed(6);
    if (accEl) accEl.textContent = (pos.coords.accuracy || 0).toFixed(0) + 'm';
  },

  _record(pos) {
    csrfPost('/locations/track/record/', {
      latitude:  pos.coords.latitude,
      longitude: pos.coords.longitude,
      accuracy:  pos.coords.accuracy || '',
      altitude:  pos.coords.altitude || '',
    }, () => {});
  },

  _onError(err) {
    const msgs = {
      1: 'Location permission denied. Enable permissions to track.',
      2: 'Location unavailable. Please check your device.',
      3: 'Location request timed out.',
    };
    showToast(msgs[err.code] || 'Location error.', 'warning');
  },

  _updateUI(isActive) {
    const indicator = document.getElementById('trackingIndicator');
    const startBtn  = document.getElementById('startTrackingBtn');
    const stopBtn   = document.getElementById('stopTrackingBtn');
    if (indicator) {
      indicator.className = `tracking-indicator ${isActive ? 'active' : 'inactive'}`;
      indicator.innerHTML = `<span class="dot"></span> ${isActive ? 'Tracking Active' : 'Not Tracking'}`;
    }
    if (startBtn) startBtn.style.display = isActive ? 'none' : '';
    if (stopBtn)  stopBtn.style.display  = isActive ? '' : 'none';
  },

  init() {
    // Check current status on page load
    fetch('/locations/track/status/')
      .then(r => r.json())
      .then(data => {
        if (data.is_tracking) {
          this.sessionId = data.session_id;
          this._startWatch();
          this._updateUI(true);
        } else {
          this._updateUI(false);
        }
      })
      .catch(() => this._updateUI(false));

    // Wire buttons
    const startBtn = document.getElementById('startTrackingBtn');
    const stopBtn  = document.getElementById('stopTrackingBtn');
    if (startBtn) startBtn.addEventListener('click', () => this.start());
    if (stopBtn)  stopBtn.addEventListener('click',  () => this.stop());
  }
};

// ── Lead status update ────────────────────────────────────────────────────────
function updateLeadStatus(leadPk, newStatus) {
  const form = new FormData();
  form.append('status', newStatus);
  fetch(`/leads/${leadPk}/status/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: form,
  })
  .then(r => r.json())
  .then(data => {
    const badge = document.getElementById(`leadStatus_${leadPk}`);
    if (badge) badge.textContent = data.label;
    showToast('Status updated.', 'success');
  })
  .catch(() => showToast('Update failed.', 'error'));
}

// ── Follow-up complete ────────────────────────────────────────────────────────
function completeFollowUp(pk, notes) {
  csrfPost(`/calling/followups/${pk}/complete/`, { notes }, data => {
    const row = document.getElementById(`followup_${pk}`);
    if (row) row.remove();
    showToast('Follow-up marked as completed.', 'success');
  });
}

// ── Task status update ────────────────────────────────────────────────────────
function updateTaskStatus(taskPk, newStatus, actualHours) {
  csrfPost(`/developers/tasks/${taskPk}/status/`, { status: newStatus, actual_hours: actualHours || '' }, data => {
    showToast('Task status updated.', 'success');
    setTimeout(() => location.reload(), 800);
  });
}

// ── Auto-dismiss alerts ───────────────────────────────────────────────────────
(function() {
  document.querySelectorAll('.crm-alert').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });
})();

// ── Init on DOM ready ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  // Init location tracker if tracking buttons exist
  if (document.getElementById('startTrackingBtn') || document.getElementById('stopTrackingBtn')) {
    LocationTracker.init();
  }

  // Confirm dangerous actions
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });

  // Tooltip init
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });

  // Responsive table: add data-labels
  document.querySelectorAll('.crm-table').forEach(table => {
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
    table.querySelectorAll('tbody tr').forEach(row => {
      row.querySelectorAll('td').forEach((td, i) => {
        if (headers[i]) td.setAttribute('data-label', headers[i]);
      });
    });
  });
});
