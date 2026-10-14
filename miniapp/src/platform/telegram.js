/*
 * The only file that knows the app might be running inside Telegram.
 *
 * One codebase serves two runtimes: a Telegram Mini App (the primary one for
 * Cola Fest) and an installable PWA in a normal browser. Rather than sprinkle
 * `if (window.Telegram)` through the screens, every capability that differs is
 * a function here that does the right thing in either place.
 *
 * The differences that actually matter:
 *
 *   identity   Telegram signs `initData`; the browser has to sign in through
 *              the Telegram Login Widget instead.
 *   QR         Telegram has a native scanner. In a browser we fall back to
 *              BarcodeDetector, and where that is missing (Safari today) the
 *              caller offers manual entry — which is why scanQr resolves to
 *              null rather than throwing.
 *   chrome     Telegram supplies a back button, haptics and a theme; the
 *              browser gets no-ops and our own colours.
 */

const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;

/** True when running inside Telegram, as opposed to a browser tab. */
export const isTelegram = Boolean(tg?.initData);

/** Raw initData, forwarded byte-for-byte — re-encoding invalidates its hash. */
export function initData() {
  return tg?.initData || "";
}

/**
 * `?startapp=...` from a deep link, e.g. a notification linking to a battle.
 * Telegram delivers it in initDataUnsafe; a browser gets it as a query param
 * so the same links work when opened outside Telegram.
 */
export function startParam() {
  if (tg?.initDataUnsafe?.start_param) return tg.initDataUnsafe.start_param;
  return new URLSearchParams(window.location.search).get("startapp") || null;
}

/** Tell Telegram we have painted, and take the full height available. */
export function ready() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  // Stops a downward swipe inside a scrollable list from dismissing the app,
  // which otherwise makes long lists feel broken.
  tg.disableVerticalSwipes?.();
}

/**
 * Show Telegram's own back button while the app is not on a root screen.
 * Returns a cleanup function, so a screen can wire it up in an effect.
 */
export function backButton(onBack) {
  if (!tg?.BackButton) return () => {};
  tg.BackButton.onClick(onBack);
  tg.BackButton.show();
  return () => {
    tg.BackButton.offClick(onBack);
    tg.BackButton.hide();
  };
}

export const haptic = {
  tap() {
    tg?.HapticFeedback?.impactOccurred?.("light");
  },
  success() {
    tg?.HapticFeedback?.notificationOccurred?.("success");
  },
  error() {
    tg?.HapticFeedback?.notificationOccurred?.("error");
  },
};

/**
 * Scan a QR code.
 *
 * Both labels are passed in rather than written here: this module is the only
 * place that knows about Telegram, and it should not also be a place that
 * knows Russian.
 *
 * Resolves to the scanned text, or null when the user cancelled OR when this
 * runtime cannot scan at all. Null is not an error: the caller shows the
 * manual-entry field either way, which is also the fallback for a cap whose
 * code is printed but not encoded.
 */
export async function scanQr(prompt = "", cancelLabel = "Cancel") {
  if (tg?.showScanQrPopup) {
    return new Promise((resolve) => {
      tg.showScanQrPopup({ text: prompt }, (text) => {
        tg.closeScanQrPopup();
        resolve(text || null);
        return true; // tells Telegram to close the popup
      });
    });
  }
  return scanWithCamera(cancelLabel);
}

/** True when this runtime can open a camera scanner at all. */
export function canScan() {
  return Boolean(tg?.showScanQrPopup) || hasBarcodeDetector();
}

function hasBarcodeDetector() {
  return (
    typeof window !== "undefined" &&
    "BarcodeDetector" in window &&
    Boolean(navigator.mediaDevices?.getUserMedia)
  );
}

/**
 * Browser fallback: getUserMedia plus BarcodeDetector.
 *
 * Chrome on Android has BarcodeDetector; Safari does not, so on iPhone
 * outside Telegram this returns null and the caller falls back to typing the
 * code. Bundling a wasm decoder would fix that at the cost of ~200KB on every
 * load, for a path that is not how Cola Fest is distributed — the Mini App's
 * native scanner is. Worth revisiting if the PWA becomes a real entry point.
 */
async function scanWithCamera(cancelLabel) {
  if (!hasBarcodeDetector()) return null;

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
    });
  } catch {
    return null; // permission denied, or no camera
  }

  const video = document.createElement("video");
  video.setAttribute("playsinline", "true");
  video.srcObject = stream;
  video.style.cssText =
    "position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:9999;background:#000";
  document.body.appendChild(video);

  const cancel = document.createElement("button");
  cancel.textContent = cancelLabel;
  cancel.style.cssText =
    "position:fixed;left:50%;bottom:40px;transform:translateX(-50%);z-index:10000;" +
    "padding:14px 28px;border:0;border-radius:999px;font:600 16px system-ui;" +
    "background:#fff;color:#111";
  document.body.appendChild(cancel);

  const stop = () => {
    stream.getTracks().forEach((track) => track.stop());
    video.remove();
    cancel.remove();
  };

  try {
    await video.play();
    const detector = new window.BarcodeDetector({ formats: ["qr_code"] });

    return await new Promise((resolve) => {
      let done = false;
      const finish = (value) => {
        if (done) return;
        done = true;
        resolve(value);
      };

      cancel.onclick = () => finish(null);

      const tick = async () => {
        if (done) return;
        try {
          const codes = await detector.detect(video);
          if (codes.length) return finish(codes[0].rawValue);
        } catch {
          // A frame that fails to decode is normal; keep going.
        }
        requestAnimationFrame(tick);
      };
      tick();

      // Give up rather than holding the camera open forever.
      setTimeout(() => finish(null), 60_000);
    });
  } finally {
    stop();
  }
}

/**
 * Telegram's theme as CSS variables, so the app blends into the client the
 * user actually has. Outside Telegram nothing is set and the stylesheet's own
 * dark palette applies.
 */
export function applyTheme() {
  if (!tg?.themeParams) return;
  const root = document.documentElement;
  for (const [key, value] of Object.entries(tg.themeParams)) {
    if (typeof value === "string") {
      root.style.setProperty(`--tg-${key.replace(/_/g, "-")}`, value);
    }
  }
  root.dataset.tgTheme = tg.colorScheme || "dark";
  tg.setHeaderColor?.("secondary_bg_color");
}

/** Open a Telegram link (a share, or the bot itself) the native way. */
export function openTelegramLink(url) {
  if (tg?.openTelegramLink) tg.openTelegramLink(url);
  else window.open(url, "_blank", "noopener");
}
