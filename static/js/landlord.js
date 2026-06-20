/* ─── Utilities ─── */
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = 'toast'; }, 3800);
}

function setLoading(btn, on) {
  btn.classList.toggle('loading', on);
  btn.disabled = on;
}

function showError(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('visible');
}

function clearErrors() {
  document.querySelectorAll('.field-error').forEach(e => e.classList.remove('visible'));
}

/* ─── Formatters ─── */
function fmtEur(val) {
  if (val == null) return '—';
  return '€' + Number(val).toLocaleString('nl-NL', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtTerm(months) {
  if (!months) return '—';
  const map = { 6: '6 months', 12: '12 months (1 yr)', 18: '18 months', 24: '24 months (2 yrs)' };
  return map[months] || months + ' months';
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
}

/* ─── Status config ─── */
const STATUS = {
  approved: { label: '✓ Approved',  cls: 'status-approved' },
  pending:  { label: '⏳ Pending',   cls: 'status-pending'  },
  rejected: { label: '✗ Rejected',  cls: 'status-rejected' },
  draft:    { label: 'Draft',        cls: 'status-draft'    },
};

/* ─── Parse reference (accept "DE-000001" or "1") ─── */
function parseRef(raw) {
  const stripped = raw.trim().toUpperCase().replace(/^DE-?0*/, '');
  const num = parseInt(stripped, 10);
  return isNaN(num) ? null : num;
}

/* ─── Render guarantee card ─── */
function showProfile(data) {
  document.getElementById('lookup-card').classList.add('hidden');
  const card = document.getElementById('profile-card');
  card.classList.remove('hidden');

  /* Status banner */
  document.getElementById('banner-approved').style.display = data.status === 'approved' ? 'flex' : 'none';
  document.getElementById('banner-pending').classList.toggle('hidden',  data.status !== 'pending');
  document.getElementById('banner-rejected').classList.toggle('hidden', data.status !== 'rejected');

  /* Reference + badge */
  document.getElementById('profile-ref').textContent = data.reference;
  const cfg   = STATUS[data.status] || STATUS.draft;
  const badge = document.getElementById('status-badge');
  badge.textContent = cfg.label;
  badge.className   = 'status-badge ' + cfg.cls;

  /* Tenant */
  document.getElementById('profile-tenant').textContent = data.tenant_first_name || 'Tenant';

  /* Property */
  const hasAddress = data.rental_address;
  document.getElementById('section-property').classList.toggle('hidden', !hasAddress);
  if (hasAddress) {
    document.getElementById('profile-address').textContent = data.rental_address;
    document.getElementById('profile-postal').textContent  = data.rental_postal_code || '';
  }

  /* Guarantee stats */
  document.getElementById('stat-deposit').textContent  = fmtEur(data.deposit_amount);
  document.getElementById('stat-term').textContent     = fmtTerm(data.repayment_months);
  document.getElementById('stat-monthly').textContent  = data.monthly_repayment ? fmtEur(data.monthly_repayment) : '—';
  document.getElementById('stat-date').textContent     = fmtDate(data.created_at);
}

function resetLookup() {
  document.getElementById('profile-card').classList.add('hidden');
  document.getElementById('lookup-card').classList.remove('hidden');
}

/* ─── Lookup submit ─── */
document.getElementById('form-lookup').addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const raw = document.getElementById('lookup-ref').value;
  const id  = parseRef(raw);
  if (!id) { showError('err-lookup-ref'); return; }

  const btn = document.getElementById('btn-lookup');
  setLoading(btn, true);

  try {
    const res  = await fetch('/api/v1/profile/landlord/' + id);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Application not found.');
    showProfile(data);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

/* Auto-uppercase and format as user types */
document.getElementById('lookup-ref').addEventListener('input', function () {
  const digits = this.value.replace(/[^0-9]/g, '');
  if (digits.length > 0) {
    this.value = 'DE-' + digits.slice(0, 6).padStart(6, '0');
  }
});
