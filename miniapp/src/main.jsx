import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { signInWithInitData } from "./api/client";
import { I18nProvider } from "./i18n";
import { applyTheme, isTelegram } from "./platform/telegram";
import "./styles.css";

applyTheme();

const client = new QueryClient({
  defaultOptions: {
    queries: {
      // Phones lose connectivity constantly; one retry turns a lift into a
      // blip, while more just delays showing the user that something is wrong.
      retry: 1,
      // Data is cheap to refetch and the game moves: coins, scores and battle
      // timers are all wrong within seconds of being fetched.
      staleTime: 5_000,
      refetchOnWindowFocus: true,
    },
  },
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <I18nProvider>
        <App />
      </I18nProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

// Inside Telegram every request already carries initData, so no sign-in is
// needed to USE the app. This exchange happens in the background purely so a
// token exists if the user later installs the PWA from the same device.
if (isTelegram) {
  signInWithInitData().catch(() => {
    // Not fatal: the tma header keeps working regardless.
  });
}

// The service worker is what makes the PWA installable. Registered after load
// so it never competes with the first paint for bandwidth.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    // The ?v= is a cache-buster for CDN edges holding an older sw.js.
    // Bump it whenever the worker's strategy changes.
    navigator.serviceWorker.register("/app/sw.js?v=2").catch(() => {
      // Blocked in a private window, or served over plain http in dev. The app
      // works without it; only offline caching and install are lost.
    });
  });
}
