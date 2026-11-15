# Windows AI APIs — reference

Loaded by `desktop-windows:platform-integration` when the app uses on-device AI. Verified 2026-11-15 against learn.microsoft.com/windows/ai/apis (Phi Silica page updated 2026-10-16). Namespaces: `Microsoft.Windows.AI`, `.AI.Text`, `.AI.Imaging`, `.AI.ContentSafety`. Windows App SDK 2.x; packaged or unpackaged.

## The rule set

1. **Readiness first.** Every API exposes `GetReadyState()` returning `AIFeatureReadyState`: `Ready`, `NotReady`, `NotSupportedOnCurrentSystem`. Branch on all three.
2. **Consent before download.** `EnsureReadyAsync()` downloads a model (several GB for the GPU language model, in the background through Windows Update). Ask the user first, say the size and where to remove it (**Settings → System → AI Components**), show progress, allow cancel.
3. **`NotSupportedOnCurrentSystem` is a working screen:** the feature is hidden or replaced by a non-AI path, with the requirement stated; never a crash or a blank region.
4. **AI work is off the UI thread, cancellable and inside a timeout budget.** Results return through `DispatcherQueue.TryEnqueue`. Inference latency varies by device; stream or show progress.
5. **User-facing names are generic:** "language model", "optional AI model" — not the product name.
6. **Output is untrusted text:** never executed, never rendered as markup unescaped, never used as a command or a path.
7. **Content safety on:** `ContentFilterOptions` (for example `PromptMaxAllowedSeverityLevel`) set deliberately, not left at a guess.
8. **Watermark:** from October 2026 some text APIs add an invisible watermark marking AI-generated text. The app owns the legal duty to mark AI content where it applies; do not strip the watermark without checking the requirement (Microsoft Learn: Watermarking in Windows AI text APIs).
9. **Not in China:** Phi Silica features are not available there.
10. **No prompt, response or user content in logs or telemetry** unless the user opted in.

```csharp
public async Task<LanguageModel?> OpenLanguageModelAsync(Func<Task<bool>> askConsentAsync)
{
    switch (LanguageModel.GetReadyState())
    {
        case AIFeatureReadyState.Ready:
            return await LanguageModel.CreateAsync();
        case AIFeatureReadyState.NotReady when await askConsentAsync():
            var ensure = await LanguageModel.EnsureReadyAsync();
            return ensure.Status == AIFeatureReadyResultState.Success
                ? await LanguageModel.CreateAsync()
                : null;
        default:
            return null;
    }
}
```

`null` means "no AI path": the caller shows the non-AI experience. A cancelled consent is not an error.

## Capabilities

| Capability | Namespace / class | Hardware | Notes |
|---|---|---|---|
| Language model (Phi Silica → Aion Instruct) | `AI.Text.LanguageModel`, `TextSummarizer`, rewrite and text-to-table skills | NPU (Copilot+ PC); GPU: GeForce RTX 30+ / Radeon RX 9060+ with 6+ GB VRAM | see the transition below |
| Text recognition (OCR) | `AI.Imaging.TextRecognizer` | NPU | |
| Image description, super resolution, segmentation, object erase | `AI.Imaging.*` | NPU | |
| Image generation | `AI.Imaging.*` | NPU | content-safety options apply |
| Video super resolution | `AI.Video.*` | NPU / CPU | |
| Speech recognition | experimental | — | **Experimental channel: never in production** |
| Windows ML | `Microsoft.Windows.AI.MachineLearning` (ONNX Runtime 1.24.x) | Windows 10 1903+ | own ONNX models; ARM64EC from 2.3.1 |

## Phi Silica → Aion Instruct (verified 2026-11-15)

- **Phi Silica is a Limited Access Feature (LAF):** an unlock token (`LimitedAccessFeatures.TryUnlockFeature`) is required; request through Microsoft's LAF form. The token is not a secret you commit: it is supplied by configuration like any other, never in the repo.
- **Phi Silica is being replaced by Aion Instruct.** November 2026: Aion Instruct begins rolling out to Windows Insider devices, Phi Silica remains, and the active model is chosen by a controlled feature rollout (side-by-side testing through a registry key). **January 2027: retail rollout, Phi Silica removed.** Aion Instruct needs **no LAF token**.
- **LoRA adapters must be re-trained** for Aion Instruct (Foundry Toolkit); a Phi Silica adapter does not carry over.
- **What the skill does about it:** write against `LanguageModel` and the readiness check only; keep the model name and any LAF token behind one configuration seam; do not depend on Phi Silica-specific behaviour (prompt compression and speculative decoding are NPU-only today); tell the user in the plan which date the project crosses. **The Aion Instruct API surface was not re-read beyond the transition notice** — a task that targets it re-reads the current page first and records the result.
- **GPU path:** needs Developer Mode, the vendor driver installed directly from NVIDIA or AMD, and (at the time of the page) a Windows Insider Experimental build and WinAppSDK 2.2.2-experimental9 or later — an experimental prerequisite, so the GPU path is **not a production dependency** until it reaches stable. Prompt compression and speculative decoding are not available on GPU.

## Audit hooks (section J)

- A model call with no `GetReadyState` branch → major.
- `EnsureReadyAsync` with no consent step → major.
- A hard dependency on Phi Silica by name, or a LAF token in source → major.
- Prompt or response text in a log → blocker if it can carry personal data.
- An experimental-channel AI API in a production build → blocker.
