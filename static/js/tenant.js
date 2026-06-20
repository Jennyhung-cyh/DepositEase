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

function fmtRate(val) {
  if (val == null) return '—';
  return (val * 100).toFixed(0) + '%';
}

function fmtTerm(months) {
  if (!months) return '—';
  const map = { 6: '6 months', 12: '12 months (1 yr)', 18: '18 months', 24: '24 months (2 yrs)' };
  return map[months] || months + ' months';
}

function fmtDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' });
}

/* ─── Status config ─── */
const STATUS = {
  approved: { label: '✓ Approved',  cls: 'status-approved' },
  pending:  { label: '⏳ Pending',   cls: 'status-pending'  },
  rejected: { label: '✗ Rejected',  cls: 'status-rejected' },
  draft:    { label: 'Draft',        cls: 'status-draft'    },
};

/* ─── Render profile ─── */
function showProfile(data) {
  document.getElementById('lookup-card').classList.add('hidden');
  const card = document.getElementById('profile-card');
  card.classList.remove('hidden');

  document.getElementById('profile-name').textContent = data.full_name;
  document.getElementById('profile-ref').textContent  = 'Ref: ' + data.reference;

  const cfg = STATUS[data.status] || STATUS.draft;
  const badge = document.getElementById('status-badge');
  badge.textContent = cfg.label;
  badge.className   = 'status-badge ' + cfg.cls;

  /* Property section */
  const hasAddress = data.rental_address;
  document.getElementById('section-property').classList.toggle('hidden', !hasAddress);
  document.getElementById('section-no-property').classList.toggle('hidden', !!hasAddress);
  if (hasAddress) {
    document.getElementById('profile-address').textContent = data.rental_address;
    document.getElementById('profile-postal').textContent  = data.rental_postal_code || '';
  }

  /* Deposit stats */
  document.getElementById('stat-deposit').textContent = fmtEur(data.deposit_amount);
  document.getElementById('stat-term').textContent    = fmtTerm(data.repayment_months);
  document.getElementById('stat-monthly').textContent = data.monthly_repayment ? fmtEur(data.monthly_repayment) : '—';
  document.getElementById('stat-rate').textContent    = fmtRate(data.interest_rate);

  /* Credit score (approved only) */
  const scoreSection = document.getElementById('section-score');
  if (data.credit_score != null && data.status === 'approved') {
    scoreSection.classList.remove('hidden');
    document.getElementById('score-value').textContent = Math.round(data.credit_score);
    const sc = data.credit_score;
    const scoreLabel = sc >= 80 ? 'Excellent' : sc >= 65 ? 'Good' : 'Acceptable';
    document.getElementById('score-label').textContent  = scoreLabel + ' credit profile';
    document.getElementById('score-reason').textContent = data.decision_reason || '';
  } else {
    scoreSection.classList.add('hidden');
  }

  /* Status notices */
  document.getElementById('section-pending').classList.toggle('hidden',  data.status !== 'pending');
  document.getElementById('section-rejected').classList.toggle('hidden', data.status !== 'rejected');
  if (data.status === 'rejected') {
    document.getElementById('rejected-reason').textContent =
      data.decision_reason || 'Application did not meet the approval criteria.';
  }

  document.getElementById('profile-date').textContent =
    data.created_at ? 'Applied on ' + fmtDate(data.created_at) : '';
}

function resetLookup() {
  document.getElementById('profile-card').classList.add('hidden');
  document.getElementById('lookup-card').classList.remove('hidden');
}

/* ─── Lookup submit ─── */
document.getElementById('form-lookup').addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const email = document.getElementById('lookup-email').value.trim();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showError('err-lookup-email'); return;
  }

  const btn = document.getElementById('btn-lookup');
  setLoading(btn, true);

  try {
    const res  = await fetch('/api/v1/profile/tenant?email=' + encodeURIComponent(email));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Application not found.');
    showProfile(data);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});
