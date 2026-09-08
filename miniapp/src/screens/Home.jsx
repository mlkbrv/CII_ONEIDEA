/*
 * Home — where the loop starts and ends.
 *
 * The core loop is buy a bottle, redeem the cap, spend the coins, challenge
 * someone (TZ section 1). So the two things on screen above the fold are the
 * balance and the button that grows it; a live battle takes the top spot when
 * there is one, because it is on a clock and everything else can wait.
 */
import { Link, useNavigate } from "react-router-dom";

import { useCoins, useMe, useMyAvatar, useMyCompetitions } from "../api/queries";
import AvatarView from "../components/AvatarView";
import { useT } from "../i18n";
import { Button, Card, Coins, Skeleton, timeLeft } from "../components/ui";

export default function Home() {
  const t = useT();
  const navigate = useNavigate();
  const { data: me, isLoading: meLoading } = useMe();
  const { data: coins } = useCoins();
  const { data: avatar } = useMyAvatar();
  const { data: competitions } = useMyCompetitions("active");

  const activeBattle = competitions?.[0];

  return (
    <div className="screen home">
      <Card className="hero">
        <div className="hero-avatar">
          <AvatarView equipment={avatar?.equipment} size="120px" />
        </div>
        <div className="hero-text">
          {meLoading ? (
            <>
              <Skeleton width="60%" height={22} />
              <Skeleton width="40%" height={16} />
            </>
          ) : (
            <>
              <p className="hero-name">{me?.username}</p>
              <p className="hero-balance">
                <Coins amount={coins?.balance} />
              </p>
              <p className="hero-streak">
                🔥 {t("common.streak")}: {me?.winning_streak ?? 0}
              </p>
            </>
          )}
        </div>
      </Card>

      <Button onClick={() => navigate("/scan")} className="cta">
        {t("home.scan_cta")}
      </Button>

      {activeBattle ? (
        <Card className="battle-teaser">
          <p className="eyebrow">{t("home.battle_running")}</p>
          <p className="battle-score">
            <strong>{activeBattle.challenger_votes}</strong>
            <span> : </span>
            <strong>{activeBattle.opponent_votes}</strong>
          </p>
          <p className="muted">
            {activeBattle.challenger.username} vs {activeBattle.opponent.username}
            {" · "}
            {t("home.time_left", { time: timeLeft(activeBattle.end_time, t) })}
          </p>
          <Button
            variant="ghost"
            onClick={() => navigate(`/battle/${activeBattle.competition_id}`)}
          >
            {t("common.open")}
          </Button>
        </Card>
      ) : (
        <Card className="battle-teaser">
          <p className="eyebrow">{t("home.no_battles")}</p>
          <p className="muted">{t("home.no_battles_hint")}</p>
          <Button variant="ghost" onClick={() => navigate("/friends")}>
            {t("home.find_opponent")}
          </Button>
        </Card>
      )}

      <div className="quick-links">
        <Link to="/shop" className="quick-link">
          🛍<span>{t("common.shop")}</span>
        </Link>
        <Link to="/wardrobe" className="quick-link">
          🎽<span>{t("common.wardrobe")}</span>
        </Link>
        <Link to="/leaderboard" className="quick-link">
          🏆<span>{t("home.leaders")}</span>
        </Link>
      </div>
    </div>
  );
}
