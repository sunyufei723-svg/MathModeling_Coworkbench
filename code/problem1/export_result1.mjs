import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function option(name, required = true) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) {
    if (required) throw new Error(`missing required option ${name}`);
    return null;
  }
  return process.argv[index + 1];
}

function columnName(indexOneBased) {
  let value = indexOneBased;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}

const templatePath = option("--template");
const payloadPath = option("--payload");
const outputPath = option("--output");
const copyPath = option("--copy", false);
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));

const header = [
  "时间\\到药材中心的距离",
  ...payload.radius_cm.map((value) => Number(value).toFixed(1)),
];
const rowCount = payload.time_s.length + 1;
const colCount = header.length;
const lastColumn = columnName(colCount);

function updateSheet(sheetName, fieldName) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const matrix = [
    header,
    ...payload.time_s.map((time, index) => [time, ...payload[fieldName][index]]),
  ];
  const usedRange = sheet.getRange(`A1:${lastColumn}${rowCount}`);
  usedRange.values = matrix;
  usedRange.format.font = { name: "Microsoft YaHei", size: 10 };
  usedRange.format.horizontalAlignment = "center";
  usedRange.format.verticalAlignment = "center";
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: "#1F4E78",
    font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange(`A2:A${rowCount}`).format = {
    fill: "#DCE6F1",
    font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#1F1F1F" },
    horizontalAlignment: "center",
  };
  sheet.getRange(`A2:A${rowCount}`).format.numberFormat = "0";
  sheet.getRange(`B2:${lastColumn}${rowCount}`).format.numberFormat = "0.0000";
  sheet.getRange("A:A").format.columnWidth = 25;
  sheet.getRange(`B:${lastColumn}`).format.columnWidth = 10;
  sheet.getRange("1:1").format.rowHeight = 30;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
}

updateSheet("温度", "temperature_c");
updateSheet("水分浓度", "moisture");
workbook.recalculate();
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
if (copyPath) {
  await fs.mkdir(path.dirname(copyPath), { recursive: true });
  const copy = await SpreadsheetFile.exportXlsx(workbook);
  await copy.save(copyPath);
}
console.log(`output: ${outputPath}`);
if (copyPath) console.log(`copy: ${copyPath}`);
