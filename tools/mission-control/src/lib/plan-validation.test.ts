import { describe, expect, it } from "vitest";
import { validatePlan, type ValidatablePlan } from "./plan-validation";

/** A minimal internally-consistent plan; each test bends one thing out of shape. */
function plan(overrides: Partial<ValidatablePlan> = {}): ValidatablePlan {
  return {
    phases: [
      { id: "p1", name: "Foundations" },
      { id: "p2", name: "Features" },
    ],
    tasks: [
      { id: "t1", phaseId: "p1", dependsOn: [] },
      { id: "t2", phaseId: "p2", dependsOn: ["t1"] },
    ],
    openQuestions: [{ id: "q1", blocksTaskIds: ["t2"] }],
    ...overrides,
  };
}

describe("validatePlan", () => {
  it("Should_ReturnNoProblems_When_PlanIsConsistent", () => {
    expect(validatePlan(plan())).toEqual([]);
  });

  it("Should_RejectTask_When_PhaseDoesNotExist", () => {
    const problems = validatePlan(
      plan({
        tasks: [{ id: "ghost", phaseId: "p-missing", dependsOn: [] }],
        openQuestions: [],
      }),
    );
    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("ghost → p-missing");
  });

  it("Should_RejectPlan_When_TaskIdsAreDuplicated", () => {
    const problems = validatePlan(
      plan({
        tasks: [
          { id: "t1", phaseId: "p1", dependsOn: [] },
          { id: "t1", phaseId: "p2", dependsOn: [] },
        ],
      }),
    );
    expect(problems.some((p) => p.includes("Duplicate task ids: t1"))).toBe(true);
  });

  it("Should_RejectPlan_When_PhaseIdsAreDuplicated", () => {
    const problems = validatePlan(
      plan({
        phases: [
          { id: "p1", name: "One" },
          { id: "p1", name: "Two" },
        ],
      }),
    );
    expect(problems.some((p) => p.includes("Duplicate phase ids: p1"))).toBe(true);
  });

  it("Should_RejectTask_When_ItDependsOnItself", () => {
    const problems = validatePlan(
      plan({ tasks: [{ id: "t1", phaseId: "p1", dependsOn: ["t1"] }] }),
    );
    expect(problems.some((p) => p === "Task t1 depends on itself.")).toBe(true);
  });

  it("Should_RejectTask_When_DependencyIsUnknown", () => {
    const problems = validatePlan(
      plan({ tasks: [{ id: "t1", phaseId: "p1", dependsOn: ["nope"] }] }),
    );
    expect(problems.some((p) => p.includes("unknown task(s): nope"))).toBe(true);
  });

  it("Should_RejectTask_When_DependencyRunsInALaterPhase", () => {
    // Phases run strictly in order, so this could never be satisfied.
    const problems = validatePlan(
      plan({
        tasks: [
          { id: "early", phaseId: "p1", dependsOn: ["late"] },
          { id: "late", phaseId: "p2", dependsOn: [] },
        ],
      }),
    );
    expect(problems.some((p) => p.includes("runs in a later phase"))).toBe(true);
  });

  it("Should_AllowDependency_When_ItRunsInAnEarlierPhase", () => {
    expect(validatePlan(plan())).toEqual([]);
  });

  it("Should_AllowDependency_When_ItRunsInTheSamePhase", () => {
    const problems = validatePlan(
      plan({
        tasks: [
          { id: "a", phaseId: "p1", dependsOn: [] },
          { id: "b", phaseId: "p1", dependsOn: ["a"] },
        ],
        openQuestions: [],
      }),
    );
    expect(problems).toEqual([]);
  });

  it("Should_RejectQuestion_When_ItBlocksAnUnknownTask", () => {
    const problems = validatePlan(
      plan({ openQuestions: [{ id: "q1", blocksTaskIds: ["missing"] }] }),
    );
    expect(problems.some((p) => p.includes("q1 blocks unknown task(s): missing"))).toBe(
      true,
    );
  });

  it("Should_ReportEveryProblem_When_SeveralArePresent", () => {
    const problems = validatePlan(
      plan({
        tasks: [
          { id: "dupe", phaseId: "p-missing", dependsOn: ["dupe"] },
          { id: "dupe", phaseId: "p1", dependsOn: [] },
        ],
        openQuestions: [{ id: "q1", blocksTaskIds: ["gone"] }],
      }),
    );
    expect(problems.length).toBeGreaterThanOrEqual(4);
  });
});
