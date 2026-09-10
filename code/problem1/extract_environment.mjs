import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function option(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) {
    throw new Error(`missing required option ${name}`);
  }
  return process.argv[index + 1];
}

const inputPath = option("--input");
const outputPath = option("--output");
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItemAt(0);
const values = sheet.getUsedRange().values;
const headers = values[0].map((value) => String(value).trim());
const required = ["时间", "温度", "水分浓度"];
const indices = Object.fromEntries(required.map((name) => [name, headers.indexOf(name)]));
for (const name of required) {
  if (indices[name] < 0) throw new Error(`附件1缺少“${name}”列`);
}

const rows = values.slice(1)
  .filter((row) => row[indices["时间"]] !== null && row[indices["时间"]] !== "")
  .map((row) => Object.fromEntries(required.map((name) => [name, Number(row[indices[name]])])));
if (rows.length < 2 || rows.some((row) => required.some((name) => !Number.isFinite(row[name])))) {
  throw new Error("附件1中的边界数据为空或含非数值单元格");
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, JSON.stringify({ rows }, null, 2), "utf8");
console.log(`environment rows: ${rows.length}`);
console.log(`output: ${outputPath}`);
