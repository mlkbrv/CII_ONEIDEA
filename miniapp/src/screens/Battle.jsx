/*
 * One battle: two outfits, the score, and the vote.
 *
 * This is the screen the whole product points at (TZ section 12), so it shows
 * the thing being judged — the two avatars, side by side, large — and nothing
 * else competes with them.
 *
 * A vote costs one coin and that coin goes into the prize pool (TZ section
 * 15), so the cost is stated on the button rather than discovered afterwards.
 * One vote per person: once cast, the buttons become a result readout.
 */
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useCoins, useCompetition, useMe, useVote } from "../api/queries";
import AvatarView from "../components/AvatarView";
import { Button, Card, ErrorState, Skeleton, timeLeft } from "../components/ui";
import { haptic } from "../platform/telegram";

export default function Battle() {
  const { competitionId } = useParams();
  const battle = useCompetition(competitionId);
  const { data: me } = useMe();
  const { data: coins } = useCoins();
  const vote = useVote();
  const [error, setError] = useState(null);

  if (battle.isError) return <ErrorState error={battle.error} onRetry={battle.refetch} />;
  if (battle.isLoading || !battle.data) {
    return (
      <div className="screen battle">
        <Skeleton height={280} radius={16} />
        <Skeleton height={60} radius={12} />
      </div>
    );
  }

  const data = battle.data;
  const isParticipant =
    me?.user_id === data.challenger.user_id || me?.user_id === data.opponent.user_id;
  const finished = data.status !== "active";
  const alreadyVoted = Boolean(data.my_vote_for);
  const total = data.challenger_votes + data.opponent_votes;

  async function castVote(userId) {
    setError(null);
    try {
      await vote.mutateAsync({ competitionId, votedForUserId: userId });
      haptic.success();
    } catch (err) {
      setError(
        {
          400: "Не хватает монет — один голос стоит 1 монету",
          403: "Участники не голосуют в своём баттле",
          409: "Ты уже голосовал в этом баттле",
        }[err.status] || err.detail || "Не удалось проголосовать"
      );
      haptic.error();
    }
  }

  return (
    <div className="screen battle">
      <Card className="battle-header">
        <p className="eyebrow">{finished ? "Баттл завершён" : "🔥 Идёт баттл"}</p>
        <p className="battle-score big">
          <strong>{data.challenger_votes}</strong>
          <span>:</span>
          <strong>{data.opponent_votes}</strong>
        </p>
        <p className="muted">
          Призовой фонд: {data.prize_pool} 🪙
          {finished ? "" : ` · осталось ${timeLeft(data.end_time)}`}
        </p>
      </Card>

      <div className="versus">
        <Side
          user={data.challenger}
          avatar={data.challenger_avatar}
          votes={data.challenger_votes}
          total={total}
          winner={finished && data.winner_id === data.challenger.user_id}
          chosen={data.my_vote_for === data.challenger.user_id}
        />
        <span className="vs" aria-hidden="true">
          VS
        </span>
        <Side
          user={data.opponent}
          avatar={data.opponent_avatar}
          votes={data.opponent_votes}
          total={total}
          winner={finished && data.winner_id === data.opponent.user_id}
          chosen={data.my_vote_for === data.opponent.user_id}
        />
      </div>

      {finished ? (
        <Card className="battle-result">
          {data.winner_id ? (
            <p>
              🏆 Победил{" "}
              <strong>
                {data.winner_id === data.challenger.user_id
                  ? data.challenger.username
                  : data.opponent.username}
              </strong>{" "}
              и забрал {data.prize_pool} 🪙
            </p>
          ) : (
            <p>🤝 Ничья — призовой фонд поделён поровну</p>
          )}
        </Card>
      ) : isParticipant ? (
        <Card className="muted">
          Это твой баттл. Зови подписчиков голосовать — каждый голос добавляет монету
          в призовой фонд.
        </Card>
      ) : alreadyVoted ? (
        <Card className="muted">Ты уже отдал свой голос в этом баттле.</Card>
      ) : (
        <div className="vote-actions">
          <Button
            disabled={vote.isPending || (coins?.balance ?? 0) < 1}
            onClick={() => castVote(data.challenger.user_id)}
          >
            За {data.challenger.username} · 1 🪙
          </Button>
          <Button
            disabled={vote.isPending || (coins?.balance ?? 0) < 1}
            onClick={() => castVote(data.opponent.user_id)}
          >
            За {data.opponent.username} · 1 🪙
          </Button>
          {(coins?.balance ?? 0) < 1 ? (
            <p className="muted small">
              Нужна хотя бы одна монета. <Link to="/scan">Активируй код с крышки</Link>.
            </p>
          ) : null}
        </div>
      )}

      {error ? <p className="status status-err">{error}</p> : null}
    </div>
  );
}

function Side({ user, avatar, votes, total, winner, chosen }) {
  // The bar is the share of the vote, so the fight is legible at a glance
  // rather than requiring arithmetic on two numbers.
  const share = total > 0 ? Math.round((votes / total) * 100) : 50;
  return (
    <div className={`side-card ${winner ? "is-winner" : ""} ${chosen ? "is-chosen" : ""}`}>
      <Link to={`/u/${user.user_id}`}>
        <AvatarView equipment={avatar?.equipment} size="100%" />
      </Link>
      <p className="side-name">
        {winner ? "🏆 " : ""}
        {user.username}
      </p>
      <div className="bar" aria-hidden="true">
        <span style={{ width: `${share}%` }} />
      </div>
      <p className="muted small">
        {votes} голосов · {share}%
      </p>
    </div>
  );
}
