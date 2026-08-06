const STATE_KEY = "ponto-funcionarios:app-state:v2";

const viewTitle = document.querySelector("#viewTitle");
const navButtons = [...document.querySelectorAll(".nav-button")];
const views = {
  dashboard: document.querySelector("#dashboardView"),
  import: document.querySelector("#importView"),
  employees: document.querySelector("#employeesView"),
  timesheet: document.querySelector("#timesheetView"),
  reports: document.querySelector("#reportsView")
};

const fileInput = document.querySelector("#fileInput");
const rawText = document.querySelector("#rawText");
const parseText = document.querySelector("#parseText");
const employeeFilter = document.querySelector("#employeeFilter");
const monthFilter = document.querySelector("#monthFilter");
const weekdayHours = document.querySelector("#weekdayHours");
const saturdayHours = document.querySelector("#saturdayHours");
const defaultTolerance = document.querySelector("#defaultTolerance");
const resultRows = document.querySelector("#resultRows");
const employeeRows = document.querySelector("#employeeRows");
const statusText = document.querySelector("#statusText");
const saveStatus = document.querySelector("#saveStatus");
const exportCsv = document.querySelector("#exportCsv");
const backupJson = document.querySelector("#backupJson");
const restoreJson = document.querySelector("#restoreJson");
const restoreFile = document.querySelector("#restoreFile");
const clearLocalData = document.querySelector("#clearLocalData");
const addEmployee = document.querySelector("#addEmployee");
const printReport = document.querySelector("#printReport");
const reportOutput = document.querySelector("#reportOutput");
const employeeBalances = document.querySelector("#employeeBalances");
const alertList = document.querySelector("#alertList");
const dashboardStatus = document.querySelector("#dashboardStatus");

const summary = {
  days: document.querySelector("#daysCount"),
  worked: document.querySelector("#workedTotal"),
  expected: document.querySelector("#expectedTotal"),
  balance: document.querySelector("#balanceTotal")
};

let state = loadState();
let records = [];
let dayRows = [];

bindEvents();
hydrate();

function bindEvents() {
  navButtons.forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  fileInput.addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    rawText.value = await readClockFile(file);
    state.rawText = rawText.value;
    processImport();
  });

  rawText.addEventListener("input", () => {
    state.rawText = rawText.value;
    saveState();
  });

  parseText.addEventListener("click", processImport);

  [monthFilter, employeeFilter].forEach((control) => {
    control.addEventListener("change", () => {
      state.filters[control.id] = control.value;
      saveState();
      renderAll();
    });
  });

  [weekdayHours, saturdayHours, defaultTolerance].forEach((control) => {
    control.addEventListener("change", () => {
      state.settings[control.id] = control.value;
      saveState();
      recalculate();
    });
  });

  resultRows.addEventListener("change", handleDayEdit);
  employeeRows.addEventListener("change", handleEmployeeEdit);
  employeeRows.addEventListener("click", handleEmployeeAction);

  addEmployee.addEventListener("click", () => {
    const id = nextEmployeeId();
    state.employees[id] = {
      id,
      name: "Novo funcionario",
      department: "",
      weekdayHours: state.settings.weekdayHours,
      saturdayHours: state.settings.saturdayHours,
      sundayHours: "00:00",
      tolerance: Number(state.settings.defaultTolerance) || 0,
      active: true
    };
    saveState();
    recalculate();
    setView("employees");
  });

  exportCsv.addEventListener("click", downloadCsv);
  backupJson.addEventListener("click", downloadBackup);
  restoreJson.addEventListener("click", () => restoreFile.click());
  restoreFile.addEventListener("change", restoreBackup);
  clearLocalData.addEventListener("click", clearSavedData);
  printReport.addEventListener("click", () => window.print());
}

function hydrate() {
  rawText.value = state.rawText;
  weekdayHours.value = state.settings.weekdayHours;
  saturdayHours.value = state.settings.saturdayHours;
  defaultTolerance.value = state.settings.defaultTolerance;
  processImport(false);
  setView(state.activeView || "dashboard");
  updateSaveStatus();
}

function defaultState() {
  return {
    savedAt: "",
    activeView: "dashboard",
    rawText: "",
    settings: {
      weekdayHours: "08:00",
      saturdayHours: "04:00",
      defaultTolerance: "15"
    },
    filters: {
      monthFilter: "",
      employeeFilter: ""
    },
    employees: {},
    dayEdits: {}
  };
}

function loadState() {
  try {
    return { ...defaultState(), ...JSON.parse(localStorage.getItem(STATE_KEY)) };
  } catch {
    return defaultState();
  }
}

function saveState() {
  state.savedAt = new Date().toISOString();
  localStorage.setItem(STATE_KEY, JSON.stringify(state));
  updateSaveStatus();
}

function updateSaveStatus() {
  if (!state.savedAt) {
    saveStatus.textContent = "Nada salvo ainda.";
    return;
  }
  saveStatus.textContent = `Salvo neste computador: ${new Date(state.savedAt).toLocaleString("pt-BR")}`;
}

function setView(name) {
  state.activeView = name;
  navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  Object.entries(views).forEach(([key, view]) => view.classList.toggle("active", key === name));
  viewTitle.textContent = navButtons.find((button) => button.dataset.view === name)?.textContent ?? "Painel";
  saveState();
}

function processImport(shouldSave = true) {
  state.rawText = rawText.value;
  records = parseClockText(state.rawText);
  syncEmployeesFromRecords(records);
  if (shouldSave) saveState();
  recalculate();
}

function recalculate() {
  records = parseClockText(state.rawText);
  dayRows = calculateRows(records);
  fillMonths(dayRows);
  fillEmployeesFilter();
  renderAll();
}

function parseClockText(text) {
  const rows = [];
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  for (const line of lines) {
    if (/^id\s+/i.test(line) || /^no\s+/i.test(line)) continue;

    const tabRow = parseTabbedClockLine(line);
    if (tabRow) rows.push(tabRow);
  }

  return rows.sort((a, b) => {
    if (a.id !== b.id) return Number(a.id) - Number(b.id);
    if (a.dateKey !== b.dateKey) return a.dateKey.localeCompare(b.dateKey);
    return a.minutes - b.minutes;
  });
}

function parseTabbedClockLine(line) {
  const columns = line.split(/\t+/).map((column) => column.trim()).filter(Boolean);
  if (columns.length < 4) return null;

  const brTimestamp = columns.find((column) => /\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/.test(column));
  if (brTimestamp) {
    const parsed = parseDateTime(brTimestamp, "br");
    if (!parsed) return null;
    return {
      id: cleanEmployeeId(columns[0]),
      name: cleanText(columns[1]),
      department: cleanText(columns[2]),
      source: "txt",
      ...parsed
    };
  }

  const isoTimestamp = columns.find((column) => /\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}:\d{2}/.test(column));
  if (isoTimestamp) {
    const parsed = parseDateTime(isoTimestamp, "iso");
    if (!parsed) return null;
    return {
      id: cleanEmployeeId(columns[2] || columns[0]),
      name: cleanText(columns[3] || `Funcionario ${columns[2] || columns[0]}`),
      department: "",
      source: "w20",
      ...parsed
    };
  }

  return null;
}

function parseDateTime(value, format) {
  const pattern = format === "iso"
    ? /(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/
    : /(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})/;
  const match = value.match(pattern);
  if (!match) return null;

  const parts = format === "iso"
    ? { year: match[1], month: match[2], day: match[3], hour: match[4], minute: match[5] }
    : { day: match[1], month: match[2], year: match[3], hour: match[4], minute: match[5] };

  const date = new Date(Number(parts.year), Number(parts.month) - 1, Number(parts.day));
  return {
    dateKey: `${parts.year}-${parts.month}-${parts.day}`,
    dateLabel: `${parts.day}/${parts.month}/${parts.year}`,
    monthKey: `${parts.year}-${parts.month}`,
    monthLabel: `${parts.month}/${parts.year}`,
    minutes: Number(parts.hour) * 60 + Number(parts.minute),
    weekday: date.getDay()
  };
}

async function readClockFile(file) {
  const buffer = await file.arrayBuffer();
  try {
    return new TextDecoder("windows-1252").decode(buffer);
  } catch {
    return new TextDecoder("utf-8").decode(buffer);
  }
}

function syncEmployeesFromRecords(rows) {
  let changed = false;
  rows.forEach((record) => {
    if (!record.id || state.employees[record.id]) return;
    state.employees[record.id] = {
      id: record.id,
      name: record.name || `Funcionario ${record.id}`,
      department: record.department || "",
      weekdayHours: state.settings.weekdayHours,
      saturdayHours: state.settings.saturdayHours,
      sundayHours: "00:00",
      tolerance: Number(state.settings.defaultTolerance) || 0,
      active: true
    };
    changed = true;
  });
  if (changed) saveState();
}

function calculateRows(rows) {
  const grouped = new Map();
  rows.forEach((record) => {
    const key = `${record.id}|${record.dateKey}`;
    if (!grouped.has(key)) {
      grouped.set(key, {
        rowKey: key,
        id: record.id,
        dateKey: record.dateKey,
        dateLabel: record.dateLabel,
        monthKey: record.monthKey,
        monthLabel: record.monthLabel,
        weekday: record.weekday,
        punches: []
      });
    }
    grouped.get(key).punches.push(record.minutes);
  });

  return [...grouped.values()].map((day) => {
    const employee = employeeFor(day.id);
    const edit = state.dayEdits[day.rowKey] ?? {};
    const originalPunches = [...day.punches].sort((a, b) => a - b);
    const punchMinutes = parsePunches(edit.punchesText) ?? originalPunches;
    const baseExpected = expectedMinutes(day.weekday, employee);
    const expected = parseTimeToMinutes(edit.expectedText) ?? baseExpected;
    const worked = sumWorkedMinutes(punchMinutes);
    const balance = applyTolerance(worked - expected, employee.tolerance);
    const credit = Math.max(0, balance);
    const debit = Math.max(0, -balance);
    const alerts = [];

    if (punchMinutes.length % 2 !== 0) alerts.push("Quantidade impar");
    if (punchMinutes.length < 2) alerts.push("Dia incompleto");
    if (edit.punchesText || edit.expectedText || edit.note) alerts.push("Alterado");

    return {
      ...day,
      employee,
      punchLabels: punchMinutes.map(formatMinutes),
      workedMinutes: worked,
      expectedMinutes: expected,
      balanceMinutes: balance,
      creditMinutes: credit,
      debitMinutes: debit,
      note: edit.note ?? "",
      alerts
    };
  }).sort((a, b) => a.dateKey.localeCompare(b.dateKey) || a.employee.name.localeCompare(b.employee.name));
}

function employeeFor(id) {
  return state.employees[id] ?? {
    id,
    name: `Funcionario ${id}`,
    department: "",
    weekdayHours: state.settings.weekdayHours,
    saturdayHours: state.settings.saturdayHours,
    sundayHours: "00:00",
    tolerance: Number(state.settings.defaultTolerance) || 0,
    active: true
  };
}

function expectedMinutes(weekday, employee) {
  if (weekday === 0) return parseTimeToMinutes(employee.sundayHours) ?? 0;
  if (weekday === 6) return parseTimeToMinutes(employee.saturdayHours) ?? 0;
  return parseTimeToMinutes(employee.weekdayHours) ?? 0;
}

function applyTolerance(balance, tolerance) {
  const limit = Number(tolerance) || 0;
  return Math.abs(balance) <= limit ? 0 : balance;
}

function sumWorkedMinutes(punchMinutes) {
  let total = 0;
  for (let index = 0; index < punchMinutes.length - 1; index += 2) {
    total += Math.max(0, punchMinutes[index + 1] - punchMinutes[index]);
  }
  return total;
}

function handleDayEdit(event) {
  const input = event.target.closest("[data-edit-field]");
  if (!input) return;
  const rowKey = input.closest("tr")?.dataset.rowKey;
  const row = dayRows.find((item) => item.rowKey === rowKey);
  if (!row) return;

  const current = state.dayEdits[rowKey] ?? {};
  state.dayEdits[rowKey] = {
    punchesText: current.punchesText ?? row.punchLabels.join(" | "),
    expectedText: current.expectedText ?? formatDuration(row.expectedMinutes),
    note: current.note ?? row.note ?? ""
  };
  state.dayEdits[rowKey][`${input.dataset.editField}Text`] = input.value;
  if (input.dataset.editField === "note") state.dayEdits[rowKey].note = input.value;
  saveState();
  recalculate();
}

function handleEmployeeEdit(event) {
  const input = event.target.closest("[data-employee-field]");
  if (!input) return;
  const id = input.closest("tr")?.dataset.employeeId;
  if (!state.employees[id]) return;

  const field = input.dataset.employeeField;
  state.employees[id][field] = input.type === "checkbox" ? input.checked : input.value;
  saveState();
  recalculate();
}

function handleEmployeeAction(event) {
  const button = event.target.closest("[data-employee-action]");
  if (!button) return;
  const id = button.closest("tr")?.dataset.employeeId;
  if (!id) return;
  if (button.dataset.employeeAction === "delete" && confirm("Excluir funcionario deste cadastro local?")) {
    delete state.employees[id];
    saveState();
    recalculate();
  }
}

function renderAll() {
  renderSummary();
  renderDashboard();
  renderEmployees();
  renderTimesheet();
  renderReport();
}

function renderSummary() {
  const rows = filteredRows();
  const totals = rows.reduce((acc, row) => {
    acc.worked += row.workedMinutes;
    acc.expected += row.expectedMinutes;
    acc.balance += row.balanceMinutes;
    return acc;
  }, { worked: 0, expected: 0, balance: 0 });

  summary.days.textContent = String(rows.length);
  summary.worked.textContent = formatDuration(totals.worked);
  summary.expected.textContent = formatDuration(totals.expected);
  summary.balance.textContent = formatSignedDuration(totals.balance);
  summary.balance.className = totals.balance < 0 ? "balance-negative" : "balance-positive";
}

function renderDashboard() {
  const rows = filteredRows();
  dashboardStatus.textContent = records.length ? `${records.length} batidas importadas.` : "Sem registros.";
  const byEmployee = groupByEmployee(rows);
  employeeBalances.innerHTML = "";
  if (!byEmployee.length) {
    employeeBalances.innerHTML = '<div class="empty-state">Sem saldo para exibir.</div>';
  } else {
    byEmployee.forEach((item) => {
      const div = document.createElement("div");
      div.className = "list-row";
      div.innerHTML = `<div><strong>${escapeHtml(item.name)}</strong><small>${item.days} dias calculados</small></div><strong class="${item.balance < 0 ? "balance-negative" : "balance-positive"}">${formatSignedDuration(item.balance)}</strong>`;
      employeeBalances.append(div);
    });
  }

  const alerts = rows.filter((row) => row.alerts.length).slice(0, 12);
  alertList.innerHTML = "";
  if (!alerts.length) {
    alertList.innerHTML = '<div class="empty-state">Nenhum alerta no filtro atual.</div>';
  } else {
    alerts.forEach((row) => {
      const div = document.createElement("div");
      div.className = "list-row";
      div.innerHTML = `<div><strong>${row.dateLabel} - ${escapeHtml(row.employee.name)}</strong><small>${row.alerts.join("; ")}</small></div><span class="alert">${row.punchLabels.join(" | ")}</span>`;
      alertList.append(div);
    });
  }
}

function renderEmployees() {
  const employees = Object.values(state.employees).sort((a, b) => a.name.localeCompare(b.name));
  employeeRows.innerHTML = "";
  if (!employees.length) {
    employeeRows.innerHTML = '<tr><td class="empty-state" colspan="9">Importe um TXT ou cadastre um funcionario.</td></tr>';
    return;
  }

  employees.forEach((employee) => {
    const tr = document.createElement("tr");
    tr.dataset.employeeId = employee.id;
    tr.innerHTML = `
      <td><input class="table-input short-input" data-employee-field="id" value="${escapeHtml(employee.id)}" disabled></td>
      <td><input class="table-input" data-employee-field="name" value="${escapeHtml(employee.name)}"></td>
      <td><input class="table-input" data-employee-field="department" value="${escapeHtml(employee.department)}"></td>
      <td><input class="table-input short-input" data-employee-field="weekdayHours" value="${escapeHtml(employee.weekdayHours)}"></td>
      <td><input class="table-input short-input" data-employee-field="saturdayHours" value="${escapeHtml(employee.saturdayHours)}"></td>
      <td><input class="table-input short-input" data-employee-field="sundayHours" value="${escapeHtml(employee.sundayHours)}"></td>
      <td><input class="table-input short-input" type="number" min="0" data-employee-field="tolerance" value="${escapeHtml(employee.tolerance)}"></td>
      <td><input type="checkbox" data-employee-field="active" ${employee.active ? "checked" : ""}></td>
      <td><button class="ghost-button danger-button" type="button" data-employee-action="delete">Excluir</button></td>
    `;
    employeeRows.append(tr);
  });
}

function renderTimesheet() {
  const rows = filteredRows();
  const monthText = monthFilter.value ? ` Mes ${monthFilter.options[monthFilter.selectedIndex].text}.` : "";
  statusText.textContent = records.length
    ? `${records.length} batidas importadas.${monthText} Dados salvos neste computador.`
    : "Nenhum arquivo importado.";
  resultRows.innerHTML = "";

  if (!rows.length) {
    resultRows.innerHTML = '<tr><td class="empty-state" colspan="10">Importe um arquivo ou ajuste os filtros.</td></tr>';
    return;
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.dataset.rowKey = row.rowKey;
    tr.innerHTML = `
      <td>${row.dateLabel}</td>
      <td>${escapeHtml(row.employee.name)}</td>
      <td>${escapeHtml(row.employee.department)}</td>
      <td><input class="table-input punches-input" data-edit-field="punches" value="${escapeHtml(row.punchLabels.join(" | "))}"></td>
      <td>${formatDuration(row.workedMinutes)}</td>
      <td><input class="table-input expected-input" data-edit-field="expected" value="${formatDuration(row.expectedMinutes)}"></td>
      <td class="balance-positive">${formatDuration(row.creditMinutes)}</td>
      <td class="balance-negative">${formatDuration(row.debitMinutes)}</td>
      <td><input class="table-input note-input" data-edit-field="note" value="${escapeHtml(row.note)}"></td>
      <td class="alert">${row.alerts.join("; ")}</td>
    `;
    resultRows.append(tr);
  });
}

function renderReport() {
  const grouped = groupByEmployee(filteredRows());
  if (!grouped.length) {
    reportOutput.innerHTML = '<div class="empty-state">Sem dados para relatorio.</div>';
    return;
  }

  reportOutput.innerHTML = grouped.map((item) => `
    <section class="report-block">
      <h3>${escapeHtml(item.name)}</h3>
      <p>Dias: ${item.days} | Trabalhado: ${formatDuration(item.worked)} | Previsto: ${formatDuration(item.expected)} | Credito: ${formatDuration(item.credit)} | Debito: ${formatDuration(item.debit)} | Saldo: ${formatSignedDuration(item.balance)}</p>
    </section>
  `).join("");
}

function groupByEmployee(rows) {
  const map = new Map();
  rows.forEach((row) => {
    if (!map.has(row.id)) {
      map.set(row.id, { id: row.id, name: row.employee.name, days: 0, worked: 0, expected: 0, credit: 0, debit: 0, balance: 0 });
    }
    const item = map.get(row.id);
    item.days += 1;
    item.worked += row.workedMinutes;
    item.expected += row.expectedMinutes;
    item.credit += row.creditMinutes;
    item.debit += row.debitMinutes;
    item.balance += row.balanceMinutes;
  });
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function filteredRows() {
  const employeeId = employeeFilter.value;
  const monthKey = monthFilter.value;
  return dayRows.filter((row) => {
    const employeeMatches = employeeId ? row.id === employeeId : true;
    const monthMatches = monthKey ? row.monthKey === monthKey : true;
    return employeeMatches && monthMatches;
  });
}

function fillMonths(rows) {
  const currentValue = state.filters.monthFilter;
  const months = new Map();
  rows.forEach((row) => months.set(row.monthKey, row.monthLabel));
  monthFilter.innerHTML = '<option value="">Todos</option>';
  [...months.entries()].sort((a, b) => b[0].localeCompare(a[0])).forEach(([key, label]) => {
    monthFilter.append(new Option(label, key));
  });
  if (months.has(currentValue)) monthFilter.value = currentValue;
  else if (months.size === 1) monthFilter.value = [...months.keys()][0];
  state.filters.monthFilter = monthFilter.value;
}

function fillEmployeesFilter() {
  const currentValue = state.filters.employeeFilter;
  employeeFilter.innerHTML = '<option value="">Todos</option>';
  Object.values(state.employees).sort((a, b) => a.name.localeCompare(b.name)).forEach((employee) => {
    employeeFilter.append(new Option(`${employee.name} (${employee.id})`, employee.id));
  });
  if (state.employees[currentValue]) employeeFilter.value = currentValue;
  state.filters.employeeFilter = employeeFilter.value;
}

function downloadCsv() {
  const rows = filteredRows();
  if (!rows.length) return;
  const header = ["Mes", "Data", "Funcionario", "Departamento", "Batidas", "Trabalhado", "Previsto", "Credito", "Debito", "Saldo", "Observacao", "Alertas"];
  const lines = rows.map((row) => [
    row.monthLabel,
    row.dateLabel,
    row.employee.name,
    row.employee.department,
    row.punchLabels.join(" | "),
    formatDuration(row.workedMinutes),
    formatDuration(row.expectedMinutes),
    formatDuration(row.creditMinutes),
    formatDuration(row.debitMinutes),
    formatSignedDuration(row.balanceMinutes),
    row.note,
    row.alerts.join("; ")
  ]);
  downloadFile(`banco-de-horas${monthFilter.value ? `-${monthFilter.value}` : ""}.csv`, [header, ...lines].map((line) => line.map(csvCell).join(";")).join("\n"), "text/csv;charset=utf-8");
}

function downloadBackup() {
  saveState();
  downloadFile(`backup-ponto-funcionario-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(state, null, 2), "application/json;charset=utf-8");
}

async function restoreBackup(event) {
  const [file] = event.target.files;
  if (!file) return;
  try {
    state = { ...defaultState(), ...JSON.parse(await file.text()) };
    saveState();
    hydrate();
  } catch {
    alert("Nao foi possivel restaurar este backup.");
  } finally {
    restoreFile.value = "";
  }
}

function clearSavedData() {
  if (!confirm("Limpar todos os dados salvos neste computador?")) return;
  localStorage.removeItem(STATE_KEY);
  state = defaultState();
  records = [];
  dayRows = [];
  hydrate();
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function nextEmployeeId() {
  const ids = Object.keys(state.employees).map(Number).filter(Number.isFinite);
  return String((Math.max(0, ...ids) + 1));
}

function parsePunches(value) {
  if (!value) return null;
  const matches = String(value).match(/\d{1,2}:\d{2}/g);
  if (!matches) return [];
  return matches.map(parseTimeToMinutes).filter((minutes) => minutes !== null).sort((a, b) => a - b);
}

function parseTimeToMinutes(value) {
  if (!value) return null;
  const match = String(value).trim().match(/^(\d{1,3}):(\d{2})$/);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes) || minutes > 59) return null;
  return hours * 60 + minutes;
}

function formatMinutes(totalMinutes) {
  const hours = Math.floor(Math.abs(totalMinutes) / 60);
  const minutes = Math.abs(totalMinutes) % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function formatDuration(totalMinutes) {
  return formatMinutes(totalMinutes);
}

function formatSignedDuration(totalMinutes) {
  return `${totalMinutes < 0 ? "-" : "+"}${formatDuration(totalMinutes)}`;
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function cleanEmployeeId(value) {
  const clean = String(value ?? "").replace(/^0+/, "");
  return clean || "0";
}

function cleanText(value) {
  return String(value ?? "")
    .replaceAll("ÿ", "")
    .replaceAll("Ã‡", "C")
    .replaceAll("Ã§", "c")
    .replaceAll("Ã£", "a")
    .replaceAll("Ã¡", "a")
    .replaceAll("Ã©", "e")
    .replaceAll("Ãº", "u")
    .replaceAll("Ã³", "o")
    .replaceAll("Ãª", "e")
    .replaceAll("Ã´", "o")
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
