/*
 * Routing, and the gate in front of it.
 *
 * HashRouter, not BrowserRouter: the app is served as static files by FastAPI,
 * and a deep link like /app/battle/<id> would otherwise be a 404 from the
 * server before React ever loads. A hash keeps every route on one document, so
 * refreshing inside a battle works with no server-side rewrite rule to
 * remember when the deployment changes.
 *
 * The gate: inside Telegram the app is already authenticated (initData rides
 * on every request) and renders immediately. In a browser it needs a token,
 * so it shows the sign-in screen until it has one.
 */
import { useCallback, useEffect, useState } from "react";
import { HashRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { canAuthenticate } from "./api/client";
import { useMe } from "./api/queries";
import { useI18n } from "./i18n";
import Layout from "./components/Layout";
import { ready, startParam } from "./platform/telegram";
import Battle from "./screens/Battle";
import Battles from "./screens/Battles";
import Follows from "./screens/Follows";
import Friends from "./screens/Friends";
import Home from "./screens/Home";
import Leaderboard from "./screens/Leaderboard";
import Notifications from "./screens/Notifications";
import Profile from "./screens/Profile";
import Scan from "./screens/Scan";
import Shop from "./screens/Shop";
import SignIn from "./screens/SignIn";
import UserWardrobe from "./screens/UserWardrobe";
import Wardrobe from "./screens/Wardrobe";

export default function App() {
  const [authed, setAuthed] = useState(canAuthenticate());

  useEffect(() => {
    ready();
  }, []);

  const onSignedIn = useCallback(() => setAuthed(true), []);

  if (!authed) return <SignIn onSignedIn={onSignedIn} />;

  return (
    <HashRouter>
      <AccountLanguage />
      <DeepLink />
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/scan" element={<Scan />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/wardrobe" element={<Wardrobe />} />
          <Route path="/battles" element={<Battles />} />
          <Route path="/battle/:competitionId" element={<Battle />} />
          <Route path="/friends" element={<Friends />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/u/:userId" element={<Profile />} />
          <Route path="/u/:userId/followers" element={<Follows kind="followers" />} />
          <Route path="/u/:userId/following" element={<Follows kind="following" />} />
          <Route path="/u/:userId/wardrobe" element={<UserWardrobe />} />
          {/* Anything unknown lands on Home rather than a dead end. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </HashRouter>
  );
}

/**
 * Adopts the language stored on the account.
 *
 * The app starts in whatever Telegram reports, which is right for a first
 * visit and wrong for a player who picked something else on another device.
 * The account is the authority — it is also what the bot writes in — so the
 * moment /users/me arrives, it wins. Unless the user has already chosen in
 * this session, in which case the switcher would appear to snap back.
 */
function AccountLanguage() {
  const { data: me } = useMe();
  const { adoptFromAccount } = useI18n();

  useEffect(() => {
    if (me?.language) adoptFromAccount(me.language);
  }, [me?.language, adoptFromAccount]);

  return null;
}

/**
 * Honours `?startapp=...` once, on first render.
 *
 * The bot links straight to a battle from a notification
 * (`t.me/bot/app?startapp=battle_<uuid>`), and Telegram delivers that as a
 * start parameter rather than as a path, so it has to be turned into a route
 * here.
 *
 * Split on the FIRST underscore only: the rest is the value verbatim. A UUID
 * contains hyphens, which start parameters allow, and reassembling it from
 * pieces is how you turn a valid id into a 404.
 */
function DeepLink() {
  const navigate = useNavigate();

  useEffect(() => {
    const param = startParam();
    if (!param) return;

    const separator = param.indexOf("_");
    const kind = separator === -1 ? param : param.slice(0, separator);
    const value = separator === -1 ? "" : param.slice(separator + 1);

    if (kind === "battle" && value) navigate(`/battle/${value}`, { replace: true });
    else if (kind === "profile" && value) navigate(`/u/${value}`, { replace: true });
    else if (kind === "scan") navigate("/scan", { replace: true });
    // Only on mount: re-running would yank the user back every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}
