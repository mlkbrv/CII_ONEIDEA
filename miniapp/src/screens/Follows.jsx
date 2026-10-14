/*
 * Someone's followers, or who they follow. Same list, same component — the
 * route decides which, exactly as the API does.
 */
import { Link, useParams } from "react-router-dom";

import { useFollow, useFollowers } from "../api/queries";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";

export default function Follows({ kind }) {
  const t = useT();
  const { userId } = useParams();
  const list = useFollowers(userId, kind);
  const follow = useFollow();

  if (list.isError) return <ErrorState error={list.error} onRetry={list.refetch} />;

  const rows = list.data?.items ?? [];

  return (
    <div className="screen follows">
      <h1 className="screen-title">
        {t(kind === "followers" ? "follows.followers" : "follows.following")}
      </h1>

      {list.isLoading ? (
        <div className="list">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} height={64} radius={14} />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="👥"
          title={t(kind === "followers" ? "follows.no_followers" : "follows.no_following")}
        />
      ) : (
        <div className="list">
          {rows.map((user) => (
            <Card key={user.user_id} className="row">
              <Link to={`/u/${user.user_id}`} className="row-main">
                <span className="row-avatar" aria-hidden="true">
                  🐻‍❄️
                </span>
                <span>
                  <strong>{user.username}</strong>
                  <span className="muted small"> 🔥 {user.winning_streak}</span>
                </span>
              </Link>
              <Button
                variant="ghost"
                disabled={follow.isPending}
                onClick={async () => {
                  try {
                    await follow.mutateAsync({
                      userId: user.user_id,
                      follow: !user.is_following,
                    });
                    haptic.success();
                  } catch {
                    haptic.error();
                  }
                }}
              >
                {t(user.is_following ? "common.unfollow" : "common.follow")}
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
