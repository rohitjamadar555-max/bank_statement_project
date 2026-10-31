import { extractPdfRows } from "./pdf-reader.js";





// Browser edition: selected statement contents are kept in this tab's JavaScript memory.
// This file intentionally makes no network requests and writes no persistent storage.
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_WORKSHEET_ROWS = 20000;
const MAX_WORKSHEET_COLUMNS = 100;
const $ = (id) => document.getElementById(id);
const fileInput = $("statement-file");
const headerSelect = $("header-row");
const mappingPanel = $("mapping-panel");
const worksheetSelect = $("worksheet-select");
const worksheetField = $("worksheet-field");
const analyzeButton = $("analyze-button");
const clearButton = $("clear-button");
const message = $("message");

let sourceRows = [];
let delimiter = ",";
let detectedHeaderIndex = 0;
let currentTransactions = [];
let currentWorkbook = null;

const aliases = {
  date: ["date", "txn date", "transaction date", "value date", "posting date", "trans date"],
  description: ["description", "narration", "particulars", "details", "transaction details", "remarks", "transaction", "merchant", "payee"],
  amount: ["amount", "txn amount", "transaction amount", "withdrawal deposit", "value"],
  debit: ["debit", "withdrawal", "withdrawals", "dr", "debit amount", "withdrawal amount"],
  credit: ["credit", "deposit", "deposits", "cr", "credit amount", "deposit amount"],
  type: ["type", "transaction type", "dr cr", "dr/cr", "debit credit", "transaction mode"]
};

const categoryRules = [
  ["food", ["restaurant", "food", "cafe", "coffee", "swiggy", "zomato", "bakery", "grocery", "supermarket"]],
  ["transport", ["uber", "ola", "taxi", "metro", "fuel", "petrol", "parking", "bus", "train"]],
  ["bills", ["electricity", "water bill", "internet", "broadband", "mobile recharge", "airtel", "jio", "gas bill"]],
  ["shopping", ["amazon", "flipkart", "shopping", "store", "mall", "clothing", "fashion"]],
  ["entertainment", ["movie", "cinema", "netflix", "spotify", "hotstar", "ticket", "game"]],
  ["health", ["hospital", "pharmacy", "medical", "clinic", "doctor", "health"]],
  ["housing", ["rent", "mortgage", "maintenance", "housing"]],
  ["income", ["salary", "bonus", "dividend", "interest"]],
  ["fees", ["fee", "charge", "gst", "interest", "penalty"]]
];

function normalizeHeading(value) {
  return String(value ?? "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/([a-z])\1+/g, "$1")
    .replace(/[^a-z0-9]+/g, "").trim();
}

const normalizedAliases = Object.fromEntries(
  Object.entries(aliases).map(([key, values]) => [key, values.map(normalizeHeading)])
);

function parseCsv(text, separator) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"' && field.length === 0) {
      quoted = true;
    } else if (char === separator) {
      row.push(field);
      field = "";
    } else if (char === "\n" || char === "\r") {
      row.push(field);
      if (row.some((cell) => cell.trim() !== "")) rows.push(row);
      row = [];
      field = "";
      if (char === "\r" && text[i + 1] === "\n") i += 1;
    } else {
      field += char;
    }
  }
  if (quoted) throw new Error("A quoted CSV value was not closed. Export the file again with standard CSV quoting.");
  row.push(field);
  if (row.some((cell) => cell.trim() !== "")) rows.push(row);
  return rows;
}

function rowMatches(row) {
  const found = {};
  const headings = row.map(normalizeHeading);
  for (const [key, choices] of Object.entries(normalizedAliases)) {
    for (const choice of choices) {
      const index = headings.indexOf(choice);
      if (index >= 0) {
        found[key] = index;
        break;
      }
    }
  }
  const complete = found.date !== undefined && found.description !== undefined &&
    (found.amount !== undefined || (found.debit !== undefined && found.credit !== undefined));
  return { found, complete };
}

function findHeader(rows) {
  const limit = Math.min(rows.length, 40);
  let best = { index: -1, found: {}, score: -1 };
  for (let i = 0; i < limit; i += 1) {
    const match = rowMatches(rows[i]);
    const score = (match.complete ? 100 : 0) + Object.keys(match.found).length * 10;
    if (score > best.score) best = { index: i, found: match.found, score };
  }
  return best.index >= 0 && best.score >= 20 ? best : { index: -1, found: {}, score: 0 };
}

function chooseCsv(text) {
  const candidates = [",", ";", "\t", "|"];
  let best = null;
  for (const candidate of candidates) {
    try {
      const rows = parseCsv(text, candidate);
      const header = findHeader(rows);
      const widths = rows.slice(0, 40).map((r) => r.length);
      const counts = new Map();
      widths.forEach((width) => counts.set(width, (counts.get(width) || 0) + 1));
      const consistency = Math.max(0, ...counts.values());
      const score = header.score * 100 + consistency * 2 + (Math.max(0, ...widths) > 1 ? 1 : 0);
      if (!best || score > best.score) best = { rows, delimiter: candidate, header, score };
    } catch (_error) {
      // A different candidate may still be valid; report a useful error if none are.
    }
  }
  if (!best || best.rows.length === 0) throw new Error("The CSV is empty or could not be read. Check that it is a valid UTF-8 CSV file.");
  if (best.header.index < 0) {
    // Keep unfamiliar headings usable: choose the widest likely header row and
    // let the user select the row and map each field manually.
    const limit = Math.min(best.rows.length, 40);
    let fallbackIndex = 0;
    let fallbackScore = -1;
    for (let index = 0; index < limit; index += 1) {
      const cells = best.rows[index].filter((cell) => String(cell).trim() !== "");
      const textCells = cells.filter((cell) => /[a-z]/i.test(cell)).length;
      const score = cells.length * 10 + textCells;
      if (score > fallbackScore) { fallbackScore = score; fallbackIndex = index; }
    }
    best.header = { index: fallbackIndex, found: {}, score: 0, detected: false };
  } else {
    best.header.detected = true;
  }
  return best;
}

function prepareWorkbookRows(rows) {
  const cleanRows = rows.map((row) => row.map((cell) => String(cell ?? "")));
  if (!cleanRows.some((row) => row.some((cell) => cell.trim() !== ""))) {
    throw new Error("This worksheet is empty. Choose a worksheet that contains transactions.");
  }
  const header = findHeader(cleanRows);
  const prepared = { rows: cleanRows, delimiter: "spreadsheet", header };
  if (header.index < 0) {
    const limit = Math.min(cleanRows.length, 40);
    let fallbackIndex = 0;
    let fallbackScore = -1;
    for (let index = 0; index < limit; index += 1) {
      const cells = cleanRows[index].filter((cell) => cell.trim() !== "");
      const textCells = cells.filter((cell) => /[a-z]/i.test(cell)).length;
      const score = cells.length * 10 + textCells;
      if (score > fallbackScore) { fallbackScore = score; fallbackIndex = index; }
    }
    prepared.header = { index: fallbackIndex, found: {}, score: 0, detected: false };
  } else {
    prepared.header.detected = true;
  }
  return prepared;
}

function setMessage(text, kind = "info") {
  message.hidden = !text;
  message.className = `message ${kind}`;
  message.textContent = text;
}

function addOption(select, label, value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  select.append(option);
}

function columnSelect(id) {
  return $(id);
}

function populateMappings(headerIndex, detected = true) {
  const header = sourceRows[headerIndex] || [];
  const count = Math.max(header.length, ...sourceRows.slice(headerIndex + 1).map((row) => row.length), 0);
  const match = rowMatches(header).found;
  const mappingIds = ["map-date", "map-description", "map-amount", "map-debit", "map-credit", "map-type"];
  mappingIds.forEach((id) => {
    const select = columnSelect(id);
    select.replaceChildren();
    addOption(select, "— Not selected —", "");
    for (let i = 0; i < count; i += 1) {
      const name = String(header[i] ?? "").trim() || `Column ${i + 1}`;
      addOption(select, `${name} (column ${i + 1})`, String(i));
    }
  });
  const keyToId = { date: "map-date", description: "map-description", amount: "map-amount", debit: "map-debit", credit: "map-credit", type: "map-type" };
  if (detected) {
    Object.entries(keyToId).forEach(([key, id]) => {
      if (match[key] !== undefined) $(id).value = String(match[key]);
    });
  }
  validateMapping();
}

function validateMapping() {
  const date = $("map-date").value;
  const description = $("map-description").value;
  const amount = $("map-amount").value;
  const debit = $("map-debit").value;
  const credit = $("map-credit").value;
  const usableAmount = amount !== "" || (debit !== "" && credit !== "");
  const selections = [date, description, amount, debit, credit].filter((value) => value !== "");
  const duplicates = new Set(selections).size !== selections.length;
  const valid = date !== "" && description !== "" && usableAmount && !duplicates;
  analyzeButton.disabled = !valid;
  $("mapping-status").textContent = duplicates
    ? "Choose a different column for each field."
    : valid
      ? "Column choices are ready. Review them, then analyze."
      : "Select Date, Description, and Amount, or select both Debit and Credit.";
  return valid;
}

function addHeaderChoices() {
  headerSelect.replaceChildren();
  const limit = Math.min(sourceRows.length, 40);
  for (let index = 0; index < limit; index += 1) {
    const preview = sourceRows[index].slice(0, 5).map((cell) => String(cell).trim()).filter(Boolean).join(" · ");
    addOption(headerSelect, `Row ${index + 1}: ${preview || "(blank)"}`, String(index));
  }
  headerSelect.value = String(detectedHeaderIndex);
  populateMappings(detectedHeaderIndex, sourceRows.length > 0);
}

function loadWorkbookSheet(sheetName) {
  try {
    if (!currentWorkbook || !window.XLSX) throw new Error("The local Excel reader did not load. Reload the page and try again.");
    const worksheet = currentWorkbook.Sheets[sheetName];
    if (!worksheet) throw new Error("This worksheet could not be opened.");
    const rangeText = worksheet["!fullref"] || worksheet["!ref"];
    if (rangeText) {
      const range = XLSX.utils.decode_range(rangeText);
      if (range.e.r + 1 > MAX_WORKSHEET_ROWS) throw new Error(`This worksheet has more than ${MAX_WORKSHEET_ROWS.toLocaleString("en-IN")} rows. Use a smaller worksheet.`);
      if (range.e.c + 1 > MAX_WORKSHEET_COLUMNS) throw new Error(`This worksheet has more than ${MAX_WORKSHEET_COLUMNS} columns. Use a narrower worksheet.`);
    }
    const rows = XLSX.utils.sheet_to_json(worksheet, {
      header: 1,
      raw: false,
      defval: "",
      blankrows: false,
      dateNF: "yyyy-mm-dd"
    });
    const parsed = prepareWorkbookRows(rows);
    sourceRows = parsed.rows;
    delimiter = "spreadsheet";
    detectedHeaderIndex = parsed.header.index;
    addHeaderChoices();
    mappingPanel.hidden = false;
    const file = fileInput.files && fileInput.files[0];
    const fileSize = file ? `${(file.size / 1024).toFixed(1)} KB` : "";
    $("file-status").textContent = `${file ? `${file.name} · ${fileSize} · ` : ""}worksheet: ${sheetName} · read in this tab`;
    const headerNote = parsed.header.detected
      ? "A likely transaction header was detected."
      : `Headings were not recognized automatically; row ${detectedHeaderIndex + 1} is a guess. Select the correct header row and map columns yourself.`;
    setMessage(`Excel worksheet “${sheetName}” opened locally. Confirm the column choices below. ${headerNote}`, parsed.header.detected ? "success" : "info");
  } catch (error) {
    sourceRows = [];
    mappingPanel.hidden = true;
    setMessage(error.message || "Could not read this Excel worksheet.", "error");
  }
}

function parseAmount(raw) {
  let value = String(raw ?? "").replace(/\u0000/g, "").trim();
  if (!value) return null;
  let negative = /^\(.*\)$/.test(value);
 value = value.replace(/^\(|\)$/g, "").replace(/[\u2212\u201C\u201D]/g, "-");
  if (/\b(?:dr|debit)\b\.?$/i.test(value)) negative = true;
  if (/\b(?:cr|credit)\b\.?$/i.test(value)) value = value.replace(/\b(?:cr|credit)\b\.?$/i, "");
 value = value.replace(/\b(?:INR|Rs\.?|Rupees?)\b/gi, "").replace(/\u20B9/g, "").replace(/\s/g, "");
  value = value.replace(/[^0-9,.-]/g, "");
  if (!value || !/^-?[0-9][0-9.,]*$/.test(value)) return null;
  const lastComma = value.lastIndexOf(",");
  const lastDot = value.lastIndexOf(".");
  if (lastComma >= 0 && lastDot >= 0) {
    const decimal = lastComma > lastDot ? "," : ".";
    const grouping = decimal === "," ? "." : ",";
    value = value.split(grouping).join("");
    if (decimal === ",") value = value.replace(",", ".");
  } else if (lastComma >= 0) {
    const digitsAfter = value.length - lastComma - 1;
    if (digitsAfter === 1 || digitsAfter === 2) value = value.replace(",", ".");
    else value = value.replace(/,/g, "");
  } else if ((value.match(/\./g) || []).length > 1) {
    const last = value.lastIndexOf(".");
    value = value.slice(0, last).replace(/\./g, "") + value.slice(last);
  }
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return negative ? -Math.abs(number) : number;
}

function parseDate(raw, order) {
  const value = String(raw ?? "").trim();
  if (!value) return null;
  let year; let month; let day;
  let match = value.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/);
  if (match) {
    year = Number(match[1]); month = Number(match[2]); day = Number(match[3]);
  } else {
    match = value.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/);
    if (match) {
      const first = Number(match[1]); const second = Number(match[2]);
      year = Number(match[3]);
      if (year < 100) year += year < 70 ? 2000 : 1900;
      if (order === "MDY") { month = first; day = second; }
      else { day = first; month = second; }
    } else {
      const parsed = Date.parse(value);
      if (!Number.isFinite(parsed)) return null;
      const date = new Date(parsed);
      year = date.getUTCFullYear(); month = date.getUTCMonth() + 1; day = date.getUTCDate();
    }
  }
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return date.toISOString().slice(0, 10);
}

function classify(description) {
  const text = String(description).toLowerCase();
  for (const [category, words] of categoryRules) {
    if (words.some((word) => text.includes(word))) return category;
  }
  return "uncategorized";
}

function amountForRow(row, rowNumber) {
  const amountColumn = $("map-amount").value;
  let amount;
  if (amountColumn !== "") {
    amount = parseAmount(row[Number(amountColumn)]);
    if (amount === null) throw new Error("Amount is blank or unreadable.");
    const typeColumn = $("map-type").value;
    if (typeColumn !== "") {
      const type = String(row[Number(typeColumn)] ?? "").toLowerCase();
      if (/\b(?:debit|withdrawal|payment|dr)\b/.test(type)) amount = -Math.abs(amount);
      if (/\b(?:credit|deposit|received|cr)\b/.test(type)) amount = Math.abs(amount);
    }
  } else {
    const debitRaw = String(row[Number($("map-debit").value)] ?? "").trim();
    const creditRaw = String(row[Number($("map-credit").value)] ?? "").trim();
    const debit = debitRaw ? parseAmount(debitRaw) : 0;
    const credit = creditRaw ? parseAmount(creditRaw) : 0;
    if (debit === null || credit === null) throw new Error("Debit or Credit value is unreadable.");
    if (!debitRaw && !creditRaw) throw new Error("Both Debit and Credit are blank.");
    if (debit !== 0 && credit !== 0) throw new Error("Both Debit and Credit contain non-zero values; check this row.");
    amount = debit !== 0 ? -Math.abs(debit) : Math.abs(credit);
  }
  return amount;
}

function buildTransactions() {
  if (!validateMapping()) return null;
  const headerIndex = Number(headerSelect.value);
  const dateColumn = Number($("map-date").value);
  const descriptionColumn = Number($("map-description").value);
  const order = $("date-order").value;
  const transactions = [];
  const issues = [];
  for (let i = headerIndex + 1; i < sourceRows.length; i += 1) {
    const row = sourceRows[i];
    if (!row.some((cell) => String(cell ?? "").trim() !== "")) continue;
    const csvRow = i + 1;
    const date = parseDate(row[dateColumn], order);
    const description = String(row[descriptionColumn] ?? "").trim();
    if (!date) { issues.push({ row: csvRow, issue: "Date is blank or unreadable." }); continue; }
    if (!description) { issues.push({ row: csvRow, issue: "Description is blank." }); continue; }
    try {
      const amount = amountForRow(row, csvRow);
      transactions.push({ date, description, amount, category: classify(description), row: csvRow });
    } catch (error) {
      issues.push({ row: csvRow, issue: error.message });
    }
  }
  if (transactions.length === 0) throw new Error("No complete transactions were recognized. Check the column mapping and date order.");
  return { transactions, issues };
}

const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

function td(row, text, tag = "td") {
  const cell = document.createElement(tag);
  cell.textContent = String(text);
  row.append(cell);
  return cell;
}

function setTableRows(bodyId, rows, columns) {
  const body = $(bodyId);
  body.replaceChildren();
  rows.forEach((item) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => td(tr, column(item)));
    body.append(tr);
  });
}

function renderResults(transactions, issues) {
  const spending = transactions.filter((item) => item.amount < 0).reduce((sum, item) => sum + Math.abs(item.amount), 0);
  const income = transactions.filter((item) => item.amount > 0).reduce((sum, item) => sum + item.amount, 0);
  const uncategorized = transactions.filter((item) => item.category === "uncategorized").length;
  const summaries = [
    ["Transactions", transactions.length],
    ["Spending", money.format(spending)],
    ["Income", money.format(income)],
    ["Uncategorized", `${((uncategorized / transactions.length) * 100).toFixed(1)}%`]
  ];
  const summaryRoot = $("summary-cards");
  summaryRoot.replaceChildren();
  summaries.forEach(([label, value]) => {
    const card = document.createElement("article");
    card.className = "summary-card";
    const caption = document.createElement("span"); caption.textContent = label;
    const strong = document.createElement("strong"); strong.textContent = String(value);
    card.append(caption, strong); summaryRoot.append(card);
  });

  const totals = new Map();
  transactions.filter((item) => item.amount < 0).forEach((item) => totals.set(item.category, (totals.get(item.category) || 0) + Math.abs(item.amount)));
  const categoryRows = [...totals.entries()].sort((a, b) => b[1] - a[1]).map(([category, value]) => ({ category, value }));
  setTableRows("category-rows", categoryRows, [(item) => item.category, (item) => money.format(item.value)]);

  const duplicates = new Map();
  transactions.forEach((item) => {
    const key = `${item.date}|${item.description.toLowerCase().replace(/\s+/g, " ")}|${item.amount.toFixed(2)}`;
    if (!duplicates.has(key)) duplicates.set(key, []);
    duplicates.get(key).push(item);
  });
  const duplicateRows = [...duplicates.values()].filter((group) => group.length > 1).flatMap((group) => group.map((item) => ({ ...item, count: group.length })));
  $("duplicates-card").hidden = duplicateRows.length === 0;
  setTableRows("duplicate-rows", duplicateRows, [(item) => item.date, (item) => `${item.description} (row ${item.row}; ${item.count} similar rows)`, (item) => money.format(item.amount)]);

  $("issues-card").hidden = issues.length === 0;
  $("issues-copy").textContent = issues.length ? `${issues.length} row(s) were left out of the totals. Review these rows and the original statement.` : "";
  setTableRows("issue-rows", issues, [(item) => item.row, (item) => item.issue]);
  setTableRows("transaction-rows", transactions, [(item) => item.date, (item) => item.description, (item) => money.format(item.amount), (item) => item.category]);
  $("results-panel").hidden = false;
}

function clearRenderedResults() {
  $("summary-cards").replaceChildren();
  ["category-rows", "issue-rows", "duplicate-rows", "transaction-rows"].forEach((id) => $(id).replaceChildren());
  $("issues-card").hidden = true;
  $("duplicates-card").hidden = true;
  $("results-panel").hidden = true;
}

fileInput.addEventListener("change", async () => {
  const file = fileInput.files && fileInput.files[0];
  // Drop any prior statement immediately, including when the new selection is
  // unsupported or cannot be parsed.
  sourceRows = [];
  currentTransactions = [];
  currentWorkbook = null;
  headerSelect.replaceChildren();
  worksheetSelect.replaceChildren();
  worksheetField.hidden = true;
  ["map-date", "map-description", "map-amount", "map-debit", "map-credit", "map-type"].forEach((id) => $(id).replaceChildren());
  clearRenderedResults();
  mappingPanel.hidden = true;
  $("file-status").textContent = "The file is opened locally in this tab.";
  setMessage("");
  if (!file) return;
  const extension = file.name.toLowerCase().split(".").pop();
  const isCsv = extension === "csv" || file.type === "text/csv";
  const isExcel = extension === "xlsx" || extension === "xls";
  const isPdf = extension === "pdf" || file.type === "application/pdf";
  if (!isCsv && !isExcel && !isPdf) {
    setMessage("Choose a CSV (.csv), Excel workbook (.xlsx), or Excel 97”“2003 workbook (.xls) file.", "error");
    fileInput.value = "";
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    setMessage("This file is larger than the 10 MB limit for this browser edition.", "error");
    fileInput.value = "";
    return;
  }
  try {
    if (isPdf) {
      const pdfRows = await extractPdfRows(file);
      const parsed = prepareWorkbookRows(pdfRows);
      sourceRows = parsed.rows;
      delimiter = "pdf";
      detectedHeaderIndex = parsed.header.index;
      addHeaderChoices();
      mappingPanel.hidden = false;
      $("file-status").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB · read locally in this tab`;
      const headerNote = parsed.header.detected
        ? `Detected a likely header on row ${detectedHeaderIndex + 1}.`
        : `Select the correct header row and map columns manually.`;
      setMessage(`PDF text extracted locally. ${headerNote} Verify all columns before analysis.`, parsed.header.detected ? "success" : "info");
    } else if (isCsv) {
      const text = (await file.text()).replace(/^\uFEFF/, "");
      const parsed = chooseCsv(text);
      sourceRows = parsed.rows;
      delimiter = parsed.delimiter;
      detectedHeaderIndex = parsed.header.index;
      addHeaderChoices();
      mappingPanel.hidden = false;
      $("file-status").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB · read in this tab`;
      const delimiterName = delimiter === "\t" ? "tab" : delimiter === "|" ? "pipe" : delimiter === ";" ? "semicolon" : "comma";
      const headerNote = parsed.header.detected
        ? `Detected a likely header on row ${detectedHeaderIndex + 1}.`
        : `Headings were not recognized automatically; row ${detectedHeaderIndex + 1} is a guess. Select the correct header row and map columns yourself.`;
      setMessage(`CSV opened locally. Detected a ${delimiterName}-separated file. ${headerNote} Confirm the column choices below.`, parsed.header.detected ? "success" : "info");
    } else {
      if (!window.XLSX) throw new Error("The local Excel reader did not load. Reload the page and try again.");
      const workbookBytes = await file.arrayBuffer();
      currentWorkbook = XLSX.read(workbookBytes, {
        type: "array",
        cellDates: true,
        sheetRows: MAX_WORKSHEET_ROWS + 1
      });
      const names = currentWorkbook.SheetNames || [];
      if (names.length === 0) throw new Error("No worksheets were found in this Excel file.");
      names.forEach((name, index) => addOption(worksheetSelect, name || `Worksheet ${index + 1}`, name));
      worksheetField.hidden = false;
      worksheetSelect.value = names[0];
      loadWorkbookSheet(worksheetSelect.value);
    }
  } catch (error) {
    sourceRows = [];
    currentWorkbook = null;
    worksheetSelect.replaceChildren();
    worksheetField.hidden = true;
    mappingPanel.hidden = true;
    setMessage(error.message || "Could not read this file.", "error");
    fileInput.value = "";
  }
});

headerSelect.addEventListener("change", () => populateMappings(Number(headerSelect.value), true));
worksheetSelect.addEventListener("change", () => {
  sourceRows = [];
  currentTransactions = [];
  clearRenderedResults();
  loadWorkbookSheet(worksheetSelect.value);
});
["map-date", "map-description", "map-amount", "map-debit", "map-credit", "map-type"].forEach((id) => $(id).addEventListener("change", validateMapping));

analyzeButton.addEventListener("click", () => {
  try {
    const result = buildTransactions();
    if (!result) return;
    currentTransactions = result.transactions;
    renderResults(result.transactions, result.issues);
    setMessage(`Analysis finished in this tab: ${result.transactions.length} transaction(s) included and ${result.issues.length} row(s) flagged for review.`, result.issues.length ? "info" : "success");
  } catch (error) {
    $("results-panel").hidden = true;
    setMessage(error.message || "Could not analyze this CSV.", "error");
  }
});

clearButton.addEventListener("click", () => {
  fileInput.value = "";
  sourceRows = [];
  currentTransactions = [];
  currentWorkbook = null;
  detectedHeaderIndex = 0;
  headerSelect.replaceChildren();
  worksheetSelect.replaceChildren();
  worksheetField.hidden = true;
  ["map-date", "map-description", "map-amount", "map-debit", "map-credit", "map-type"].forEach((id) => $(id).replaceChildren());
  $("file-status").textContent = "The file is opened locally in this tab.";
  mappingPanel.hidden = true;
  clearRenderedResults();
  setMessage("File and visible results cleared from this app tab.", "success");
});
