/** Профиль: цель, язык, приватность, выход и удаление аккаунта.
 *
 *  Ни пейволла, ни призыва обновиться (спека §20, §24). Раздела разработчика с
 *  адресом API здесь нет: веб-клиент раздаётся тем же сервером, к которому ходит,
 *  и подменять адрес нечему.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, button, notice, sectionHeader, confirmDialog } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { session } from "../session.js";
import { navigate } from "../router.js";
import { LANGUAGES, language, selectLanguage } from "../l10n.js";
import { showPrivacy } from "./welcome.js";

export function profileView() {
  const node = h("div.page");
  let error = null;
  let busy = false;

  const changeRole = async (value) => {
    try {
      session.apply(await api.updateProfile({ targetRole: value || null }));
    } catch (apiError) {
      error = apiError;
      render();
    }
  };

  const signOut = async () => {
    const confirmed = await confirmDialog({
      title: S.Profile.signOutQuestion,
      message: S.Profile.signOutMessage,
      confirmTitle: S.Profile.signOut,
      destructive: true,
    });
    if (confirmed) await session.signOut();
  };

  const deleteAccount = async () => {
    const confirmed = await confirmDialog({
      title: S.Profile.deleteQuestion,
      message: S.Profile.deleteMessage,
      confirmTitle: S.Profile.deletePermanently,
      destructive: true,
    });
    if (!confirmed) return;
    busy = true;
    render();
    try {
      await session.deleteAccount();
    } catch (apiError) {
      error = apiError;
      busy = false;
      render();
    }
  };

  const labeled = (label, value) =>
    h("div.row", h("span.grow.muted", label), h("span", { style: { fontWeight: "500" } }, value));

  const render = () => {
    const me = session.me;
    fill(
      node,
      h("h1", S.Profile.title),
      me &&
        h(
          "div.stack",
          sectionHeader(S.Profile.practiceSection),
          card(
            h(
              "div.stack.s",
              labeled(S.Profile.level, String(me.level)),
              labeled(S.Profile.totalXp, String(me.totalXp)),
              labeled(S.Profile.targetRole, S.Roles.title(me.targetRole))
            )
          )
        ),
      // Глоссарий доступен и из урока, и отсюда: для новичка это условие
      // читаемости домена, а не украшение.
      h(
        "button.rowlink.card",
        { type: "button", onclick: () => navigate("/glossary") },
        icon("character.book.closed", { size: 18 }),
        h("span.grow.title", S.Glossary.title),
        icon("chevron.right", { size: 14, className: "tertiary" })
      ),
      h(
        "div.stack",
        sectionHeader(S.Profile.roleSection, S.Profile.roleFooter),
        card(
          h(
            "select",
            {
              "aria-label": S.Profile.targetRole,
              onchange: (event) => changeRole(event.target.value),
            },
            h("option", { value: "", selected: !me?.targetRole }, S.Roles.none),
            S.Roles.keys.map((key) =>
              h("option", { value: key, selected: me?.targetRole === key }, S.Roles.title(key))
            )
          )
        )
      ),
      h(
        "div.stack",
        sectionHeader(S.Profile.languageSection, S.Profile.languageFooter),
        card(
          h(
            "div.segmented",
            LANGUAGES.map((option) =>
              h(
                `button${option.code === language() ? ".selected" : ""}`,
                { type: "button", onclick: () => selectLanguage(option.code) },
                option.displayName
              )
            )
          )
        )
      ),
      h(
        "div.stack",
        sectionHeader(S.Profile.privacySection),
        h(
          "button.rowlink.card",
          { type: "button", onclick: showPrivacy },
          icon("hand.raised", { size: 18 }),
          h("span.grow.title", S.Profile.privacyNotice),
          icon("chevron.right", { size: 14, className: "tertiary" })
        )
      ),
      error && notice(error.userMessage, { symbol: "exclamationmark.circle", tone: "negative" }),
      h(
        "div.stack.s",
        button(S.Profile.signOut, signOut, { variant: "secondary", symbol: "rectangle.portrait.and.arrow.right" }),
        button(busy ? S.Profile.deleting : S.Profile.deleteAccount, deleteAccount, {
          variant: "destructive",
          symbol: "trash",
          disabled: busy,
        }),
        h("p.caption.tertiary", S.Profile.deleteFooter)
      )
    );
  };

  const unsubscribe = () => session.removeEventListener("change", render);
  session.addEventListener("change", render);
  node.dispose = unsubscribe;

  render();
  return node;
}
