import { ulid } from "ulidx";
import * as fs from "fs";
import * as path from "path";

const ULID_FILE = path.join(__dirname, "../../.ulid");

/**
 * スタックのライフタイム中は固定のULIDを返す。
 * 初回生成時に .ulid ファイルに永続化し、以降は再利用する。
 */
export function getOrCreateUlid(): string {
  if (fs.existsSync(ULID_FILE)) {
    return fs.readFileSync(ULID_FILE, "utf-8").trim();
  }
  const id = ulid().toLowerCase();
  fs.writeFileSync(ULID_FILE, id, "utf-8");
  return id;
}
