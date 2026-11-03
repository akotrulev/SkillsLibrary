---
paths:
  - "**/*{View,Screen,Row,Sheet,Form}.swift"
  - "**/{Views,Screens,Components,UI}/**/*.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): SwiftUI views. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its views. -->

# SwiftUI view standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise; a SwiftUI rule is never flagged on a UIKit screen.

- `body` is pure and cheap: no network call, `UserDefaults` read, decode, formatter construction or sort. *major*
- Async work starts in `.task` / `.task(id:)`, never `Task { }` in `onAppear` or a load in `init`. *major*
- Every data region is one `LoadState` enum rendering loading, loaded, empty and failed, plus stale and offline where cached, scoped to the response-dependent subtree; chrome and filters survive. *major*
- An undecodable response is failed, never empty; a failed refetch keeps the data, marked stale; a cancelled request renders nothing; offline is not a server error and offers no retry. *major*
- Every surfaced failure also raises the one persistent banner: safe-area top, never auto-dismissed, a 44 pt close, deduped. *major*
- Never render `localizedDescription`, a raw server string or a body. *major*
- Unbounded data is a `List` or lazy stack with stable domain ids: no `id: \.self` on non-unique data, no index, no `UUID()` per render. *major*
- System controls and SF Symbols; no custom tab bar, navigation bar or back button imitating another platform. *major*
- No `AnyView` to dodge a type error, no `GeometryReader` as a default layout tool. *minor*
- `NavigationStack(path:)` with typed `Hashable` routes carrying ids, never models; `navigationDestination(for:)` once at the stack root; each tab owns its stack; a destination loads its own data. No `NavigationView`, `NavigationLink(destination:)` or `presentationMode`. *major*
- Sheets use `.sheet(item:)` with a close affordance. *minor*
- Forms: one pure validator; errors as localized text beside the field; submit guards re-entry, shows progress and carries one idempotency key; `textContentType` on credential, address and code fields; `SecureField` for secrets; server field errors land on their fields, unknown ones in a form-level message. *major*
- `#Preview` per state with no live data; no `PreviewProvider` in new code. *minor*
