/*
 * The browser / PWA sign-in.
 *
 * Never seen inside Telegram — there, initData already proves who the user is
 * and the app goes straight in. This is the door for someone who installed the
 * PWA or opened the link in a normal tab.
 *
 * The Telegram Login Widget is loaded as a script that injects its own iframe
 * button; there is no npm package and no way to style it. It hands the signed
 * payload to a global callback, which is why one is registered on window.
 */
import { useEffect, useRef, useState } from "react";

import { api, signInWithWidget } from "../api/client";
import { Button, Card } from "../components/ui";

const CALLBACK = "onTelegramAuth";

export default function SignIn({ onSignedIn }) {
  const holder = useRef(null);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // The bot's @handle comes from the server rather than the build, so
    // changing bots does not mean rebuilding the frontend.
    api("/config")
      .then(setConfig)
      .catch(() => setConfig({ bot_username: "" }));
  }, []);

  useEffect(() => {
    if (!config?.bot_username || !holder.current) return undefined;

    window[CALLBACK] = async (user) => {
      try {
        // Every field Telegram sent, as strings — the signature covers all of
        // them, so dropping or renaming one makes it fail to verify.
        const data = Object.fromEntries(
          Object.entries(user).map(([key, value]) => [key, String(value)])
        );
        await signInWithWidget(data);
        onSignedIn();
      } catch (err) {
        setError(err.detail || "Не удалось войти");
      }
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", config.bot_username);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-onauth", `${CALLBACK}(user)`);
    script.setAttribute("data-request-access", "write");
    holder.current.appendChild(script);

    const node = holder.current;
    return () => {
      node.replaceChildren();
      delete window[CALLBACK];
    };
  }, [config, onSignedIn]);

  return (
    <div className="screen signin">
      <Card>
        <div className="signin-mark" aria-hidden="true">
          🐻‍❄️
        </div>
        <h1 className="screen-title">Cola Fest</h1>
        <p className="muted">
          Собирай монеты с крышек, одевай своего медведя и вызывай друзей на баттл
          образов.
        </p>

        {config === null ? (
          <p className="muted small">Загружаем…</p>
        ) : config.bot_username ? (
          <>
            <p className="muted small">Войди через Telegram, чтобы начать:</p>
            <div ref={holder} className="signin-widget" />
          </>
        ) : (
          <p className="status status-err">
            Вход через браузер не настроен. Открой приложение из Telegram.
          </p>
        )}

        {config?.webapp_url ? (
          <Button variant="ghost" onClick={() => window.open(config.webapp_url, "_blank")}>
            Открыть в Telegram
          </Button>
        ) : null}

        {error ? <p className="status status-err">{error}</p> : null}
      </Card>
    </div>
  );
}
