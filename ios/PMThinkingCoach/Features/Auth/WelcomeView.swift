import AuthenticationServices
import SwiftUI

/// Welcome / sign-in (spec §10.1).
struct WelcomeView: View {
    @EnvironmentObject private var session: SessionStore
    @State private var showingPrivacy = false

    var body: some View {
        VStack(spacing: Theme.Spacing.xl) {
            Spacer()

            VStack(spacing: Theme.Spacing.l) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 56))
                    .foregroundStyle(Theme.Palette.accent)

                Text("Practise thinking like a Product Manager.")
                    .font(.largeTitle.weight(.bold))
                    .multilineTextAlignment(.center)

                Text("A short daily product scenario. Your decision. Clear feedback.")
                    .font(.title3)
                    .foregroundStyle(Theme.Palette.secondaryText)
                    .multilineTextAlignment(.center)
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
                .disabled(session.isAuthenticating)
                .accessibilityLabel("Continue with Apple")

                if AppConfig.allowsDeveloperSignIn {
                    Button("Continue without Apple (development)") {
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

                Button("Privacy notice") { showingPrivacy = true }
                    .font(.footnote)
                    .frame(minHeight: Theme.minimumTapTarget)
            }
            .padding(.horizontal, Theme.Spacing.xl)
            .padding(.bottom, Theme.Spacing.xl)

            if session.isAuthenticating {
                ProgressView().padding(.bottom, Theme.Spacing.l)
            }
        }
        .background(Theme.Palette.background)
        .sheet(isPresented: $showingPrivacy) { PrivacyNoticeView() }
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

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    Text("What we collect and why")
                        .font(.title2.weight(.bold))

                    privacyItem(
                        title: "Your account",
                        body: "Signing in with Apple gives us a stable identifier for your "
                            + "account. We do not ask for your name, email, employer, or any "
                            + "demographic information."
                    )
                    privacyItem(
                        title: "What you write",
                        body: "The reasoning you write for each challenge is sent to our "
                            + "server and to our AI provider for the sole purpose of "
                            + "generating your feedback. It is never sent to analytics, "
                            + "crash reporting, or notifications."
                    )
                    privacyItem(
                        title: "Product analytics",
                        body: "We record which screens you reach and which options you "
                            + "select so we can improve the product. These events never "
                            + "include what you wrote or the feedback you received."
                    )
                    privacyItem(
                        title: "Deleting your account",
                        body: "You can delete your account from Profile at any time. This "
                            + "removes your written responses, your feedback, and your "
                            + "identity link."
                    )
                    privacyItem(
                        title: "What scores mean",
                        body: "Skill scores are practice signals based on your in-app work. "
                            + "They are not an assessment of job readiness and they do not "
                            + "predict hiring outcomes."
                    )
                }
                .padding(Theme.Spacing.l)
            }
            .navigationTitle("Privacy")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
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
