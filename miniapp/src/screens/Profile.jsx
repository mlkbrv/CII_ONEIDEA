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
  useUpdateMe,
} from "../api/queries";
import AvatarView from "../components/AvatarView";
import DemographicsForm from "../components/DemographicsForm";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { LANGUAGES, useI18n, useT } from "../i18n";
import { haptic } from "../platform/telegram";

// TZ section 10: the challenger picks the length.
const DURATIONS = [30, 60, 360, 1440];

export default function Profile() {
  const t = useT();
  const { language, choose } = useI18n();
  const params = useParams();
  const navigate = useNavigate();
  const { data: me } = useMe();

  // On /profile the id is not in the URL, so it comes from the session.
  const userId = params.userId ?? me?.user_id;
  const profile = useProfile(userId);
  const follow = useFollow();
  const challenge = useChallenge();
  const updateMe = useUpdateMe();

  const [aboutOpen, setAboutOpen] = useState(false);
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
      setMessage({ ok: true, text: t("profile.challenge_sent") });
      haptic.success();
    } catch (err) {
      setMessage({
        ok: false,
        text: t(err.status === 409 ? "profile.err_busy" : "profile.err_challenge"),
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
            <span>{t("profile.followers")}</span>
          </Link>
          <Link to={`/u/${user.user_id}/following`} className="stat">
            <strong>{user.following_count}</strong>
            <span>{t("profile.following")}</span>
          </Link>
          <div className="stat">
            <strong>🔥 {user.winning_streak}</strong>
            <span>{t("profile.streak_short")}</span>
          </div>
        </div>

        {user.active_competition_id ? (
          <Button
            variant="ghost"
            onClick={() => navigate(`/battle/${user.active_competition_id}`)}
          >
            {t("profile.watch_battle")}
          </Button>
        ) : null}

        {user.is_self ? (
          <div className="row-actions">
            <Link to="/wardrobe">
              <Button variant="ghost">{t("common.wardrobe")}</Button>
            </Link>
            <Link to="/shop">
              <Button variant="ghost">{t("common.shop")}</Button>
            </Link>
          </div>
        ) : (
          <div className="row-actions">
            <Button
              variant={user.is_following ? "ghost" : "primary"}
              onClick={toggleFollow}
              disabled={follow.isPending}
            >
              {t(user.is_following ? "common.unfollow" : "common.follow")}
            </Button>
            <Button variant="ghost" onClick={() => setChallenging((open) => !open)}>
              {t("profile.challenge")}
            </Button>
          </div>
        )}

        {challenging ? (
          <div className="durations">
            <p className="muted small">{t("profile.duration_question")}</p>
            <div className="row-actions">
              {DURATIONS.map((minutes) => (
                <Button
                  key={minutes}
                  variant="ghost"
                  disabled={challenge.isPending}
                  onClick={() => sendChallenge(minutes)}
                >
                  {t(`duration.${minutes}`)}
                </Button>
              ))}
            </div>
          </div>
        ) : null}

        {message ? (
          <p className={`status ${message.ok ? "status-ok" : "status-err"}`}>{message.text}</p>
        ) : null}
      </Card>

      {user.is_self ? (
        <Card>
          <p className="muted small">{t("profile.language")}</p>
          <div className="row-actions">
            {LANGUAGES.map((option) => (
              <Button
                key={option.code}
                variant={language === option.code ? "primary" : "ghost"}
                onClick={() => {
                  // Switch the interface immediately, then tell the server —
                  // it is what the bot reads when it writes notifications, so
                  // a failed request would leave the two disagreeing.
                  choose(option.code);
                  updateMe.mutate({ language: option.code });
                }}
              >
                {option.label}
              </Button>
            ))}
          </div>
        </Card>
      ) : null}

      {user.is_self && me?.demographics_status !== "answered" ? (
        <Card className="link-card" onClick={() => setAboutOpen(true)}>
          {t("demographics.profile_cta")}
        </Card>
      ) : null}
      {aboutOpen ? <DemographicsForm onClose={() => setAboutOpen(false)} /> : null}

      {user.wardrobe_public || user.is_self ? (
        <Link to={user.is_self ? "/wardrobe" : `/u/${user.user_id}/wardrobe`}>
          <Card className="link-card">{t("profile.view_wardrobe")}</Card>
        </Link>
      ) : (
        <EmptyState
          icon="🔒"
          title={t("wardrobe.hidden")}
          hint={t("profile.wardrobe_private")}
        />
      )}
    </div>
  );
}
