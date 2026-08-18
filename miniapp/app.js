const tg = window.Telegram?.WebApp;
const form = document.getElementById("redeem-form");
const input = document.getElementById("code");
const statusEl = document.getElementById("status");
const redeemBtn = document.getElementById("redeem-btn");
const scanBtn = document.getElementById("scan-btn");

if (tg) {
  tg.ready();
  tg.expand();
}

function setStatus(text, kind) {
  statusEl.hidden = !text;
  statusEl.textContent = text;
  statusEl.className = `status ${kind || ""}`;
}

function authHeaders() {
  const initData = tg?.initData || "";
  if (!initData) {
    throw new Error("Открой экран из Telegram");
  }
  return {
    "Content-Type": "application/json",
    Authorization: `tma ${initData}`,
  };
}

async function redeem(code) {
  const trimmed = String(code || "").trim();
  if (!trimmed) {
    setStatus("Введи промокод", "err");
    return;
  }
  redeemBtn.disabled = true;
  setStatus("Проверяем код…");
  try {
    const response = await fetch("/api/v1/promo-codes/redeem", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ code: trimmed }),
    });
    const data = await response.json().catch(() => ({}));
    if (response.ok) {
      setStatus(`+${data.coin_reward} монет. Баланс: ${data.balance}`, "ok");
      tg?.HapticFeedback?.notificationOccurred("success");
      return;
    }
    const messages = {
      401: "Открой приложение из Telegram",
      404: "Промокод не найден",
      409: "Этот промокод уже использован",
      410: "Срок действия промокода истёк",
      503: "Бот ещё не настроен на сервере",
    };
    setStatus(messages[response.status] || data.detail || "Не удалось активировать код", "err");
    tg?.HapticFeedback?.notificationOccurred("error");
  } catch (error) {
    setStatus(error.message || "Нет соединения с сервером", "err");
  } finally {
    redeemBtn.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  redeem(input.value);
});

scanBtn.addEventListener("click", () => {
  if (!tg?.showScanQrPopup) {
    setStatus("Сканер QR недоступен. Введи код вручную.", "err");
    return;
  }
  tg.showScanQrPopup({ text: "Наведи камеру на QR промокода" }, (value) => {
    if (!value) {
      return;
    }
    tg.closeScanQrPopup();
    input.value = value;
    redeem(value);
  });
});
