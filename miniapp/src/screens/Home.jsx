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
import { Button, Card, Coins, Skeleton, timeLeft } from "../components/ui";

export default function Home() {
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
                🔥 Серия побед: {me?.winning_streak ?? 0}
              </p>
            </>
          )}
        </div>
      </Card>

      <Button onClick={() => navigate("/scan")} className="cta">
        📷 Ввести код с крышки
      </Button>

      {activeBattle ? (
        <Card className="battle-teaser">
          <p className="eyebrow">Идёт баттл</p>
          <p className="battle-score">
            <strong>{activeBattle.challenger_votes}</strong>
            <span> : </span>
            <strong>{activeBattle.opponent_votes}</strong>
          </p>
          <p className="muted">
            {activeBattle.challenger.username} vs {activeBattle.opponent.username}
            {" · "}
            осталось {timeLeft(activeBattle.end_time)}
          </p>
          <Button
            variant="ghost"
            onClick={() => navigate(`/battle/${activeBattle.competition_id}`)}
          >
            Открыть
          </Button>
        </Card>
      ) : (
        <Card className="battle-teaser">
          <p className="eyebrow">Баттлов нет</p>
          <p className="muted">
            Вызови друга на баттл образов — победитель забирает весь призовой фонд.
          </p>
          <Button variant="ghost" onClick={() => navigate("/friends")}>
            Найти соперника
          </Button>
        </Card>
      )}

      <div className="quick-links">
        <Link to="/shop" className="quick-link">
          🛍<span>Магазин</span>
        </Link>
        <Link to="/wardrobe" className="quick-link">
          🎽<span>Гардероб</span>
        </Link>
        <Link to="/leaderboard" className="quick-link">
          🏆<span>Лидеры</span>
        </Link>
      </div>
    </div>
  );
}
