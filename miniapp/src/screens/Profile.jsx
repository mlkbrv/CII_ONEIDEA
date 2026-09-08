/*
 * A profile — yours or somebody else's.
 *
 * One component for both, because the API already answers the only questions
 * that differ (`is_self`, `is_following`, `wardrobe_public`). Two components
 * would drift: the challenge button would gain a feature the self view never
 * got, and the outfit would end up rendered two slightly different ways.
 *
 * Route /profile shows the signed-in user, /u/:userId shows anyone.
 */
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  useChallenge,
  useFollow,
  useMe,
  useProfile,
} from "../api/queries";
import AvatarView from "../components/AvatarView";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { haptic } from "../platform/telegram";

// TZ section 10: the challenger picks the length.
const DURATIONS = [
  { minutes: 30, label: "30 минут" },
  { minutes: 60, label: "1 час" },
  { minutes: 360, label: "6 часов" },
  { minutes: 1440, label: "24 часа" },
];

export default function Profile() {
  const params = useParams();
  const navigate = useNavigate();
  const { data: me } = useMe();

  // On /profile the id is not in the URL, so it comes from the session.
  const userId = params.userId ?? me?.user_id;
  const profile = useProfile(userId);
  const follow = useFollow();
  const challenge = useChallenge();

  const [challenging, setChallenging] = useState(false);
  const [message, setMessage] = useState(null);

  if (profile.isError) {
    return <ErrorState error={profile.error} onRetry={profile.refetch} />;
  }
  if (profile.isLoading || !profile.data) {
    return (
      <div className="screen profile">
        <Card>
          <Skeleton height={200} radius={14} />
          <Skeleton width="50%" height={22} />
          <Skeleton width="70%" height={16} />
        </Card>
      </div>
    );
  }

  const user = profile.data;

  async function toggleFollow() {
    try {
      await follow.mutateAsync({ userId: user.user_id, follow: !user.is_following });
      haptic.success();
    } catch {
      haptic.error();
    }
  }

  async function sendChallenge(minutes) {
    setMessage(null);
    try {
      await challenge.mutateAsync({ opponentId: user.user_id, durationMinutes: minutes });
      setChallenging(false);
      setMessage({ ok: true, text: "Вызов отправлен. Ждём ответа соперника." });
      haptic.success();
    } catch (err) {
      setMessage({
        ok: false,
        text:
          err.status === 409
            ? "Один из вас уже участвует в баттле"
            : err.detail || "Не удалось отправить вызов",
      });
      haptic.error();
    }
  }

  return (
    <div className="screen profile">
      <Card className="profile-head">
        <AvatarView equipment={user.avatar?.equipment} size="160px" />
        <h1 className="screen-title">{user.username}</h1>
        {user.biography ? <p className="muted">{user.biography}</p> : null}

        <div className="stats">
          <Link to={`/u/${user.user_id}/followers`} className="stat">
            <strong>{user.followers_count}</strong>
            <span>подписчиков</span>
          </Link>
          <Link to={`/u/${user.user_id}/following`} className="stat">
            <strong>{user.following_count}</strong>
            <span>подписок</span>
          </Link>
          <div className="stat">
            <strong>🔥 {user.winning_streak}</strong>
            <span>серия</span>
          </div>
        </div>

        {user.active_competition_id ? (
          <Button
            variant="ghost"
            onClick={() => navigate(`/battle/${user.active_competition_id}`)}
          >
            ⚔️ Смотреть баттл
          </Button>
        ) : null}

        {user.is_self ? (
          <div className="row-actions">
            <Link to="/wardrobe">
              <Button variant="ghost">Гардероб</Button>
            </Link>
            <Link to="/shop">
              <Button variant="ghost">Магазин</Button>
            </Link>
          </div>
        ) : (
          <div className="row-actions">
            <Button
              variant={user.is_following ? "ghost" : "primary"}
              onClick={toggleFollow}
              disabled={follow.isPending}
            >
              {user.is_following ? "Отписаться" : "Подписаться"}
            </Button>
            <Button variant="ghost" onClick={() => setChallenging((open) => !open)}>
              ⚔️ Вызвать
            </Button>
          </div>
        )}

        {challenging ? (
          <div className="durations">
            <p className="muted small">Сколько длится баттл?</p>
            <div className="row-actions">
              {DURATIONS.map((option) => (
                <Button
                  key={option.minutes}
                  variant="ghost"
                  disabled={challenge.isPending}
                  onClick={() => sendChallenge(option.minutes)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>
        ) : null}

        {message ? (
          <p className={`status ${message.ok ? "status-ok" : "status-err"}`}>{message.text}</p>
        ) : null}
      </Card>

      {user.wardrobe_public || user.is_self ? (
        <Link to={user.is_self ? "/wardrobe" : `/u/${user.user_id}/wardrobe`}>
          <Card className="link-card">👀 Посмотреть гардероб</Card>
        </Link>
      ) : (
        <EmptyState icon="🔒" title="Гардероб скрыт" hint="Этот игрок закрыл свой гардероб." />
      )}
    </div>
  );
}
