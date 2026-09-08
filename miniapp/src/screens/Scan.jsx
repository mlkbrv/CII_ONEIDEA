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
import { canScan, haptic, scanQr } from "../platform/telegram";
import { Button, Card, Coins } from "../components/ui";

const MESSAGES = {
  404: "Код не найден. Проверь, что ввёл его правильно.",
  409: "Этот код уже использован.",
  410: "Срок действия кода истёк.",
  401: "Открой приложение из Telegram.",
  503: "Бот ещё не настроен на сервере.",
};

export default function Scan() {
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
      setError(MESSAGES[err.status] || err.detail || "Не удалось активировать код");
      haptic.error();
    }
  }

  async function scan() {
    const scanned = await scanQr();
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
        <h1 className="screen-title">Код с крышки</h1>
        <p className="muted">
          Каждая крышка — это монеты. Отсканируй код или введи его руками.
        </p>

        {canScan() ? (
          <Button onClick={scan} className="cta">
            📷 Сканировать
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
            placeholder="XXXX-XXXX"
            // Codes are printed in capitals; autocorrect on a phone otherwise
            // "helps" by lowercasing and inserting spaces.
            autoCapitalize="characters"
            autoCorrect="off"
            autoComplete="off"
            spellCheck="false"
            maxLength={64}
            aria-label="Код с крышки"
          />
          <Button type="submit" disabled={redeem.isPending || !code.trim()}>
            {redeem.isPending ? "Проверяем…" : "Активировать"}
          </Button>
        </form>

        {result ? (
          <p className="status status-ok">
            Готово! +{result.coins_earned} монет. Баланс:{" "}
            <Coins amount={result.balance} />
          </p>
        ) : null}
        {error ? <p className="status status-err">{error}</p> : null}
      </Card>
    </div>
  );
}
