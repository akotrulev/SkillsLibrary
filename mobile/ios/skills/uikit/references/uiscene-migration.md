# Moving to the UIScene lifecycle (TN3187)

Linking against the iOS 27 SDK makes the scene lifecycle mandatory. Source: Apple Technical Note TN3187, *Migrating to the UIKit scene-based life cycle*. **Read the note against the installed SDK before editing** — the manifest keys below are the long-standing ones; re-check them against the note.

Scope: the move only. It does not restructure navigation, change screens, or raise the deployment target (scenes exist since iOS 13).

## 1. Detect where the app is

| Signal | State |
|---|---|
| `UIApplicationSceneManifest` in `Info.plist` and a class implementing `UIWindowSceneDelegate` | Already scene-based — stop |
| `window` property on the `AppDelegate`, `application(_:didFinishLaunchingWithOptions:)` creating the window | Needs the move |
| SwiftUI `App` lifecycle | Already scene-based |
| Mixed: manifest present, window still created in the app delegate | Half-done — finish step 4 |

`rg -n "UIApplicationSceneManifest|UIWindowSceneDelegate|var window: UIWindow" -g 'Info.plist' -g '*.swift'`

## 2. The manifest

```xml
<key>UIApplicationSceneManifest</key>
<dict>
    <key>UIApplicationSupportsMultipleScenes</key>
    <false/>
    <key>UISceneConfigurations</key>
    <dict>
        <key>UIWindowSceneSessionRoleApplication</key>
        <array>
            <dict>
                <key>UISceneConfigurationName</key>
                <string>Default Configuration</string>
                <key>UISceneDelegateClassName</key>
                <string>$(PRODUCT_MODULE_NAME).SceneDelegate</string>
            </dict>
        </array>
    </dict>
</dict>
```

A storyboard-based app adds `UISceneStoryboardFile` to the configuration and removes `UIMainStoryboardFile` from the top level. iPad apps that support multiple windows set `UIApplicationSupportsMultipleScenes` to `true` and handle several scenes — a product decision, not part of the move.

## 3. The scene delegate

```swift
final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private var appServices: AppServices { AppServices.shared }

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = RootComposer.makeRoot(services: appServices)
        window.makeKeyAndVisible()
        self.window = window

        if let url = options.urlContexts.first?.url { route(url) }
        if let activity = options.userActivities.first { route(activity) }
    }

    func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
        if let url = contexts.first?.url { route(url) }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        route(userActivity)
    }

    func stateRestorationActivity(for scene: UIScene) -> NSUserActivity? {
        scene.userActivity
    }
}
```

- The root is built by the **composition root** from initializer-injected parts — the scene delegate does not create dependencies ad hoc. If the project holds services in a singleton today, keep that shape in the move and flag it; replacing it is not part of this task.
- **`route(_:)` is the one function turning a URL or activity into a destination** — the same one `onOpenURL` uses on the SwiftUI side ([`navigation`](../../navigation/SKILL.md)). It validates scheme, host and parameters first; a link is untrusted input (`mobile-<stack>:security` § 5).
- A cold start from a link delivers it in `willConnectTo` options; a warm start delivers it through `openURLContexts` / `continue`. Both paths route.

## 4. Slim the app delegate

Keep in `AppDelegate`: process-wide setup (crash reporting, push registration callbacks, background `URLSession` handlers). **Remove** the `window` property, window creation, and `application(_:open:options:)` / `application(_:continue:restorationHandler:)` (scene-based apps receive these on the scene delegate).

```swift
final class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        UISceneConfiguration(name: "Default Configuration", sessionRole: connectingSceneSession.role)
    }
}
```

Code that read `UIApplication.shared.delegate.window` or `UIApplication.shared.keyWindow` moves to the scene: `view.window?.windowScene`, `UIWindowScene.keyWindow` (iOS 15+). Alerts and presentations that assumed one window are presented from a view controller in the right scene.

## 5. State and lifecycle

- App-level lifecycle callbacks (`applicationDidBecomeActive`, `applicationWillResignActive`) become scene callbacks (`sceneDidBecomeActive`, `sceneWillResignActive`, `sceneDidEnterBackground`) — the **app-switcher cover** for sensitive screens ([`mobile-<stack>:security`](../../../../_shared/security/references/ios.md) § 3) moves to `sceneWillResignActive`.
- Old state restoration (`application(_:shouldSaveSecureApplicationState:)`) becomes `stateRestorationActivity(for:)` and `scene(_:restoreInteractionStateWith:)`.
- Background tasks and notifications stay on the app delegate / `UNUserNotificationCenter`; they are not per scene.

## 6. Launch screen

The iOS 27 SDK also requires a launch screen: `UILaunchScreen` in `Info.plist` (or a launch storyboard). An app with neither is the second blocker — check both together.

## 7. Check

- Cold launch, warm launch, launch from a universal link, launch from a push, launch after a process kill: each reaches the right screen.
- On iPad, the window resizes and (if supported) a second window opens.
- Nothing reads `UIApplication.shared.keyWindow` or the delegate's `window`.
