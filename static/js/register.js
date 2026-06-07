/* global state */
let tenantId = null;
let applicationId = null;
let bankConnected = false;
let incomeMethod = 'bank';

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

function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg || el.textContent; el.classList.add('visible'); }
}

function clearErrors() {
  document.querySelectorAll('.field-error').forEach(e => e.classList.remove('visible'));
  document.querySelectorAll('input.error').forEach(e => e.classList.remove('error'));
}

/* ─── Step navigation ─── */
function goToStep(n) {
  document.getElementById('step1').classList.toggle('hidden', n !== 1);
  document.getElementById('step2').classList.toggle('hidden', n !== 2);

  ['prog-1', 'prog-2', 'prog-3'].forEach((id, i) => {
    const el = document.getElementById(id);
    el.classList.remove('active', 'done');
    if (i + 1 < n) el.classList.add('done');
    else if (i + 1 === n) el.classList.add('active');
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ─── ID type toggle ─── */
document.querySelectorAll('input[name="id_type"]').forEach(radio => {
  radio.addEventListener('change', () => {
    const isBSN = radio.value === 'bsn';
    document.getElementById('bsn-group').classList.toggle('hidden', !isBSN);
    document.getElementById('passport-group').classList.toggle('hidden', isBSN);
  });
});

/* ─── Upload zones ─── */
function initUploadZone(zoneId, inputId, previewId, previewNameId) {
  const zone  = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const prev  = document.getElementById(previewId);
  const name  = document.getElementById(previewNameId);

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });

  input.addEventListener('change', () => {
    if (input.files.length) handleFile(input.files[0]);
  });

  function handleFile(file) {
    zone.classList.add('has-file');
    name.textContent = file.name;
    prev.classList.add('visible');
    zone.querySelector('.upload-icon').style.display = 'none';
    zone.querySelector('.upload-text').style.display = 'none';
  }
}

initUploadZone('zone-id',      'file-id',      'prev-id',      'prev-id-name');
initUploadZone('zone-payslip', 'file-payslip', 'prev-payslip', 'prev-payslip-name');

/* ─── Income method toggle ─── */
function selectIncomeMethod(method) {
  incomeMethod = method;
  document.getElementById('tc-bank').classList.toggle('selected', method === 'bank');
  document.getElementById('tc-payslip').classList.toggle('selected', method === 'payslip');
  document.getElementById('panel-bank').classList.toggle('hidden', method !== 'bank');
  document.getElementById('panel-payslip').classList.toggle('hidden', method === 'bank');
}

/* ─── Bank connect (simulated PSD2) ─── */
document.getElementById('btn-connect-bank').addEventListener('click', async () => {
  if (!tenantId) { toast('Complete step 1 first.', 'error'); return; }
  if (bankConnected) return;

  const btn = document.getElementById('btn-connect-bank');
  setLoading(btn, true);

  try {
    const fd = new FormData();
    fd.append('tenant_id', tenantId);
    const res = await fetch('/api/v1/register/connect-bank', { method: 'POST', body: fd });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Bank connection failed.');

    bankConnected = true;
    btn.classList.add('connected');
    document.getElementById('bank-btn-label').textContent =
      `✅ Connected — ${data.bank_name} · ${data.months_retrieved} months retrieved`;
    toast('Bank connected successfully!', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
    btn.disabled = bankConnected;
  }
});

/* ─── Date of birth: manual entry only (DD-MM-YYYY) ─── */
const dobInput = document.getElementById('dob_input');

/* Auto-format manual digits as DD-MM-YYYY while typing */
dobInput.addEventListener('input', () => {
  const digits = dobInput.value.replace(/\D/g, '').slice(0, 8);
  if (digits.length > 4) dobInput.value = `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`;
  else if (digits.length > 2) dobInput.value = `${digits.slice(0, 2)}-${digits.slice(2)}`;
  else dobInput.value = digits;
});

/* Parses "DD-MM-YYYY" -> ISO "YYYY-MM-DD", or null if invalid/non-existent date */
function parseDob(str) {
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(str.trim());
  if (!m) return null;
  const [, dd, mm, yyyy] = m;
  const d = new Date(`${yyyy}-${mm}-${dd}T00:00:00`);
  if (d.getFullYear() != yyyy || d.getMonth() + 1 != mm || d.getDate() != dd) return null;
  return `${yyyy}-${mm}-${dd}`;
}

/* ─── STEP 1 SUBMIT ─── */
document.getElementById('form-identity').addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const idType    = document.querySelector('input[name="id_type"]:checked').value;
  const idNumber  = idType === 'bsn'
    ? document.getElementById('bsn').value.trim()
    : document.getElementById('passport').value.trim();
  const fullName  = document.getElementById('full_name').value.trim();
  const email     = document.getElementById('email').value.trim();
  const idFile    = document.getElementById('file-id').files[0];

  let valid = true;

  if (idType === 'bsn' && !/^\d{9}$/.test(idNumber)) {
    showError('err-bsn'); document.getElementById('bsn').classList.add('error'); valid = false;
  }
  if (idType === 'passport' && idNumber.length < 6) {
    showError('err-passport'); document.getElementById('passport').classList.add('error'); valid = false;
  }
  if (!fullName) { showError('err-name'); valid = false; }

  let dobIso = null;
  if (!dobInput.value.trim()) {
    showError('err-dob'); valid = false;
  } else {
    dobIso = parseDob(dobInput.value);
    if (!dobIso) {
      showError('err-dob'); valid = false;
    } else {
      const ageMs = new Date() - new Date(`${dobIso}T00:00:00`);
      const age = ageMs / (365.25 * 24 * 3600 * 1000);
      if (age < 18) { showError('err-dob', 'You must be at least 18 years old.'); valid = false; }
    }
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showError('err-email'); valid = false;
  }
  if (!idFile) { showError('err-id-doc'); valid = false; }

  if (!valid) return;

  const btn = document.getElementById('btn-identity');
  setLoading(btn, true);

  try {
    /* 1. POST identity fields */
    const fd1 = new FormData();
    fd1.append('full_name', fullName);
    fd1.append('email', email);
    fd1.append('date_of_birth', dobIso);
    fd1.append('id_type', idType);
    fd1.append('id_number', idNumber);

    const r1 = await fetch('/api/v1/register/identity', { method: 'POST', body: fd1 });
    const d1 = await r1.json();
    if (!r1.ok) throw new Error(d1.detail || 'Registration failed.');

    tenantId = d1.tenant_id;
    applicationId = d1.application_id;

    /* 2. Upload ID document */
    const fd2 = new FormData();
    fd2.append('tenant_id', tenantId);
    fd2.append('doc_type', 'id_document');
    fd2.append('file', idFile);
    const r2 = await fetch('/api/v1/register/upload-document', { method: 'POST', body: fd2 });
    if (!r2.ok) { const e2 = await r2.json(); throw new Error(e2.detail || 'ID upload failed.'); }

    toast('Identity verified — step 2 of 3', 'success');
    goToStep(2);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

/* ─── STEP 2 SUBMIT ─── */
document.getElementById('form-income').addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const employment = document.querySelector('input[name="employment_status"]:checked')?.value;
  const amount     = parseFloat(document.getElementById('amount_requested').value);
  const payslipFile= document.getElementById('file-payslip').files[0];

  let valid = true;

  if (!employment) { showError('err-employment'); valid = false; }
  if (!amount || amount < 1000 || amount > 4000) { showError('err-amount'); valid = false; }

  if (incomeMethod === 'bank' && !bankConnected) {
    toast('Please connect your bank account first.', 'error'); valid = false;
  }
  if (incomeMethod === 'payslip' && !payslipFile) {
    showError('err-payslip'); valid = false;
  }

  if (!valid) return;

  const btn = document.getElementById('btn-income');
  setLoading(btn, true);

  try {
    /* Upload payslip if chosen */
    if (incomeMethod === 'payslip' && payslipFile) {
      const fdp = new FormData();
      fdp.append('tenant_id', tenantId);
      fdp.append('doc_type', 'payslip');
      fdp.append('file', payslipFile);
      const rp = await fetch('/api/v1/register/upload-document', { method: 'POST', body: fdp });
      if (!rp.ok) { const ep = await rp.json(); throw new Error(ep.detail || 'Payslip upload failed.'); }
    }

    /* POST income step */
    const fd = new FormData();
    fd.append('tenant_id', tenantId);
    fd.append('application_id', applicationId);
    fd.append('employment_status', employment);
    fd.append('amount_requested', amount);

    const res = await fetch('/api/v1/register/income', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Submission failed.');

    toast('Application submitted! Running credit check...', 'success');
    goToStep(3);

    /* Redirect to scoring/decision page (to be built) */
    setTimeout(() => {
      window.location.href = `/decision?application_id=${applicationId}`;
    }, 1800);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});
