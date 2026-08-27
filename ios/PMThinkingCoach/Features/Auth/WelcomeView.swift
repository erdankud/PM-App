import AuthenticationServices
import SwiftUI

/// Welcome / sign-in (spec §10.1).
struct WelcomeView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var container: AppContainer
    @EnvironmentObject private var language: LanguageStore
    @State private var showingPrivacy = false

    var body: some View {
        VStack(spacing: Theme.Spacing.xl) {
            languageToggle
                .padding(.horizontal, Theme.Spacing.l)
                .padding(.top, Theme.Spacing.s)
                .appear(0)

            Spacer()

            VStack(spacing: Theme.Spacing.l) {
                Image(systemName: "arrow.triangle.branch")
                    .font(.system(size: 56, weight: .semibold))
                    .foregroundStyle(Theme.Palette.accent)
                    .appear(1)

                Text(S.Welcome.headline)
                    .font(.largeTitle.weight(.bold))
                    .multilineTextAlignment(.center)
                    .appear(2)

                Text(S.Welcome.subheadline)
                    .font(.title3)
                    .foregroundStyle(Theme.Palette.secondaryText)
                    .multilineTextAlignment(.center)
                    .appear(3)
            }
            .padding(.horizontal, Theme.Spacing.l)

            Spacer()

            VStack(spacing: Theme.Spacing.m) {
                SignInWithAppleButton(.continue) { request in
                    request.requestedScopes = []
                } onCompletion: { result in
                    handle(result)
                }
                .signInWithAppleButtonStyle(.black)
                .frame(height: 50)
                .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.control))
                .disabled(session.isAuthenticating)
                .accessibilityLabel(S.Welcome.continueWithApple)

                if AppConfig.allowsDeveloperSignIn {
                    Button(S.Welcome.developerSignIn) {
                        Task { await session.signInAsDeveloper() }
                    }
                    .font(.footnote)
                    .foregroundStyle(Theme.Palette.secondaryText)
                    .frame(minHeight: Theme.minimumTapTarget)
                    .disabled(session.isAuthenticating)
                }

                if let error = session.authError {
                    InlineNotice(
                        text: error.userMessage,
                        systemImage: "exclamationmark.circle",
                        tint: Theme.Palette.negative
                    )
                    .padding(.horizontal, Theme.Spacing.s)
                }

                Button(S.Welcome.privacyNotice) { showingPrivacy = true }
                    .font(.footnote)
                    .frame(minHeight: Theme.minimumTapTarget)
            }
            .animation(Motion.standard, value: session.authError)
            .padding(.horizontal, Theme.Spacing.xl)
            .padding(.bottom, Theme.Spacing.xl)
            .appear(4)

            if session.isAuthenticating {
                ProgressView()
                    .padding(.bottom, Theme.Spacing.l)
                    .transition(.opacity)
            }
        }
        .animation(Motion.quick, value: session.isAuthenticating)
        .background(Theme.Palette.background)
        .sheet(isPresented: $showingPrivacy) { PrivacyNoticeView() }
    }

    /// Offered before sign-in as well as in Profile: someone who cannot read the
    /// welcome copy should not have to sign in to fix that.
    private var languageToggle: some View {
        HStack {
            Spacer()
            Picker(S.Profile.languageLabel, selection: Binding(
                get: { language.language },
                set: { container.setLanguage($0) }
            )) {
                ForEach(AppLanguage.allCases) { option in
                    Text(option.shortName).tag(option)
                }
            }
            .pickerStyle(.segmented)
            .frame(width: 120)
            .accessibilityLabel(S.Profile.languageLabel)
        }
    }

    private func handle(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let tokenData = credential.identityToken,
                let identityToken = String(data: tokenData, encoding: .utf8)
            else {
                session.authError = .server(status: -1, code: "apple_token_missing")
                return
            }
            Task { await session.signInWithApple(identityToken: identityToken) }
        case .failure:
            // A cancelled Apple sheet is not an error worth shouting about (spec §10.1).
            session.authError = nil
        }
    }
}

struct PrivacyNoticeView: View {
    @Environment(\.dismiss) private var dismiss

    private var items: [(title: String, body: String)] {
        [
            (S.Privacy.accountTitle, S.Privacy.accountBody),
            (S.Privacy.writingTitle, S.Privacy.writingBody),
            (S.Privacy.analyticsTitle, S.Privacy.analyticsBody),
            (S.Privacy.deletionTitle, S.Privacy.deletionBody),
            (S.Privacy.scoresTitle, S.Privacy.scoresBody)
        ]
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    Text(S.Privacy.heading)
                        .font(.title2.weight(.bold))
                        .appear(0)

                    ForEach(Array(items.enumerated()), id: \.element.title) { index, item in
                        privacyItem(title: item.title, body: item.body)
                            .appear(index + 1)
                    }
                }
                .padding(Theme.Spacing.l)
            }
            .navigationTitle(S.Privacy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(S.Common.done) { dismiss() }
                }
            }
        }
    }

    private func privacyItem(title: String, body: String) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text(title).font(.headline)
            Text(body).font(.subheadline).foregroundStyle(Theme.Palette.secondaryText)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
