
import * as pdfjsLib from "./vendor/pdf.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "./vendor/pdf.worker.mjs",
  import.meta.url
).toString();

const MAX_PDF_PAGES = 100;

function groupTextIntoLines(items) {
  const positioned = items
    .filter((item) => item.str && item.str.trim())
    .map((item) => ({
      text: item.str.trim(),
      x: item.transform[4],
      y: item.transform[5],
      width: item.width || 0,
      height: Math.abs(item.transform[3]) || 10
    }))
    .sort((a, b) => {
      if (Math.abs(b.y - a.y) > 2) return b.y - a.y;
      return a.x - b.x;
    });

  const lines = [];

  for (const item of positioned) {
    let line = lines.find(
      (candidate) => Math.abs(candidate.y - item.y) <= 2.5
    );

    if (!line) {
      line = { y: item.y, items: [] };
      lines.push(line);
    }

    line.items.push(item);
  }

  return lines
    .map((line) => {
      line.items.sort((a, b) => a.x - b.x);

      let text = "";
      let previous = null;

      for (const item of line.items) {
        if (previous) {
          const gap = item.x - (previous.x + previous.width);
          const fontSize = Math.max(previous.height, item.height);

          if (gap > fontSize * 1.2) {
            text += "  ";
          } else if (gap > 1) {
            text += " ";
          }
        }

        text += item.text;
        previous = item;
      }

      return {
        text: text.trim(),
        items: line.items
      };
    })
    .sort((a, b) => b.items[0].y - a.items[0].y);
}

function isTransactionHeader(text) {
  const normalized = text.toLowerCase().replace(/[_-]/g, " ");

  const hasDate = /\bdate\b/.test(normalized);
  const hasDescription =
    /\b(description|details|narration|particulars|remarks)\b/.test(normalized);
  const hasAmount =
    /\b(amount|debit|credit|withdrawal|deposit)\b/.test(normalized);

  return hasDate && hasDescription && hasAmount;
}

function splitLineIntoCells(line) {
  return line.text
    .split(/\s{2,}/)
    .map((cell) => cell.trim())
    .filter(Boolean);
}

function buildRows(lines) {
  const headerIndex = lines.findIndex((line) =>
    isTransactionHeader(line.text)
  );

  if (headerIndex === -1) {
    throw new Error(
      "No recognizable transaction header was found in this PDF. " +
      "This reader currently supports selectable-text PDFs with recognizable column headings."
    );
  }

  const headerLine = lines[headerIndex];
  const headerItems = headerLine.items;

  // Use the horizontal positions of the header cells to identify
  // the corresponding columns in transaction rows.
  const headerCells = splitLineIntoCells(headerLine);

  if (headerCells.length < 3) {
    throw new Error(
      "The PDF headings could not be separated into columns. " +
      "Try exporting the statement as CSV or Excel."
    );
  }

  const columnStarts = [];
  let itemIndex = 0;

  for (const cell of headerCells) {
    const firstWord = cell.split(/\s+/)[0].toLowerCase();

    while (
      itemIndex < headerItems.length &&
      !headerItems[itemIndex].text.toLowerCase().includes(firstWord)
    ) {
      itemIndex += 1;
    }

    if (itemIndex < headerItems.length) {
      columnStarts.push({
        label: cell,
        x: headerItems[itemIndex].x
      });
      itemIndex += 1;
    }
  }

  if (columnStarts.length < 3) {
    throw new Error(
      "Could not identify the PDF table's column positions reliably."
    );
  }

  const rows = [headerCells];

  for (const line of lines.slice(headerIndex + 1)) {
    if (!line.text) continue;

    // Ignore repeated page headings.
    if (isTransactionHeader(line.text)) continue;

    const cells = Array(columnStarts.length).fill("");

    for (const item of line.items) {
      let columnIndex = -1;

      for (let index = 0; index < columnStarts.length; index += 1) {
        if (item.x >= columnStarts[index].x - 2) {
          columnIndex = index;
        } else {
          break;
        }
      }

      if (columnIndex === -1) continue;

      cells[columnIndex] = cells[columnIndex]
        ? `${cells[columnIndex]} ${item.text}`
        : item.text;
    }

    if (cells.some((cell) => cell.trim())) {
      rows.push(cells.map((cell) => cell.trim()));
    }
  }

  if (rows.length < 2) {
    throw new Error("No transaction rows were extracted from this PDF.");
  }

  return rows;
}

export async function extractPdfRows(file) {
  if (!(file instanceof File)) {
    throw new Error("Please select a valid PDF file.");
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("The selected file is not a PDF.");
  }

  const bytes = await file.arrayBuffer();

  let document;
  let loadingTask;

  try {
    loadingTask = pdfjsLib.getDocument({
      data: new Uint8Array(bytes)
    });

    document = await loadingTask.promise;

    if (document.numPages > MAX_PDF_PAGES) {
      throw new Error(
        `This PDF has ${document.numPages} pages. The current limit is ${MAX_PDF_PAGES} pages.`
      );
    }

    const allLines = [];

    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
      const page = await document.getPage(pageNumber);
      const content = await page.getTextContent();

      if (!content.items.length) continue;

      allLines.push(...groupTextIntoLines(content.items));
    }

    if (!allLines.length) {
      throw new Error(
        "This PDF contains no selectable text. Scanned PDF support will be added separately."
      );
    }

    return buildRows(allLines);
  } catch (error) {
    if (error.name === "PasswordException") {
      throw new Error("This PDF is password-protected. Remove its password and try again.");
    }

    throw new Error(error.message || "Could not extract text from this PDF.");
  } finally {
    if (loadingTask) {
      await loadingTask.destroy();
    }
  }
}
