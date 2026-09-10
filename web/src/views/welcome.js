/** Вход и регистрация.
 *
 *  Одна форма на два режима: поля у входа и регистрации одинаковые, разное только
 *  то, что делает сервер. Отдельный экран регистрации заставлял бы человека
 *  вспоминать, регистрировался он уже или нет, — а это он и так не помнит.
 *
 *  Какие способы показывать, решает сервер (`GET /v1/auth/methods`): кнопка Google
 *  без настроенного Client ID — обещание, которого сервер не выполнит.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { button, notice, sheet } from "../components.js";
import { S } from "../strings.js";
import { session } from "../session.js";
import { api } from "../api.js";
import { onLanguageChange } from "../l10n.js";

const PASSWORD_MIN = 8;

export function welcomeView() {
  const node = h("div.page", { style: { maxWidth: "420px", paddingTop: "7vh" } });
  let mode = "signin";
  let methods = null;
  let formError = null;
  const form = { email: "", password: "" };

  const submit = async () => {
    formError = null;
    if (!form.email.includes("@")) {
      formError = S.Auth.emailInvalid;
      render();
      return;
    }
    if (form.password.length < PASSWORD_MIN) {
      formError = S.Auth.passwordRule(PASSWORD_MIN);
      render();
      return;
    }
    if (mode === "signup") await session.signUp(form.email, form.password);
    else await session.signInWithPassword(form.email, form.password);
  };

  const field = (label, key, type, autocomplete) =>
    h(
      "label.stack.s",
      h("span.small", { style: { fontWeight: "600" } }, label),
      h("input", {
        type,
        value: form[key],
        autocomplete,
        placeholder: key === "email" ? S.Auth.emailPlaceholder : "",
        oninput: (event) => {
          form[key] = event.target.value;
        },
        onkeydown: (event) => {
          if (event.key === "Enter") submit();
        },
      })
    );

  const passwordForm = () =>
    h(
      "form.stack",
      {
        onsubmit: (event) => {
          event.preventDefault();
          submit();
        },
      },
      field(S.Auth.email, "email", "email", "email"),
      field(
        S.Auth.password,
        "password",
        "password",
        mode === "signup" ? "new-password" : "current-password"
      ),
      mode === "signup" && h("p.caption.tertiary", S.Auth.passwordRule(PASSWORD_MIN)),
      button(mode === "signup" ? S.Auth.signUp : S.Auth.signIn, submit, {
        wide: true,
        disabled: session.isAuthenticating,
      }),
      h(
        "button.btn.quiet",
        {
          type: "button",
          onclick: () => {
            mode = mode === "signup" ? "signin" : "signup";
            formError = null;
            render();
          },
        },
        mode === "signup" ? S.Auth.haveAccount : S.Auth.needAccount
      )
    );

  /** Кнопку рисует сам Google: подпись, тема и язык — его, а токен приходит в
   *  колбэк. Скрипт грузится только когда сервер сказал, что Google настроен. */
  const googleButton = () => {
    const holder = h("div", { style: { display: "flex", justifyContent: "center" } });
    const render_ = () => {
      if (!window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: methods.googleClientId,
        callback: (response) => session.signInWithGoogle(response.credential),
      });
      window.google.accounts.id.renderButton(holder, {
        theme: "outline",
        size: "large",
        width: 320,
        text: mode === "signup" ? "signup_with" : "signin_with",
      });
    };
    if (window.google?.accounts?.id) {
      queueMicrotask(render_);
    } else {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.onload = render_;
      document.head.append(script);
    }
    return holder;
  };

  const separator = () =>
    h(
      "div.row",
      { style: { color: "var(--text-tertiary)" } },
      h("span", { style: { flex: 1, height: "1px", background: "var(--separator)" } }),
      h("span.caption", S.Auth.or),
      h("span", { style: { flex: 1, height: "1px", background: "var(--separator)" } })
    );

  const render = () => {
    const error = formError || session.authError?.userMessage;
    const nothing = methods && !methods.password && !methods.google && !methods.developer;

    fill(
      node,
      h(
        "div.stack.l",
        { style: { alignItems: "center", textAlign: "center", padding: "20px 0 8px" } },
        icon("arrow.triangle.branch", { size: 48 }),
        h("h1", S.Welcome.headline)
      ),
      session.isAuthenticating
        ? h("div.state", h("div.spinner"))
        : h(
            "div.stack",
            nothing && notice(S.Auth.noMethods, { symbol: "exclamationmark.triangle", tone: "caution" }),
            methods?.google && googleButton(),
            methods?.google && methods?.password && separator(),
            methods?.password && passwordForm(),
            methods?.developer &&
              button(S.Welcome.developerSignIn, () => session.signInAsDeveloper(), {
                variant: "quiet",
              })
          ),
      error && notice(error, { symbol: "exclamationmark.circle", tone: "negative" }),
      button(S.Welcome.privacyNotice, showPrivacy, { variant: "quiet" })
    );
  };

  api
    .authMethods()
    .then((response) => {
      methods = response;
      render();
    })
    .catch(() => {
      // Сервер не ответил: показываем форму пароля, а не пустой экран — она
      // работает всюду, где вход вообще включён.
      methods = { password: true, google: false, apple: false, developer: false };
      render();
    });

  session.addEventListener("change", render);
  const stopLanguage = onLanguageChange(render);
  node.dispose = () => {
    session.removeEventListener("change", render);
    stopLanguage();
  };
  render();
  return node;
}

export function showPrivacy() {
  const items = [
    [S.Privacy.accountTitle, S.Privacy.accountBody],
    [S.Privacy.writingTitle, S.Privacy.writingBody],
    [S.Privacy.analyticsTitle, S.Privacy.analyticsBody],
    [S.Privacy.deletionTitle, S.Privacy.deletionBody],
    [S.Privacy.scoresTitle, S.Privacy.scoresBody],
  ];
  sheet(
    S.Privacy.heading,
    h(
      "div.stack.l",
      items.map(([title, body]) => h("div.stack.s", h("h3", title), h("p.small.muted", body)))
    )
  );
}
