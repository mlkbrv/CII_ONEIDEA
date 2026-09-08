/*
 * The shop.
 *
 * TZ section 5 asks for filter, select, preview on the avatar, then buy. The
 * preview is the part that matters: nobody spends 900 coins on a shape in a
 * grid, so tapping an item puts it straight onto the player's own bear, over
 * whatever they are already wearing.
 */
import { useMemo, useState } from "react";

import { useCoins, useMyAvatar, usePurchase, useShop, useWardrobe } from "../api/queries";
import AvatarView, { ItemThumb } from "../components/AvatarView";
import { Button, Card, Coins, ErrorState, Skeleton, Tabs } from "../components/ui";
import { haptic } from "../platform/telegram";

export default function Shop() {
  const [category, setCategory] = useState(null);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState(null);

  const shop = useShop();
  const { data: avatar } = useMyAvatar();
  const { data: coins } = useCoins();
  const { data: wardrobe } = useWardrobe();
  const purchase = usePurchase();

  // The categories come out of the items themselves. There is no public
  // categories endpoint, and with a catalogue this size deriving them is one
  // less request and one less thing that can disagree with the catalogue.
  const categories = useMemo(() => {
    const seen = new Map();
    for (const item of shop.data?.items ?? []) {
      if (!seen.has(item.category.category_id)) {
        seen.set(item.category.category_id, item.category.category_name);
      }
    }
    return [...seen.entries()].map(([value, label]) => ({ value, label }));
  }, [shop.data]);

  const owned = useMemo(
    () => new Set((wardrobe?.items ?? []).map((entry) => entry.item.item_id)),
    [wardrobe]
  );

  const items = (shop.data?.items ?? []).filter(
    (item) => category === null || item.category.category_id === category
  );

  async function buy(item) {
    setMessage(null);
    try {
      const result = await purchase.mutateAsync(item.item_id);
      setMessage({
        ok: true,
        text: `${item.name} — куплено! Осталось ${result.remaining_balance} монет`,
      });
      haptic.success();
    } catch (err) {
      setMessage({
        ok: false,
        text:
          err.status === 400
            ? "Не хватает монет — активируй ещё одну крышку"
            : err.status === 409
              ? "Эта вещь уже у тебя в гардеробе"
              : err.detail || "Не удалось купить",
      });
      haptic.error();
    }
  }

  if (shop.isError) return <ErrorState error={shop.error} onRetry={shop.refetch} />;

  return (
    <div className="screen shop">
      <Card className="shop-preview">
        <AvatarView equipment={avatar?.equipment} preview={selected} size="150px" />
        <div className="shop-preview-info">
          {selected ? (
            <>
              <p className="item-name">{selected.name}</p>
              {selected.description ? (
                <p className="muted small">{selected.description}</p>
              ) : null}
              <p>
                <Coins amount={selected.price} />
              </p>
              {owned.has(selected.item_id) ? (
                <Button variant="ghost" disabled>
                  Уже в гардеробе
                </Button>
              ) : (
                <Button
                  onClick={() => buy(selected)}
                  disabled={purchase.isPending || (coins?.balance ?? 0) < selected.price}
                >
                  {purchase.isPending
                    ? "Покупаем…"
                    : (coins?.balance ?? 0) < selected.price
                      ? "Не хватает монет"
                      : "Купить"}
                </Button>
              )}
            </>
          ) : (
            <p className="muted">
              Выбери вещь — примерим её на твоём медведе, прежде чем покупать.
            </p>
          )}
        </div>
      </Card>

      {message ? (
        <p className={`status ${message.ok ? "status-ok" : "status-err"}`}>{message.text}</p>
      ) : null}

      <Tabs
        value={category}
        onChange={setCategory}
        options={[{ value: null, label: "Все" }, ...categories]}
      />

      {shop.isLoading ? (
        <div className="grid">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height={120} radius={14} />
          ))}
        </div>
      ) : (
        <div className="grid">
          {items.map((item) => (
            <button
              key={item.item_id}
              className={`tile ${selected?.item_id === item.item_id ? "is-selected" : ""}`}
              onClick={() => {
                haptic.tap();
                setSelected(item);
              }}
            >
              <ItemThumb item={item} />
              <span className="tile-name">{item.name}</span>
              <span className="tile-price">
                {owned.has(item.item_id) ? "✓ есть" : <Coins amount={item.price} />}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
