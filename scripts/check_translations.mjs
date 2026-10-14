/*
 * Every language must define exactly the same keys.
 *
 * A missing key does not crash — it silently falls back to Russian — so
 * nothing would ever surface a half-translated screen except a user noticing.
 * This is what notices instead.
 *
 *     node scripts/check_translations.mjs
 */
import az from "../miniapp/src/i18n/az.js";
import en from "../miniapp/src/i18n/en.js";
import ru from "../miniapp/src/i18n/ru.js";

const TABLES = { ru, en, az };
const REFERENCE = "ru";

const referenceKeys = new Set(Object.keys(TABLES[REFERENCE]));
let problems = 0;

for (const [language, table] of Object.entries(TABLES)) {
  if (language === REFERENCE) continue;
  const keys = new Set(Object.keys(table));

  const missing = [...referenceKeys].filter((key) => !keys.has(key));
  const extra = [...keys].filter((key) => !referenceKeys.has(key));

  if (missing.length) {
    console.error(`[FAIL] ${language}: ${missing.length} key(s) missing`);
    missing.forEach((key) => console.error(`         ${key}`));
    problems += missing.length;
  }
  if (extra.length) {
    console.error(`[FAIL] ${language}: ${extra.length} key(s) not in ${REFERENCE}`);
    extra.forEach((key) => console.error(`         ${key}`));
    problems += extra.length;
  }

  // A placeholder dropped in translation means a sentence with a hole in it:
  // "You won {prize} coins" rendering as "You won coins".
  for (const key of referenceKeys) {
    if (!keys.has(key)) continue;
    const placeholders = (text) => (String(text).match(/\{\w+\}/g) || []).sort().join(",");
    const expected = placeholders(TABLES[REFERENCE][key]);
    const actual = placeholders(table[key]);
    if (expected !== actual) {
      console.error(`[FAIL] ${language}: ${key} placeholders ${actual || "(none)"} != ${expected || "(none)"}`);
      problems += 1;
    }
  }

  if (!missing.length && !extra.length) {
    console.log(`[OK  ] ${language}: ${keys.size} keys`);
  }
}

if (problems) {
  console.error(`\n${problems} problem(s).`);
  process.exit(1);
}
console.log(`\nAll ${Object.keys(TABLES).length} languages agree on ${referenceKeys.size} keys.`);
