/** Онбординг: как устроен маршрут и необязательная целевая роль.
 *
 *  Диагностика из v0.1 убрана: новичку нечего диагностировать, а вопросы стояли
 *  барьером перед первым уроком (спека v0.2 §10).
 */
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { button, notice } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { session } from "../session.js";

export function onboardingView() {
  const node = h("div.page", { style: { maxWidth: "620px" } });
  let step = "howItWorks";
  let selectedRole = session.me?.targetRole ?? null;
  let error = null;
  let busy = false;

  const render = () => {
    node.replaceChildren(step === "howItWorks" ? howItWorks() : roleStep());
  };

  const howItWorks = () => {
    const steps = [
      ["map", S.Onboarding.stepMapTitle, S.Onboarding.stepMapBody],
      ["circle.circle", S.Onboarding.stepRingsTitle, S.Onboarding.stepRingsBody],
      ["book", S.Onboarding.stepLessonsTitle, S.Onboarding.stepLessonsBody],
      ["flag.checkered", S.Onboarding.stepGateTitle, S.Onboarding.stepGateBody],
      ["lock.open", S.Onboarding.stepUnlockTitle, S.Onboarding.stepUnlockBody],
    ];
    return h(
      "div.stack.xl",
      h(
        "div.stack.s",
        h("h1", S.Onboarding.howItWorksTitle),
        h("p.muted", S.Onboarding.howItWorksSubtitle)
      ),
      h(
        "div.stack",
        steps.map(([symbol, title, body]) =>
          h(
            "div.card.row.top",
            icon(symbol, { size: 22 }),
            h("div.stack.s", h("h3", title), h("p.small.muted", body))
          )
        )
      ),
      notice(S.Onboarding.ownPace, { symbol: "tortoise" }),
      button(S.Common.continueAction, () => {
        step = "role";
        render();
      }, { wide: true })
    );
  };

  const roleStep = () =>
    h(
      "div.stack.xl",
      h("div.stack.s", h("h1", S.Onboarding.roleTitle), h("p.muted", S.Onboarding.roleSubtitle)),
      h(
        "div.stack.s",
        S.Roles.keys.map((key) =>
          h(
            `button.option${selectedRole === key ? ".selected" : ""}`,
            {
              type: "button",
              style: { padding: "12px 16px", alignItems: "center" },
              onclick: () => {
                selectedRole = selectedRole === key ? null : key;
                render();
              },
            },
            icon(selectedRole === key ? "checkmark.circle.fill" : "circle", { size: 18 }),
            h("span", S.Roles.title(key))
          )
        )
      ),
      error && notice(error.userMessage, { symbol: "exclamationmark.circle", tone: "negative" }),
      h(
        "div.stack.s",
        button(S.Onboarding.startLearning, () => finish(selectedRole), { wide: true, disabled: busy }),
        button(S.Onboarding.skipRole, () => finish(null), { variant: "quiet" })
      )
    );

  const finish = async (role) => {
    busy = true;
    error = null;
    render();
    try {
      const profile = await api.updateProfile({
        targetRole: role,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        completeOnboarding: true,
      });
      session.apply(profile);
    } catch (apiError) {
      error = apiError;
    } finally {
      busy = false;
      render();
    }
  };

  render();
  return node;
}
