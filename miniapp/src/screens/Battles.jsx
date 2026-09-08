/*
 * Battles — the two views TZ section 14 asks for.
 *
 * "Мои" holds anything involving the player: incoming challenges they have to
 * answer, challenges they sent, and their live battle. Incoming requests sit
 * at the top because they are the only thing here that is blocked on the user
 * doing something.
 *
 * "Другие" is the feed of battles from people they follow, which is where the
 * voting economy lives (TZ section 15).
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  useDiscover,
  useMyCompetitions,
  useRequests,
  useRespondToRequest,
} from "../api/queries";
import { Button, Card, EmptyState, ErrorState, Skeleton, Tabs, timeLeft } from "../components/ui";
import { haptic } from "../platform/telegram";

export default function Battles() {
  const [tab, setTab] = useState("mine");

  return (
    <div className="screen battles">
      <Tabs
        value={tab}
        onChange={setTab}
        options={[
          { value: "mine", label: "Мои" },
          { value: "others", label: "Другие" },
        ]}
      />
      {tab === "mine" ? <MyBattles /> : <OtherBattles />}
    </div>
  );
}

function MyBattles() {
  const navigate = useNavigate();
  const incoming = useRequests("incoming");
  const outgoing = useRequests("outgoing");
  const active = useMyCompetitions("active");
  const respond = useRespondToRequest();
  const [error, setError] = useState(null);

  async function answer(requestId, action) {
    setError(null);
    try {
      await respond.mutateAsync({ requestId, action });
      haptic.success();
    } catch (err) {
      setError(
        err.status === 409
          ? "Кто-то из вас уже в баттле — этот вызов больше не действителен"
          : err.detail || "Не удалось ответить на вызов"
      );
      haptic.error();
    }
  }

  if (incoming.isLoading || active.isLoading) {
    return (
      <div className="list">
        {Array.from({ length: 3 }, (_, index) => (
          <Skeleton key={index} height={90} radius={14} />
        ))}
      </div>
    );
  }
  if (incoming.isError) return <ErrorState error={incoming.error} onRetry={incoming.refetch} />;

  const pendingIn = incoming.data ?? [];
  const pendingOut = outgoing.data ?? [];
  const live = active.data ?? [];

  if (!pendingIn.length && !pendingOut.length && !live.length) {
    return (
      <EmptyState
        icon="⚔️"
        title="Пока пусто"
        hint="Вызови кого-нибудь на баттл образов — победитель забирает весь призовой фонд."
        action={
          <Link to="/friends">
            <Button variant="ghost">К друзьям</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="list">
      {error ? <p className="status status-err">{error}</p> : null}

      {pendingIn.map((request) => (
        <Card key={request.request_id} className="request">
          <p>
            <strong>{request.challenger.username}</strong> вызывает тебя на баттл
          </p>
          <p className="muted small">{humanDuration(request.duration_minutes)}</p>
          <div className="row-actions">
            <Button disabled={respond.isPending} onClick={() => answer(request.request_id, "accept")}>
              Принять
            </Button>
            <Button
              variant="ghost"
              disabled={respond.isPending}
              onClick={() => answer(request.request_id, "decline")}
            >
              Отклонить
            </Button>
          </div>
        </Card>
      ))}

      {live.map((battle) => (
        <BattleCard key={battle.competition_id} battle={battle} onOpen={navigate} live />
      ))}

      {pendingOut.map((request) => (
        <Card key={request.request_id} className="request">
          <p className="muted">
            Ты вызвал <strong>{request.opponent.username}</strong> — ждём ответа
          </p>
          <Button
            variant="ghost"
            disabled={respond.isPending}
            onClick={() => answer(request.request_id, "cancel")}
          >
            Отменить вызов
          </Button>
        </Card>
      ))}
    </div>
  );
}

function OtherBattles() {
  const navigate = useNavigate();
  const [scope, setScope] = useState("following");
  const discover = useDiscover(scope);

  if (discover.isError) return <ErrorState error={discover.error} onRetry={discover.refetch} />;

  const battles = discover.data?.items ?? [];

  return (
    <>
      <Tabs
        value={scope}
        onChange={setScope}
        options={[
          { value: "following", label: "Мои подписки" },
          { value: "all", label: "Все" },
        ]}
      />
      {discover.isLoading ? (
        <div className="list">
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} height={90} radius={14} />
          ))}
        </div>
      ) : battles.length === 0 ? (
        <EmptyState
          icon="🍿"
          title={scope === "following" ? "У твоих подписок нет баттлов" : "Сейчас никто не сражается"}
          hint={
            scope === "following"
              ? "Подпишись на больше игроков или посмотри все баттлы."
              : "Загляни позже — или начни свой."
          }
        />
      ) : (
        <div className="list">
          {battles.map((battle) => (
            <BattleCard key={battle.competition_id} battle={battle} onOpen={navigate} />
          ))}
        </div>
      )}
    </>
  );
}

function BattleCard({ battle, onOpen, live = false }) {
  return (
    <Card className="battle-card" onClick={() => onOpen(`/battle/${battle.competition_id}`)}>
      <div className="battle-row">
        <span className="side">{battle.challenger.username}</span>
        <span className="score">
          {battle.challenger_votes} : {battle.opponent_votes}
        </span>
        <span className="side">{battle.opponent.username}</span>
      </div>
      <p className="muted small">
        {live ? "Твой баттл · " : ""}
        Приз: {battle.prize_pool} 🪙 · осталось {timeLeft(battle.end_time)}
      </p>
    </Card>
  );
}

function humanDuration(minutes) {
  if (minutes < 60) return `${minutes} минут`;
  const hours = minutes / 60;
  if (hours === 1) return "1 час";
  if (hours < 5) return `${hours} часа`;
  return `${hours} часов`;
}
