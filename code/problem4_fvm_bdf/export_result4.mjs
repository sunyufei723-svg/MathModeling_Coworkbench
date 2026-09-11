import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function option(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) throw new Error(`missing required option ${name}`);
  return process.argv[index + 1];
}


function writeRowsInChunks(sheet, startRow, rows, columnCount, chunkSize = 300) {
  for (let offset = 0; offset < rows.length; offset += chunkSize) {
    const chunk = rows.slice(offset, offset + chunkSize);
    sheet.getRangeByIndexes(startRow + offset, 0, chunk.length, columnCount).values = chunk;
  }
}


const templatePath = option("--template");
const payloadPath = option("--payload");
const outputPath = option("--output");
const copyPath = option("--copy-output");
const previewDir = option("--preview-dir");
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const sheetNames = workbook.worksheets.items.map((sheet) => sheet.name);
if (sheetNames.length !== 1 || sheetNames[0] !== "水分浓度") {
  throw new Error(`template sheets changed: ${JSON.stringify(sheetNames)}`);
}

const sheet = workbook.worksheets.getItem("水分浓度");
const columnCount = payload.headers.length;
const rowCount = payload.rows.length;
if (columnCount !== 22 || rowCount !== payload.metadata.first_strict_60s_time_s / 60) {
  throw new Error(`unexpected payload dimensions: columns=${columnCount}, rows=${rowCount}`);
}
for (let index = 0; index < rowCount; index += 1) {
  if (payload.rows[index][0] !== (index + 1) * 60) {
    throw new Error(`non-regular time at row ${index + 2}`);
  }
}
if (!(payload.metadata.previous_max_moisture >= 0.15 && payload.metadata.first_strict_report_max_moisture < 0.15)) {
  throw new Error("strict threshold metadata failed");
}

sheet.getRange("A2:V5000").clear({ applyTo: "contents" });
sheet.getRangeByIndexes(0, 0, 1, columnCount).values = [payload.headers];
writeRowsInChunks(sheet, 1, payload.rows, columnCount);
sheet.getRange(`A2:A${rowCount + 1}`).format.numberFormat = "0";
sheet.getRange(`B2:V${rowCount + 1}`).format.numberFormat = "0.0000";
sheet.getRange("A1:A1").format.columnWidth = 24;
sheet.getRange("B1:U1").format.columnWidth = 10;
sheet.getRange("V1:V1").format.columnWidth = 14;
sheet.freezePanes.freezeRows(1);

workbook.recalculate();
const firstCheck = await workbook.inspect({
  kind: "table",
  range: "水分浓度!A1:V5",
  include: "values,formulas",
  tableMaxRows: 5,
  tableMaxCols: 22,
  maxChars: 9000,
});
const lastCheck = await workbook.inspect({
  kind: "table",
  range: `水分浓度!A${Math.max(1, rowCount - 1)}:V${rowCount + 1}`,
  include: "values,formulas",
  tableMaxRows: 3,
  tableMaxCols: 22,
  maxChars: 9000,
});
const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});

await fs.mkdir(previewDir, { recursive: true });
for (const [name, range] of [
  ["result4_first", "A1:V28"],
  ["result4_last", `A${Math.max(1, rowCount - 18)}:V${rowCount + 1}`],
]) {
  const preview = await workbook.render({ sheetName: "水分浓度", range, scale: 1.25, format: "png" });
  await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
await fs.mkdir(path.dirname(copyPath), { recursive: true });
await fs.copyFile(outputPath, copyPath);

const saved = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedSheet = saved.worksheets.getItem("水分浓度");
const savedLast = savedSheet.getRange(`A${rowCount + 1}:V${rowCount + 1}`).values[0];
const savedPrevious = savedSheet.getRange(`A${rowCount}:V${rowCount}`).values[0];
const finalMaximum = Math.max(...savedLast.slice(1).filter((value) => typeof value === "number"));
const previousMaximum = Math.max(...savedPrevious.slice(1).filter((value) => typeof value === "number"));
if (
  saved.worksheets.items.length !== 1
  || savedLast[0] !== payload.metadata.first_strict_60s_time_s
  || !(previousMaximum >= 0.15 && finalMaximum < 0.15)
) {
  throw new Error("saved workbook structure, time, or threshold verification failed");
}
console.log(JSON.stringify({
  outputPath,
  copyPath,
  rowCount,
  columnCount,
  usedRange: savedSheet.getUsedRange().address,
  previousMaximum,
  finalMaximum,
  firstCheck: firstCheck.ndjson,
  lastCheck: lastCheck.ndjson,
  formulaErrors: formulaErrors.ndjson,
  savedLast,
}, null, 2));
