/*
 * Battles — the two views TZ section 14 asks for.
 *
 * "Mine" holds anything involving the player: incoming challenges they have
 * to answer, challenges they sent, and their live battle. Incoming requests
 * sit at the top because they are the only thing here that is blocked on the
 * user doing something.
 *
 * "Others" is the feed of battles from people they follow, which is where the
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
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";

export default function Battles() {
  const t = useT();
  const [tab, setTab] = useState("mine");

  return (
    <div className="screen battles">
      <Tabs
        value={tab}
        onChange={setTab}
        options={[
          { value: "mine", label: t("battles.mine") },
          { value: "others", label: t("battles.others") },
        ]}
      />
      {tab === "mine" ? <MyBattles /> : <OtherBattles />}
    </div>
  );
}

function MyBattles() {
  const t = useT();
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
      setError(t(err.status === 409 ? "battles.err_conflict" : "battles.err_generic"));
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
        title={t("battles.empty")}
        hint={t("battles.empty_hint")}
        action={
          <Link to="/friends">
            <Button variant="ghost">{t("battles.to_friends")}</Button>
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
          <p>{t("battles.challenges_you", { username: request.challenger.username })}</p>
          <p className="muted small">{t(`duration.${request.duration_minutes}`)}</p>
          <div className="row-actions">
            <Button disabled={respond.isPending} onClick={() => answer(request.request_id, "accept")}>
              {t("battles.accept")}
            </Button>
            <Button
              variant="ghost"
              disabled={respond.isPending}
              onClick={() => answer(request.request_id, "decline")}
            >
              {t("battles.decline")}
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
            {t("battles.you_challenged", { username: request.opponent.username })}
          </p>
          <Button
            variant="ghost"
            disabled={respond.isPending}
            onClick={() => answer(request.request_id, "cancel")}
          >
            {t("battles.cancel_challenge")}
          </Button>
        </Card>
      ))}
    </div>
  );
}

function OtherBattles() {
  const t = useT();
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
          { value: "following", label: t("battles.my_subscriptions") },
          { value: "all", label: t("battles.all") },
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
          title={t(
            scope === "following" ? "battles.none_following" : "battles.none_at_all"
          )}
          hint={t(
            scope === "following"
              ? "battles.none_following_hint"
              : "battles.none_at_all_hint"
          )}
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
  const t = useT();
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
        {live ? t("battles.mine_prefix") : ""}
        {t("battles.card_meta", {
          prize: battle.prize_pool,
          time: timeLeft(battle.end_time, t),
        })}
      </p>
    </Card>
  );
}
