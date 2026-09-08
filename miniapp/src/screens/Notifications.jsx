/*
 * The in-app notification feed.
 *
 * The bot is the primary channel (TZ section 16) — this is where a player
 * catches up on what they scrolled past in chat. The server renders the text,
 * so a message here and the one in Telegram cannot say different things.
 *
 * Everything is marked read on open rather than per row: the badge exists to
 * say "something happened", and once the list is on screen that has been
 * answered. Tapping each item to clear a badge is busywork.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useMarkAllRead, useNotifications } from "../api/queries";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui";

// Which notifications lead somewhere, and where.
function destinationOf(notification) {
  const payload = notification.payload || {};
  if (payload.competition_id) return `/battle/${payload.competition_id}`;
  if (notification.actor_id) return `/u/${notification.actor_id}`;
  if (payload.request_id) return "/battles";
  return null;
}

export default function Notifications() {
  const navigate = useNavigate();
  const feed = useNotifications();
  const markAllRead = useMarkAllRead();

  const unread = feed.data?.unread ?? 0;
  useEffect(() => {
    // Fire once per screenful of unread, not on every render.
    if (unread > 0 && !markAllRead.isPending) markAllRead.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unread > 0]);

  if (feed.isError) return <ErrorState error={feed.error} onRetry={feed.refetch} />;

  const items = feed.data?.items ?? [];

  return (
    <div className="screen notifications">
      <h1 className="screen-title">Уведомления</h1>

      {feed.isLoading ? (
        <div className="list">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} height={64} radius={12} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon="🔔"
          title="Пока тихо"
          hint="Здесь появятся вызовы на баттлы, результаты и новые подписчики."
        />
      ) : (
        <div className="list">
          {items.map((notification) => {
            const to = destinationOf(notification);
            return (
              <Card
                key={notification.notification_id}
                className={`notification ${notification.is_read ? "" : "is-unread"} ${
                  to ? "is-clickable" : ""
                }`}
                onClick={to ? () => navigate(to) : undefined}
              >
                <p>{notification.message}</p>
                <p className="muted small">{formatWhen(notification.created_at)}</p>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatWhen(value) {
  // Stored naive UTC; without the Z the browser reads it as local time and is
  // wrong by the device's offset — which for a "2 minutes ago" label shows up
  // immediately as "in 3 hours".
  const when = new Date(value.endsWith("Z") ? value : `${value}Z`);
  const minutes = Math.round((Date.now() - when.getTime()) / 60000);

  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return when.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}
