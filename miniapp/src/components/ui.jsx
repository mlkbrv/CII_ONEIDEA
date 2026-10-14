/*
 * The small shared pieces every screen is built from.
 *
 * Kept in one file because they are each a few lines and they only make sense
 * as a set — one button, one card, one way to say "nothing here yet", one way
 * to say "loading". Screens that reach for their own variants are how an app
 * ends up looking like four different apps.
 */
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";

export function Button({ variant = "primary", onClick, className = "", children, ...rest }) {
  return (
    <button
      // className is pulled out of the props rather than left in `rest`: a
      // spread would replace this string wholesale, so <Button className="cta">
      // would silently lose `btn btn-primary` and render as a bare browser
      // button — white on white, and only visible by looking at it.
      className={`btn btn-${variant} ${className}`.trim()}
      onClick={(event) => {
        // Every button press buzzes. It is the cheapest thing that makes a
        // web view feel like an app rather than a page.
        haptic.tap();
        onClick?.(event);
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = "", ...rest }) {
  return (
    <div className={`card ${className}`} {...rest}>
      {children}
    </div>
  );
}

/** A coin amount. Always with the symbol, so a bare number is never ambiguous. */
export function Coins({ amount, className = "" }) {
  return (
    <span className={`coins ${className}`}>
      <span aria-hidden="true">🪙</span>
      {amount ?? 0}
    </span>
  );
}

/**
 * A grey block standing in for content that is on its way.
 *
 * Skeletons rather than a spinner: the layout stops jumping when the data
 * lands, and the user can see the shape of what is coming.
 */
export function Skeleton({ height = 20, width = "100%", radius = 10, className = "" }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ height, width, borderRadius: radius }}
    />
  );
}

export function EmptyState({ icon = "🐻‍❄️", title, hint, action }) {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden="true">
        {icon}
      </div>
      <p className="empty-title">{title}</p>
      {hint ? <p className="empty-hint">{hint}</p> : null}
      {action}
    </div>
  );
}

/**
 * What a screen shows when a request failed.
 *
 * Always with a retry: on a phone the overwhelmingly common cause is a tunnel
 * or a lift, and the fix is to try again rather than to restart the app.
 */
export function ErrorState({ error, onRetry }) {
  const t = useT();
  return (
    <EmptyState
      icon="⚠️"
      title={t("common.error_title")}
      // The server's own message when there is one: "This code has expired"
      // is more use than "could not load". It arrives already localised.
      hint={error?.detail || error?.message || t("common.error_hint")}
      action={
        onRetry ? (
          <Button variant="ghost" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : null
      }
    />
  );
}

/** Section heading used down the whole app. */
export function SectionTitle({ children, action }) {
  return (
    <div className="section-title">
      <h2>{children}</h2>
      {action}
    </div>
  );
}

/** A row of mutually exclusive filters (shop categories, battle tabs). */
export function Tabs({ value, onChange, options }) {
  return (
    <div className="tabs" role="tablist">
      {options.map((option) => (
        <button
          key={option.value}
          role="tab"
          aria-selected={value === option.value}
          className={`tab ${value === option.value ? "is-active" : ""}`}
          onClick={() => {
            haptic.tap();
            onChange(option.value);
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Time left, phrased the way a person would say it.
 *
 * Battles are 30 minutes to 24 hours, so the useful unit changes as the clock
 * runs down: hours early on, minutes at the end. "0:03:41" would be precise
 * and much harder to read at a glance.
 */
export function timeLeft(endTime, t) {
  // The API stores naive UTC; without the Z the browser would read it as local
  // time and be wrong by the device's offset.
  const end = new Date(endTime.endsWith("Z") ? endTime : `${endTime}Z`);
  const ms = end.getTime() - Date.now();
  if (ms <= 0) return t("common.finished");

  const minutes = Math.floor(ms / 60000);
  if (minutes < 60) return `${minutes} ${t("common.minutes_short")}`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} ${t("common.hours_short")} ${minutes % 60} ${t("common.minutes_short")}`;
  }
  return `${Math.floor(hours / 24)} ${t("common.days_short")}`;
}
