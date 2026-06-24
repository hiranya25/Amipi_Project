let inventoryFile = null;
let eventsFile = null;
let currentRecords = [];

const dzInventory = document.getElementById('dz-inventory');
const dzEvents = document.getElementById('dz-events');
const inputInventory = document.getElementById('input-inventory');
const inputEvents = document.getElementById('input-events');
const fileInventory = document.getElementById('file-inventory');
const fileEvents = document.getElementById('file-events');
const lblInventory = document.getElementById('lbl-inventory');
const lblEvents = document.getElementById('lbl-events');
const eventSelector = document.getElementById('event-selector');
const runBtn = document.getElementById('run-btn');

function handleDrop(e, type) {
  e.preventDefault();
  const file = e.dataTransfer ? e.dataTransfer.files[0] : e.target.files[0];
  if (!file) return;
  
  hideToast();
  if (type === 'inventory') {
    inventoryFile = file;
    lblInventory.innerHTML = 'Click or drop to replace';
    fileInventory.innerHTML = file.name;
    fileInventory.style.display = 'block';
    dzInventory.classList.add('active');
    dzInventory.classList.remove('error');
    document.getElementById('err-inventory').classList.remove('show');
    validateInventoryCSV(file);
  } else {
    eventsFile = file;
    lblEvents.innerHTML = 'Click or drop to replace';
    fileEvents.innerHTML = file.name;
    fileEvents.style.display = 'block';
    dzEvents.classList.add('active');
    dzEvents.classList.remove('error');
    document.getElementById('err-events').classList.remove('show');
    parseEventsCSV(file);
  }
  checkReady();
}

[dzInventory, dzEvents].forEach(dz => {
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.style.borderColor = 'var(--accent-blue)'; });
  dz.addEventListener('dragleave', e => { e.preventDefault(); dz.style.borderColor = ''; });
});

dzInventory.addEventListener('drop', e => handleDrop(e, 'inventory'));
dzEvents.addEventListener('drop', e => handleDrop(e, 'events'));
dzInventory.addEventListener('click', () => inputInventory.click());
dzEvents.addEventListener('click', () => inputEvents.click());
inputInventory.addEventListener('change', e => handleDrop(e, 'inventory'));
inputEvents.addEventListener('change', e => handleDrop(e, 'events'));

function parseEventsCSV(file) {
  const formData = new FormData();
  formData.append('events_csv', file);
  eventSelector.innerHTML = '<option value="">Parsing events...</option>';
  
  fetch('/api/events', { method: 'POST', body: formData })
    .then(async res => {
      let data;
      try { data = await res.json(); } catch(e) { throw new Error(`Status ${res.status}: Server returned non-JSON.`); }
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status} Error`);
      return data;
    })
    .then(data => {
      if (data.error) throw new Error(data.error);
      eventSelector.innerHTML = '<option value="">Select an event...</option>';
      data.events.forEach(ev => {
        const opt = document.createElement('option');
        opt.value = ev; opt.textContent = ev;
        eventSelector.appendChild(opt);
      });
      eventSelector.disabled = false;
      checkReady();
    })
    .catch(err => {
      dzEvents.classList.add('error');
      const errDiv = document.getElementById('err-events');
      errDiv.textContent = err.message;
      errDiv.classList.add('show');
      eventSelector.innerHTML = '<option value="">Error parsing events</option>';
      eventsFile = null;
      checkReady();
    });
}

function validateInventoryCSV(file) {
  const formData = new FormData();
  formData.append('inventory_csv', file);
  fetch('/api/validate_inventory', { method: 'POST', body: formData })
    .then(async res => {
      let data;
      try { data = await res.json(); } catch(e) { throw new Error(`Status ${res.status}: Server returned non-JSON.`); }
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status} Error`);
      if (data.error) throw new Error(data.error);
      checkReady();
    })
    .catch(err => {
      dzInventory.classList.add('error');
      const errDiv = document.getElementById('err-inventory');
      errDiv.textContent = err.message;
      errDiv.classList.add('show');
      inventoryFile = null;
      checkReady();
    });
}

eventSelector.addEventListener('change', checkReady);

function checkReady() {
  runBtn.disabled = !(inventoryFile && eventsFile && eventSelector.value);
}

runBtn.addEventListener('click', async () => {
  hideToast();
  const btnOriginalText = runBtn.textContent;
  runBtn.textContent = 'Processing...';
  runBtn.disabled = true;
  
  const formData = new FormData();
  formData.append('inventory_csv', inventoryFile);
  formData.append('events_csv', eventsFile);
  formData.append('event_name', eventSelector.value);
  formData.append('use_ai', document.getElementById('ai-toggle').checked);
  
  try {
    const res = await fetch('/api/process', { method: 'POST', body: formData });
    let data;
    try { data = await res.json(); } catch(e) { throw new Error(`Status ${res.status}: Server returned non-JSON.`); }
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status} Error`);
    if (data.error) throw new Error(data.error);
    
    currentRecords = data.records;
    renderDashboard();
    document.getElementById('export-csv-btn').disabled = false;
  } catch (err) {
    showToast(err.message);
  } finally {
    runBtn.textContent = btnOriginalText;
    runBtn.disabled = false;
  }
});

function renderDashboard() {
  const eventName = eventSelector.value;
  document.getElementById('event-title-display').textContent = eventName;
  document.getElementById('kpi-total-desc').textContent = eventName;
  
  let totalUnits = 0;
  let highPriority = 0;
  let riskStockout = 0;
  let countMed = 0;
  let countLow = 0;
  let countDnr = 0;
  
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = '';
  
  currentRecords.forEach((rec, idx) => {
    totalUnits += rec.suggested_order_qty;
    const pri = rec.priority === 'Do Not Reorder' ? 'DNR' : rec.priority;
    
    if (pri === 'High') highPriority++;
    if (pri === 'Medium') countMed++;
    if (pri === 'Low') countLow++;
    if (pri === 'DNR') countDnr++;
    if (pri === 'High' && rec.available_inventory <= 2) riskStockout++;
    
    const subtitle = `${rec.recommendation} - ${eventName}`;
    
    const card = document.createElement('div');
    card.className = `sku-card ${pri}`;
    card.innerHTML = `
      <div class="card-header">
        <div class="card-badge ${pri}">● ${rec.priority}</div>
        <div class="card-title">${rec.style_number}</div>
        <div class="card-subtitle">${subtitle}</div>
      </div>
      <div class="card-stats">
        <div class="stat-col">
          <div class="stat-label">Suggested order</div>
          <div class="stat-val yellow">${rec.suggested_order_qty}</div>
        </div>
        <div class="stat-col">
          <div class="stat-label">Available now</div>
          <div class="stat-val">${rec.available_inventory}</div>
        </div>
      </div>
      <div class="card-reason">"${rec.reason}"</div>
      <div class="card-actions">
        <button class="btn-yellow" onclick="event.stopPropagation(); alert('Order added to sheet')">Confirm order</button>
        <button class="btn-dark" onclick="openSlideover(${idx})">Details</button>
      </div>
    `;
    grid.appendChild(card);
  });
  
  document.getElementById('kpi-total-val').textContent = currentRecords.length;
  document.getElementById('kpi-units-val').textContent = totalUnits;
  document.getElementById('kpi-units-desc').textContent = `Across ${currentRecords.length} SKUs`;
  document.getElementById('kpi-high-val').textContent = highPriority;
  document.getElementById('kpi-risk-val').textContent = riskStockout;
  
  document.getElementById('flt-all').textContent = currentRecords.length;
  document.getElementById('flt-high').textContent = highPriority;
  document.getElementById('flt-med').textContent = countMed;
  document.getElementById('flt-low').textContent = countLow;
  document.getElementById('flt-dnr').textContent = countDnr;
}

const slideover = document.getElementById('slideover');
document.getElementById('so-close').addEventListener('click', () => slideover.classList.remove('open'));
document.getElementById('so-close-btn').addEventListener('click', () => slideover.classList.remove('open'));

function openSlideover(idx) {
  const rec = currentRecords[idx];
  document.getElementById('so-style').textContent = rec.style_number;
  document.getElementById('so-sub').textContent = eventSelector.value;
  
  const pri = rec.priority === 'Do Not Reorder' ? 'DNR' : rec.priority;
  const recText = `${rec.priority} — ${rec.recommendation} — ${rec.suggested_order_qty} units`;
  document.getElementById('so-rec-text').textContent = recText;
  document.getElementById('so-rec').className = `so-rec ${pri}`;
  
  document.getElementById('so-reason').textContent = `"${rec.reason}"`;
  document.getElementById('so-reason').style.borderLeftColor = `var(--priority-${pri.toLowerCase()})`;
  
  // If no AI was used, show template note
  const useAi = document.getElementById('ai-toggle').checked;
  document.getElementById('so-template-note').style.display = useAi ? 'none' : 'block';
  
  document.getElementById('tr-avail').textContent = rec.available_inventory;
  document.getElementById('tr-monthly').textContent = rec.monthly_sales_rate;
  document.getElementById('tr-proj').textContent = rec.projected_demand_until_event;
  document.getElementById('tr-mult').textContent = `${rec.event_multiplier}x`;
  document.getElementById('tr-needed').textContent = rec.recommended_stock_needed;
  document.getElementById('tr-qty').textContent = rec.suggested_order_qty;
  
  document.getElementById('override-qty').textContent = rec.suggested_order_qty;
  
  slideover.classList.add('open');
}

document.getElementById('so-confirm').addEventListener('click', () => {
  slideover.classList.remove('open');
  alert('Order added to sheet');
});

let toastTimeout;
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), 4000);
}

function hideToast() {
  const toast = document.getElementById('toast');
  toast.classList.remove('show');
  if (toastTimeout) clearTimeout(toastTimeout);
}

document.getElementById('export-csv-btn').addEventListener('click', () => {
  if (!currentRecords.length) return;
  const headers = ['style_number', 'available_inventory', 'monthly_sales_rate', 'projected_demand_until_event', 'event_multiplier', 'recommended_stock_needed', 'suggested_order_qty', 'priority', 'recommendation', 'reason'];
  const rows = currentRecords.map(r => headers.map(h => {
    let val = r[h] === null ? '' : r[h].toString();
    if (val.includes(',') || val.includes('"')) { val = `"${val.replace(/"/g, '""')}"`; }
    return val;
  }).join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'order_sheet.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
});
