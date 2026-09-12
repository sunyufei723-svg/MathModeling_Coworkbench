import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function option(name, required = true) {
  const index = process.argv.indexOf(name);
  if (index >= 0 && index + 1 < process.argv.length) return process.argv[index + 1];
  if (required) throw new Error(`missing required option ${name}`);
  return null;
}


function writeRowsInChunks(sheet, startRow, rows, columnCount, chunkSize = 500) {
  for (let offset = 0; offset < rows.length; offset += chunkSize) {
    const chunk = rows.slice(offset, offset + chunkSize);
    sheet.getRangeByIndexes(startRow + offset, 0, chunk.length, columnCount).values = chunk;
  }
}


const templatePath = option("--template");
const payloadPath = option("--payload");
const outputPath = option("--output");
const copyPath = option("--copy-output", false);
const previewDir = option("--preview-dir");

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const columnCount = payload.headers.length;
const dataRowCount = payload.temperature_rows.length;
if (columnCount !== 22 || dataRowCount !== 10800 || payload.moisture_rows.length !== dataRowCount) {
  throw new Error(`unexpected payload dimensions: columns=${columnCount}, temperature=${dataRowCount}, moisture=${payload.moisture_rows.length}`);
}

for (const [sheetName, rows] of [
  ["温度", payload.temperature_rows],
  ["水分浓度", payload.moisture_rows],
]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  sheet.getRangeByIndexes(0, 0, 1, columnCount).values = [payload.headers];
  writeRowsInChunks(sheet, 1, rows, columnCount);
  sheet.getRange(`A2:A${dataRowCount + 1}`).format.numberFormat = "0";
  sheet.getRange(`B2:V${dataRowCount + 1}`).format.numberFormat = "0.0000";
}

workbook.recalculate();
const temperatureCheck = await workbook.inspect({
  kind: "table",
  range: "温度!A1:V5",
  include: "values,formulas",
  tableMaxRows: 5,
  tableMaxCols: 22,
  maxChars: 8000,
});
const moistureCheck = await workbook.inspect({
  kind: "table",
  range: "水分浓度!A10798:V10801",
  include: "values,formulas",
  tableMaxRows: 4,
  tableMaxCols: 22,
  maxChars: 8000,
});
const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["温度", "水分浓度"]) {
  const preview = await workbook.render({
    sheetName,
    range: "A1:V30",
    scale: 1.25,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
if (copyPath) {
  await fs.mkdir(path.dirname(copyPath), { recursive: true });
  await fs.copyFile(outputPath, copyPath);
}

const saved = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedSummary = {
  temperatureFirst: saved.worksheets.getItem("温度").getRange("A1:V3").values,
  temperatureLast: saved.worksheets.getItem("温度").getRange("A10801:V10801").values,
  moistureFirst: saved.worksheets.getItem("水分浓度").getRange("A1:V3").values,
  moistureLast: saved.worksheets.getItem("水分浓度").getRange("A10801:V10801").values,
};
console.log(JSON.stringify({
  outputPath,
  copyPath,
  temperatureCheck: temperatureCheck.ndjson,
  moistureCheck: moistureCheck.ndjson,
  formulaErrors: formulaErrors.ndjson,
  savedSummary,
}, null, 2));
