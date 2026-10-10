# Interop seams — UIKit in SwiftUI

A complete `UIViewRepresentable`; the rules are in `SKILL.md`.

```swift
struct MapContainer: UIViewRepresentable {
    let region: MKCoordinateRegion
    let onSelect: (Place.ID) -> Void

    func makeUIView(context: Context) -> MKMapView {
        let view = MKMapView()
        view.delegate = context.coordinator
        view.accessibilityIdentifier = "Map.View"
        return view
    }

    func updateUIView(_ view: MKMapView, context: Context) {
        view.setRegion(region, animated: false)
    }

    func makeCoordinator() -> Coordinator { Coordinator(onSelect: onSelect) }

    final class Coordinator: NSObject, MKMapViewDelegate {
        let onSelect: (Place.ID) -> Void
        init(onSelect: @escaping (Place.ID) -> Void) { self.onSelect = onSelect }
    }

    static func dismantleUIView(_ view: MKMapView, coordinator: Coordinator) {
        view.delegate = nil
    }
}
```

- **`makeUIView` builds once; `updateUIView` applies state and is idempotent** — never create subviews there, never trigger state changes from it (a loop), and diff before writing (`if view.region != region`).
- **Delegates and target-action live in the `Coordinator`**, which holds closures, not the SwiftUI view.
- Clean up in `dismantleUIView`; `UIViewControllerRepresentable` for whole controllers (camera, document picker, `SFSafariViewController`) — and prefer the SwiftUI equivalent (`PhotosPicker`, `fileImporter`, `Link`) where it exists ([`device-features`](../device-features/SKILL.md)).
- `sizeThatFits(_:uiView:context:)` (iOS 16+) tells SwiftUI the size; without it the view takes the proposed size.

