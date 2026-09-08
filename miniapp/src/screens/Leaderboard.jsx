/*
 * Leaderboard — TZ section 17.
 *
 * Two rankings, because they answer different questions: the streak rewards
 * being hot right now (and is the thing the game asks you to protect, TZ
 * section 13), total wins rewards having been good all along.
 *
 * The caller's own row is pinned at the bottom whenever they are not on the
 * visible page. A leaderboard you cannot find yourself on gives a new player
 * nothing to aim at.
 */
import { useState } from "react";
import { Link } from "react-router-dom";

import { useLeaderboard } from "../api/queries";
import { Card, EmptyState, ErrorState, Skeleton, Tabs } from "../components/ui";
import { useT } from "../i18n";

export default function Leaderboard() {
  const t = useT();
  const [metric, setMetric] = useState("streak");
  const board = useLeaderboard(metric);

  if (board.isError) return <ErrorState error={board.error} onRetry={board.refetch} />;

  const rows = board.data?.items ?? [];
  const me = board.data?.me;
  const meOnPage = rows.some((row) => row.is_self);

  return (
    <div className="screen leaderboard">
      <Tabs
        value={metric}
        onChange={setMetric}
        options={[
          { value: "streak", label: t("leaderboard.streak") },
          { value: "wins", label: t("leaderboard.wins") },
        ]}
      />

      {board.isLoading ? (
        <div className="list">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} height={52} radius={12} />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="🏆"
          title={t("leaderboard.empty")}
          hint={t("leaderboard.empty_hint")}
        />
      ) : (
        <div className="list">
          {rows.map((row) => (
            <Row key={row.user_id} row={row} metric={metric} />
          ))}
        </div>
      )}

      {me && !meOnPage ? (
        <div className="pinned-me">
          <p className="muted small">{t("leaderboard.you_are_here")}</p>
          <Row row={me} metric={metric} />
        </div>
      ) : null}
    </div>
  );
}

function Row({ row, metric }) {
  // The top three get medals; below that the number is clearer than an icon.
  const medal = { 1: "🥇", 2: "🥈", 3: "🥉" }[row.rank];
  return (
    <Link to={`/u/${row.user_id}`}>
      <Card className={`rank-row ${row.is_self ? "is-self" : ""}`}>
        <span className="rank">{medal ?? row.rank}</span>
        <span className="rank-name">{row.username}</span>
        <span className="rank-value">
          {metric === "streak" ? `🔥 ${row.winning_streak}` : `🏆 ${row.competitions_won}`}
        </span>
      </Card>
    </Link>
  );
}
