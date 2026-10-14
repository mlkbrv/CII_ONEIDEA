/*
 * Redeeming a code from a bottle cap.
 *
 * Scanning and typing are given equal weight on purpose. Telegram's scanner
 * is the fast path, but not every cap will carry a scannable code and not
 * every runtime can open a camera (Safari outside Telegram has no
 * BarcodeDetector), so the text field is always there rather than hidden
 * behind a "having trouble?" link.
 */
import { useState } from "react";

import { useRedeemCode } from "../api/queries";
import { useT } from "../i18n";
import { canScan, haptic, scanQr } from "../platform/telegram";
import { Button, Card, Coins } from "../components/ui";

// HTTP status -> which sentence to show. The server's own `detail` is in
// English, so these are used in preference to it.
const MESSAGE_KEYS = {
  404: "scan.err_404",
  409: "scan.err_409",
  410: "scan.err_410",
  401: "scan.err_401",
  503: "scan.err_503",
};

export default function Scan() {
  const t = useT();
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const redeem = useRedeemCode();

  async function submit(value) {
    const trimmed = (value ?? code).trim();
    if (!trimmed) return;

    setError(null);
    setResult(null);
    try {
      const response = await redeem.mutateAsync(trimmed);
      setResult(response);
      setCode("");
      haptic.success();
    } catch (err) {
      setError(t(MESSAGE_KEYS[err.status] || "scan.err_generic"));
      haptic.error();
    }
  }

  async function scan() {
    const scanned = await scanQr(t("scan.hint"), t("common.cancel"));
    // null means cancelled, or this runtime cannot scan — either way there is
    // nothing to report, the field below is right there.
    if (scanned) {
      setCode(scanned);
      submit(scanned);
    }
  }

  return (
    <div className="screen scan">
      <Card>
        <p className="eyebrow">Cola Fest</p>
        <h1 className="screen-title">{t("scan.title")}</h1>
        <p className="muted">{t("scan.hint")}</p>

        {canScan() ? (
          <Button onClick={scan} className="cta">
            {t("scan.scan_button")}
          </Button>
        ) : null}

        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
          className="code-form"
        >
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder={t("scan.placeholder")}
            // Codes are printed in capitals; autocorrect on a phone otherwise
            // "helps" by lowercasing and inserting spaces.
            autoCapitalize="characters"
            autoCorrect="off"
            autoComplete="off"
            spellCheck="false"
            maxLength={64}
            aria-label={t("scan.label")}
          />
          <Button type="submit" disabled={redeem.isPending || !code.trim()}>
            {redeem.isPending ? t("scan.checking") : t("scan.submit")}
          </Button>
        </form>

        {result ? (
          <p className="status status-ok">
            {t("scan.success", { coins: result.coins_earned })}{" "}
            <Coins amount={result.balance} />
          </p>
        ) : null}
        {error ? <p className="status status-err">{error}</p> : null}
      </Card>
    </div>
  );
}
