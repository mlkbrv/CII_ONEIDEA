/*
 * Friends and search, on one screen.
 *
 * TZ sections 8 and 9 describe these separately, but they are the same task —
 * find a person and open them — and on a phone a search field above the list
 * is how that is done. Two tabs would mean guessing which one holds the person
 * you want.
 *
 * With a query typed, the list becomes results; with the field empty it is who
 * you already follow.
 */
import { useState } from "react";
import { Link } from "react-router-dom";

import { useFollow, useFollowers, useMe, useSearch } from "../api/queries";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";

export default function Friends() {
  const t = useT();
  const [term, setTerm] = useState("");
  const { data: me } = useMe();
  const following = useFollowers(me?.user_id, "following");
  const search = useSearch(term);
  const follow = useFollow();

  const searching = term.trim().length >= 2;
  const rows = searching
    ? (search.data ?? []).map((user) => ({ ...user, is_following: undefined }))
    : (following.data?.items ?? []);

  const loading = searching ? search.isLoading : following.isLoading;
  const failed = searching ? search.error : following.error;

  async function toggleFollow(user) {
    try {
      await follow.mutateAsync({ userId: user.user_id, follow: !user.is_following });
      haptic.success();
    } catch {
      haptic.error();
    }
  }

  return (
    <div className="screen friends">
      <input
        className="search-input"
        value={term}
        onChange={(event) => setTerm(event.target.value)}
        placeholder={t("friends.search_placeholder")}
        autoCorrect="off"
        autoCapitalize="none"
        aria-label={t("friends.search_placeholder")}
      />

      {failed ? (
        <ErrorState
          error={failed}
          onRetry={searching ? search.refetch : following.refetch}
        />
      ) : loading ? (
        <div className="list">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} height={64} radius={14} />
          ))}
        </div>
      ) : rows.length === 0 ? (
        searching ? (
          <EmptyState
            icon="🔍"
            title={t("friends.nobody_found")}
            hint={t("friends.nobody_found_hint")}
          />
        ) : (
          <EmptyState
            icon="👥"
            title={t("friends.no_following")}
            hint={t("friends.no_following_hint")}
          />
        )
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
                  {user.biography ? <span className="muted small"> {user.biography}</span> : null}
                </span>
              </Link>
              {user.is_following === undefined ? (
                <Link to={`/u/${user.user_id}`}>
                  <Button variant="ghost">{t("common.open")}</Button>
                </Link>
              ) : (
                <Button
                  variant="ghost"
                  disabled={follow.isPending}
                  onClick={() => toggleFollow(user)}
                >
                  {t(user.is_following ? "common.unfollow" : "common.follow")}
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
