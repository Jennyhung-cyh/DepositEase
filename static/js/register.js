/* global state */
let tenantId = null;
let applicationId = null;
let bankConnected = false;
let incomeDocVariant = null;   // 'payslip' | 'tax_return' | 'duo_letter' | null

/* Drives the conditional "Upload income document" panel — which document
   type applies depends on employment status (and, for students, whether
   they receive DUO / have part-time income). */
const INCOME_DOC_CONFIG = {
  payslip: {
    docType: 'payslip',
    label: 'Upload last 3 payslips',
    hint: 'PDF or image of your last 3 payslips',
    tip: "<strong>What's in a payslip?</strong><br>Employer · Gross &amp; net salary · Pay period · Tax &amp; pension details",
  },
  tax_return: {
    docType: 'tax_return',
    label: "Upload last 2 years' tax returns (aangifte)",
    hint: "PDF or image of your tax returns (aangifte)",
    tip: 'Accepted: PDF from Belastingdienst portal',
  },
  duo_letter: {
    docType: 'duo_letter',
    label: 'Upload DUO toekenningsbrief',
    hint: 'PDF or image of your DUO toekenningsbrief',
    tip: 'This confirms your monthly student finance amount',
  },
};

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
  document.getElementById('step3').classList.toggle('hidden', n !== 3);

  ['prog-1', 'prog-2', 'prog-3', 'prog-4'].forEach((id, i) => {
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

/* ─── Employment status conditional follow-ups ─── */
document.querySelectorAll('input[name="employment_status"]').forEach(radio => {
  radio.addEventListener('change', () => {
    const v = radio.value;
    document.getElementById('cond-contract-type').classList.toggle('hidden',
      !(v === 'employed_full_time' || v === 'employed_part_time'));
    document.getElementById('cond-self-employed').classList.toggle('hidden', v !== 'self_employed');
    document.getElementById('cond-student').classList.toggle('hidden', v !== 'student');
    document.getElementById('cond-unemployed').classList.toggle('hidden', v !== 'unemployed');
    updateIncomeDocPanel();
  });
});

/* ─── Residency status conditional follow-ups ─── */
document.querySelectorAll('input[name="residency_status"]').forEach(radio => {
  radio.addEventListener('change', () => {
    const v = radio.value;
    document.getElementById('cond-permit').classList.toggle('hidden', v !== 'non_eu_permit');
    document.getElementById('cond-recent').classList.toggle('hidden', v !== 'recently_arrived');
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

/* Clears a file input and its preview — used when the income document
   type changes (e.g. employment status switches from employed to student). */
function resetUploadZone(zoneId, inputId, previewId, previewNameId) {
  const zone  = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const prev  = document.getElementById(previewId);
  const name  = document.getElementById(previewNameId);

  zone.classList.remove('has-file');
  input.value = '';
  name.textContent = '';
  prev.classList.remove('visible');
  zone.querySelector('.upload-icon').style.display = '';
  zone.querySelector('.upload-text').style.display = '';
}

initUploadZone('zone-id',         'file-id',         'prev-id',         'prev-id-name');
initUploadZone('zone-income-doc', 'file-income-doc', 'prev-income-doc', 'prev-income-doc-name');
initUploadZone('zone-contract',   'file-contract',   'prev-contract',   'prev-contract-name');

/* ─── Income document panel — type depends on employment situation ─── */
/* Returns a doc-type key when determinable, null when confirmed not
   applicable (unemployed / no-income student), or undefined when the
   applicant hasn't answered enough questions yet to tell. */
function determineIncomeDocVariant() {
  const emp = document.querySelector('input[name="employment_status"]:checked')?.value;
  if (!emp) return undefined;
  if (emp === 'employed_full_time' || emp === 'employed_part_time') return 'payslip';
  if (emp === 'self_employed') return 'tax_return';
  if (emp === 'student') {
    const duo      = document.querySelector('input[name="receives_duo"]:checked')?.value;
    const parttime = document.querySelector('input[name="has_parttime_income"]:checked')?.value;
    if (duo === 'yes') return 'duo_letter';
    if (parttime === 'yes') return 'payslip';
    if (duo === 'no' && parttime === 'no') return null;   // confirmed no income source
    return undefined;   // student selected, but DUO/part-time not answered yet
  }
  return null;          // unemployed — nothing to upload
}

function updateIncomeDocPanel() {
  const variant = determineIncomeDocVariant();
  const prompt = document.getElementById('income-doc-prompt');
  const panel  = document.getElementById('income-doc-panel');
  const none   = document.getElementById('income-doc-none');

  if (variant === undefined) {
    panel.classList.add('hidden');
    none.classList.add('hidden');
    prompt.classList.remove('hidden');
    incomeDocVariant = null;
    return;
  }
  prompt.classList.add('hidden');

  if (variant === null) {
    panel.classList.add('hidden');
    none.classList.remove('hidden');
    incomeDocVariant = null;
    return;
  }

  none.classList.add('hidden');
  panel.classList.remove('hidden');

  if (incomeDocVariant !== variant) {
    incomeDocVariant = variant;
    const cfg = INCOME_DOC_CONFIG[variant];
    document.getElementById('income-doc-label').textContent = cfg.label;
    document.getElementById('income-doc-hint').textContent = cfg.hint;
    document.getElementById('income-doc-tip').innerHTML = cfg.tip;
    resetUploadZone('zone-income-doc', 'file-income-doc', 'prev-income-doc', 'prev-income-doc-name');
  }
}

document.querySelectorAll('input[name="receives_duo"], input[name="has_parttime_income"]').forEach(radio => {
  radio.addEventListener('change', updateIncomeDocPanel);
});

updateIncomeDocPanel();

/* ─── Bank connect (simulated PSD2, required) ─── */
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
    document.getElementById('bank-status').classList.add('connected');
    document.getElementById('bank-status-label').textContent =
      `Status: ✅ Connected — ${data.bank_name} · ${data.months_retrieved} months retrieved`;
    document.getElementById('err-bank').classList.remove('visible');
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

    toast('Identity verified — step 2 of 4', 'success');
    goToStep(2);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

/* ─── Postal code auto-format ─── */
document.getElementById('rental_postal_code').addEventListener('input', function () {
  const digits = this.value.replace(/\s/g, '');
  if (digits.length > 4) {
    this.value = digits.slice(0, 4) + ' ' + digits.slice(4, 6).toUpperCase();
  }
});

/* ─── Repayment term options (dynamic) ─── */
/* Candidate options in months — filtered to [min_months, 24] */
const REPAYMENT_CANDIDATES = [6, 12, 18, 24];

function updateRepaymentOptions() {
  const termSpecified = document.querySelector('input[name="contract_term_specified"]:checked')?.value;
  document.getElementById('cond-term-months').classList.toggle('hidden', termSpecified !== 'yes');

  let minMonths = 12;
  if (termSpecified === 'yes') {
    const raw = parseInt(document.getElementById('contract_term_months').value, 10);
    if (!isNaN(raw) && raw > 0) minMonths = raw;
  }

  const options = REPAYMENT_CANDIDATES.filter(m => m >= minMonths && m <= 24);
  if (options.length === 0) options.push(24);

  const container = document.getElementById('repayment-options');
  const currentSelected = document.querySelector('input[name="repayment_months"]:checked')?.value;
  container.innerHTML = '';

  const labels = { 6: '6 months', 12: '12 months (1 year)', 18: '18 months', 24: '24 months (2 years)' };
  options.forEach(months => {
    const checked = currentSelected == months ? 'checked' : '';
    container.insertAdjacentHTML('beforeend',
      `<input type="radio" name="repayment_months" id="rm-${months}" value="${months}" ${checked} />` +
      `<label for="rm-${months}">${labels[months] || months + ' months'}</label>`
    );
  });
}

document.querySelectorAll('input[name="contract_term_specified"]').forEach(r => {
  r.addEventListener('change', updateRepaymentOptions);
});

document.getElementById('contract_term_months').addEventListener('input', updateRepaymentOptions);

/* ─── STEP 3 SUBMIT ─── */
document.getElementById('form-rental').addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  const address    = document.getElementById('rental_address').value.trim();
  const postal     = document.getElementById('rental_postal_code').value.trim();
  const deposit    = parseFloat(document.getElementById('deposit_amount').value);
  const contractFile = document.getElementById('file-contract').files[0];
  const termSpecified = document.querySelector('input[name="contract_term_specified"]:checked')?.value;
  const termMonthsRaw = document.getElementById('contract_term_months').value;
  const repayment  = document.querySelector('input[name="repayment_months"]:checked')?.value;

  let valid = true;

  if (!address) { showError('err-address'); valid = false; }

  if (!/^\d{4}\s?[A-Za-z]{2}$/.test(postal)) {
    showError('err-postal'); valid = false;
  }

  if (!contractFile) { showError('err-contract'); valid = false; }

  if (termSpecified === 'yes') {
    const tm = parseInt(termMonthsRaw, 10);
    if (!tm || tm < 1) { showError('err-term-months'); valid = false; }
  }

  if (isNaN(deposit) || deposit <= 0 || deposit > 4000) {
    showError('err-deposit'); valid = false;
  }

  if (!repayment) { showError('err-repayment'); valid = false; }

  if (!valid) return;

  const btn = document.getElementById('btn-rental');
  setLoading(btn, true);

  try {
    /* Upload rental contract */
    const fdContract = new FormData();
    fdContract.append('tenant_id', tenantId);
    fdContract.append('doc_type', 'rental_contract');
    fdContract.append('file', contractFile);
    const rc = await fetch('/api/v1/register/upload-document', { method: 'POST', body: fdContract });
    if (!rc.ok) { const ec = await rc.json(); throw new Error(ec.detail || 'Contract upload failed.'); }

    /* POST rental details */
    const fd = new FormData();
    fd.append('tenant_id', tenantId);
    fd.append('application_id', applicationId);
    fd.append('rental_address', address);
    fd.append('rental_postal_code', postal);
    fd.append('deposit_amount', deposit);
    fd.append('repayment_months', repayment);
    if (termSpecified === 'yes' && termMonthsRaw) {
      fd.append('contract_term_months', parseInt(termMonthsRaw, 10));
    }

    const res = await fetch('/api/v1/register/rental', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Submission failed.');

    toast('Application submitted! Running credit check...', 'success');
    goToStep(4);

    setTimeout(() => {
      window.location.href = `/decision?application_id=${applicationId}`;
    }, 1800);
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

  const employment   = document.querySelector('input[name="employment_status"]:checked')?.value;
  const contractType = document.querySelector('input[name="contract_type"]:checked')?.value;
  const selfEmpYears = document.querySelector('input[name="self_employed_duration"]:checked')?.value;
  const receivesDuo  = document.querySelector('input[name="receives_duo"]:checked')?.value;
  const parttimeInc  = document.querySelector('input[name="has_parttime_income"]:checked')?.value;
  const residency    = document.querySelector('input[name="residency_status"]:checked')?.value;
  const permitType   = document.querySelector('input[name="permit_type"]:checked')?.value;
  const permitExpiry = document.getElementById('permit_expiry').value;
  const incomeDocFile = document.getElementById('file-income-doc').files[0];

  let valid = true;

  if (!employment) { showError('err-employment'); valid = false; }
  if ((employment === 'employed_full_time' || employment === 'employed_part_time') && !contractType) {
    showError('err-contract-type'); valid = false;
  }
  if (employment === 'self_employed' && !selfEmpYears) {
    showError('err-self-employed'); valid = false;
  }
  if (employment === 'student') {
    if (!receivesDuo) { showError('err-duo'); valid = false; }
    if (!parttimeInc) { showError('err-parttime'); valid = false; }
  }

  if (!residency) { showError('err-residency'); valid = false; }
  if (residency === 'non_eu_permit') {
    if (!permitType)   { showError('err-permit-type'); valid = false; }
    if (!permitExpiry) { showError('err-permit-expiry'); valid = false; }
  }

  if (!bankConnected) {
    showError('err-bank');
    toast('Please connect your bank account to continue.', 'error'); valid = false;
  }

  if (!valid) return;

  const btn = document.getElementById('btn-income');
  setLoading(btn, true);

  try {
    /* Upload income document if the applicant chose to add one (recommended, not required) */
    if (incomeDocVariant && incomeDocFile) {
      const fdp = new FormData();
      fdp.append('tenant_id', tenantId);
      fdp.append('doc_type', INCOME_DOC_CONFIG[incomeDocVariant].docType);
      fdp.append('file', incomeDocFile);
      const rp = await fetch('/api/v1/register/upload-document', { method: 'POST', body: fdp });
      if (!rp.ok) { const ep = await rp.json(); throw new Error(ep.detail || 'Income document upload failed.'); }
    }

    /* POST income step */
    const fd = new FormData();
    fd.append('tenant_id', tenantId);
    fd.append('application_id', applicationId);
    fd.append('employment_status', employment);
    if (contractType) fd.append('contract_type', contractType);
    if (selfEmpYears) fd.append('self_employed_duration', selfEmpYears);
    if (receivesDuo)  fd.append('receives_duo', receivesDuo);
    if (parttimeInc)  fd.append('has_parttime_income', parttimeInc);
    fd.append('residency_status', residency);
    if (permitType)   fd.append('permit_type', permitType);
    if (permitExpiry) fd.append('permit_expiry_date', permitExpiry);

    const res = await fetch('/api/v1/register/income', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Submission failed.');

    toast('Income verified — step 3 of 4', 'success');
    updateRepaymentOptions();
    goToStep(3);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});
