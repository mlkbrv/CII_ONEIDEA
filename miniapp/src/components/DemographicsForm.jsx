/*
 * The optional "tell us about yourself" form: gender and year of birth.
 *
 * Telegram does not share either with a Mini App, so the only way to know is
 * to ask. It is optional on purpose, a skipped form is remembered so it is
 * not shown again, and answering earns a one-time coin bonus (the server pays
 * it, this only displays what the server says).
 *
 * Shown once on first launch (DemographicsGate) and again from the profile for
 * anyone who skipped.
 */
import { useEffect, useRef, useState } from "react";

import { useMe, useSkipDemographics, useSubmitDemographics } from "../api/queries";
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";
import { Button, Card } from "./ui";

const GENDERS = ["male", "female", "undisclosed"];
const OLDEST = 100;
const YOUNGEST = 10;

function birthYears() {
  const year = new Date().getFullYear();
  const years = [];
  for (let value = year - YOUNGEST; value >= year - OLDEST; value -= 1) years.push(value);
  return years;
}

export default function DemographicsForm({ onClose }) {
  const t = useT();
  const { data: me } = useMe();
  const submit = useSubmitDemographics();
  const skip = useSkipDemographics();

  const [gender, setGender] = useState(me?.gender ?? null);
  const [year, setYear] = useState(me?.birth_year ? String(me.birth_year) : "");
  const [error, setError] = useState(false);
  const [bonus, setBonus] = useState(null);

  const ready = gender !== null || year !== "";
  const busy = submit.isPending || skip.isPending;

  async function save() {
    setError(false);
    try {
      const answers = {};
      if (gender) answers.gender = gender;
      if (year) answers.birth_year = Number(year);
      const result = await submit.mutateAsync(answers);
      haptic.success();
      if (result.bonus_coins > 0) setBonus(result.bonus_coins);
      else onClose();
    } catch {
      haptic.error();
      setError(true);
    }
  }

  async function later() {
    try {
      if (me?.demographics_status === null || me?.demographics_status === undefined) {
        await skip.mutateAsync();
      }
    } finally {
      onClose();
    }
  }

  if (bonus !== null) {
    return (
      <div className="sheet-backdrop">
        <Card className="sheet">
          <h2 className="screen-title">{t("demographics.thanks")}</h2>
          <p className="muted">
            {t("demographics.bonus_received")} <strong>+{bonus}</strong> {t("common.coins")}
          </p>
          <Button onClick={onClose}>{t("demographics.close")}</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="sheet-backdrop">
      <Card className="sheet">
        <h2 className="screen-title">{t("demographics.title")}</h2>
        <p className="muted small">{t("demographics.subtitle")}</p>

        <p className="muted small">{t("demographics.gender")}</p>
        <div className="row-actions">
          {GENDERS.map((option) => (
            <Button
              key={option}
              variant={gender === option ? "primary" : "ghost"}
              onClick={() => setGender(option)}
              disabled={busy}
            >
              {t(`demographics.gender_${option}`)}
            </Button>
          ))}
        </div>

        <label className="muted small" htmlFor="birth-year">
          {t("demographics.year")}
        </label>
        <select
          id="birth-year"
          className="field"
          value={year}
          onChange={(event) => setYear(event.target.value)}
          disabled={busy}
        >
          <option value="">{t("demographics.year_placeholder")}</option>
          {birthYears().map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>

        <p className="muted small">{t("demographics.privacy")}</p>
        {error ? <p className="status status-err">{t("demographics.error")}</p> : null}

        <div className="row-actions">
          <Button onClick={save} disabled={!ready || busy}>
            {t("demographics.save")}
          </Button>
          <Button variant="ghost" onClick={later} disabled={busy}>
            {t("demographics.skip")}
          </Button>
        </div>
      </Card>
    </div>
  );
}

/** Opens the form by itself, once, for a player who has never been asked. */
export function DemographicsGate() {
  const { data: me } = useMe();
  const [open, setOpen] = useState(false);
  const decided = useRef(false);

  // Decided once, when the account first arrives: saving refreshes /users/me
  // and flips the status, which must not close the thank-you screen early.
  useEffect(() => {
    if (!me || decided.current) return;
    decided.current = true;
    if (me.demographics_status === null || me.demographics_status === undefined) setOpen(true);
  }, [me]);

  return open ? <DemographicsForm onClose={() => setOpen(false)} /> : null;
}
