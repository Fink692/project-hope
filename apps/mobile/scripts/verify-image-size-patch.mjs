import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { Worker, isMainThread, parentPort } from "node:worker_threads";

if (isMainThread) {
  const worker = new Worker(new URL(import.meta.url));
  const timeout = setTimeout(async () => {
    await worker.terminate();
    console.error("Patched image parser did not terminate safely.");
    process.exitCode = 1;
  }, 1500);
  worker.once("message", (message) => {
    clearTimeout(timeout);
    if (message !== "ok") process.exitCode = 1;
    else console.log("Patched image parser rejects zero-length ICNS/JXL/HEIF boxes.");
  });
  worker.once("error", (error) => {
    clearTimeout(timeout);
    console.error(error);
    process.exitCode = 1;
  });
} else {
  const require = createRequire(import.meta.url);
  const packageRoot = dirname(require.resolve("image-size/package.json"));
  const { ICNS } = require(join(packageRoot, "dist/types/icns.js"));
  const { JXL } = require(join(packageRoot, "dist/types/jxl.js"));
  const { HEIF } = require(join(packageRoot, "dist/types/heif.js"));
  const { findBox } = require(join(packageRoot, "dist/types/utils.js"));

  const zeroBox = Buffer.alloc(16);
  zeroBox.write("jxlp", 4, "ascii");
  assert.equal(findBox(zeroBox, "jxlp", 0), undefined);
  assert.throws(() => JXL.calculate(zeroBox), /No codestream/);
  assert.throws(() => HEIF.calculate(zeroBox), /Invalid HEIF/);

  const zeroEntryIcns = Buffer.alloc(16);
  zeroEntryIcns.write("icns", 0, "ascii");
  zeroEntryIcns.writeUInt32BE(16, 4);
  zeroEntryIcns.write("ic07", 8, "ascii");
  zeroEntryIcns.writeUInt32BE(0, 12);
  assert.throws(() => ICNS.calculate(zeroEntryIcns), /Invalid ICNS entry length/);

  parentPort.postMessage("ok");
}
