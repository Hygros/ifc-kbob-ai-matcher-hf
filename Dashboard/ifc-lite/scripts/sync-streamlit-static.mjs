import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const projectRoot = resolve(process.cwd());
const srcDir = resolve(projectRoot, "dist");
const targetDir = resolve(projectRoot, "..", "static", "viewer");

if (!existsSync(srcDir)) {
  console.error("[sync] Missing dist directory. Run npm run build first.");
  process.exit(1);
}

rmSync(targetDir, { recursive: true, force: true });
mkdirSync(targetDir, { recursive: true });
cpSync(srcDir, targetDir, { recursive: true });

console.log(`[sync] Copied ${srcDir} -> ${targetDir}`);
