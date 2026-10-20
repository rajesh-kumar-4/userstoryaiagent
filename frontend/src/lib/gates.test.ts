import { describe, expect, it } from "vitest";
import type { ChangeSet, Finding, Severity } from "./types";
import {
  classifyRiskScore,
  countBySeverity,
  evaluatePreCommitGate,
  evaluateReleaseGate,
  fileChurn,
  groupFindingsByCategory,
  validateBranchPair,
  validateRef,
} from "./gates";

const finding = (severity: Severity, category = "general") => ({ severity, category }) as Finding;

const file = (
  path: string,
  added: number,
  deleted: number,
  modified: number,
) =>
  ({
    path,
    added_lines: added,
    deleted_lines: deleted,
    modified_lines: modified,
    change_type: "MODIFIED",
  }) as ChangeSet["files"][number];

describe("validateRef", () => {
  it("requires a value when required", () => {
    expect(validateRef("Branch", "   ", true)).toBe("Branch is required");
  });

  it("allows an empty optional value", () => {
    expect(validateRef("Branch", "", false)).toBeNull();
  });

  it("rejects values longer than 255 characters", () => {
    expect(validateRef("Branch", "a".repeat(256), true)).toBe("Branch must be 255 characters or fewer");
  });

  it("rejects characters outside the backend pattern", () => {
    expect(validateRef("Branch", "feature branch", true)).toContain("may only contain");
    expect(validateRef("Branch", "-leading-dash", true)).toContain("may only contain");
  });

  it("accepts common git ref names", () => {
    expect(validateRef("Branch", "feature/login-v2.1", true)).toBeNull();
    expect(validateRef("Branch", "  release@2026  ", true)).toBeNull();
  });
});

describe("validateBranchPair", () => {
  it("flags identical source and target after trimming", () => {
    expect(validateBranchPair("main", " main ")).toBe("Source and target branches must differ");
  });

  it("accepts distinct branches and empty inputs", () => {
    expect(validateBranchPair("main", "develop")).toBeNull();
    expect(validateBranchPair("", "")).toBeNull();
  });
});

describe("classifyRiskScore", () => {
  it.each([
    [0, "LOW"],
    [19, "LOW"],
    [20, "MEDIUM"],
    [49, "MEDIUM"],
    [50, "HIGH"],
    [79, "HIGH"],
    [80, "CRITICAL"],
    [100, "CRITICAL"],
  ] as const)("maps score %i to %s", (score, level) => {
    expect(classifyRiskScore(score)).toBe(level);
  });
});

describe("evaluatePreCommitGate", () => {
  it("blocks on CRITICAL or HIGH findings", () => {
    const gate = evaluatePreCommitGate({ findings: [finding("HIGH")], risk_level: "HIGH" });
    expect(gate.decision).toBe("BLOCK");
    expect(gate.reasons[0]).toContain("1 CRITICAL/HIGH");
  });

  it("warns on MEDIUM findings", () => {
    const gate = evaluatePreCommitGate({ findings: [finding("MEDIUM")], risk_level: "LOW" });
    expect(gate.decision).toBe("WARN");
  });

  it("passes when there are no blocking or medium findings", () => {
    const gate = evaluatePreCommitGate({ findings: [finding("LOW")], risk_level: "LOW" });
    expect(gate.decision).toBe("PASS");
  });
});

describe("evaluateReleaseGate", () => {
  const base = {
    findings: [] as Finding[],
    risk_level: "LOW" as Severity,
    risk_score: 10,
    warnings: [] as string[],
    summary_source: "analysis-engine",
  };

  it("returns GO when every check passes", () => {
    const gate = evaluateReleaseGate(base);
    expect(gate.decision).toBe("GO");
    expect(gate.reasons).toEqual(["All release checks passed"]);
    expect(gate.checklist.every((item) => item.passed)).toBe(true);
  });

  it("returns NO_GO on any CRITICAL finding", () => {
    const gate = evaluateReleaseGate({ ...base, findings: [finding("CRITICAL")] });
    expect(gate.decision).toBe("NO_GO");
    expect(gate.checklist[0].passed).toBe(false);
  });

  it("returns NO_GO when the overall risk level is CRITICAL", () => {
    expect(evaluateReleaseGate({ ...base, risk_level: "CRITICAL" }).decision).toBe("NO_GO");
  });

  it("returns CONDITIONAL_GO when the score reaches the threshold", () => {
    const gate = evaluateReleaseGate({ ...base, risk_score: 70 });
    expect(gate.decision).toBe("CONDITIONAL_GO");
    expect(gate.reasons.join(" ")).toContain("at or above 70");
  });

  it("honours a custom maxScore", () => {
    expect(evaluateReleaseGate({ ...base, risk_score: 30 }, 25).decision).toBe("CONDITIONAL_GO");
  });

  it("returns CONDITIONAL_GO for HIGH findings and analysis warnings", () => {
    expect(evaluateReleaseGate({ ...base, findings: [finding("HIGH")] }).decision).toBe("CONDITIONAL_GO");
    expect(evaluateReleaseGate({ ...base, warnings: ["partial scan"] }).decision).toBe("CONDITIONAL_GO");
  });
});

describe("groupFindingsByCategory", () => {
  it("groups findings under their category", () => {
    const groups = groupFindingsByCategory([
      finding("LOW", "security"),
      finding("HIGH", "security"),
      finding("MEDIUM", "style"),
    ]);
    expect(Object.keys(groups).sort()).toEqual(["security", "style"]);
    expect(groups.security).toHaveLength(2);
    expect(groups.style).toHaveLength(1);
  });
});

describe("countBySeverity", () => {
  it("returns zero for every severity with no findings", () => {
    expect(countBySeverity([])).toEqual({ LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 });
  });

  it("counts findings per severity", () => {
    expect(countBySeverity([finding("LOW"), finding("HIGH"), finding("HIGH")])).toEqual({
      LOW: 1,
      MEDIUM: 0,
      HIGH: 2,
      CRITICAL: 0,
    });
  });
});

describe("fileChurn", () => {
  it("sorts by total churn descending, then path ascending", () => {
    const result = fileChurn({
      files: [file("b.ts", 1, 1, 0), file("a.ts", 5, 0, 0), file("c.ts", 0, 1, 1)],
    });
    expect(result.map((item) => item.path)).toEqual(["a.ts", "b.ts", "c.ts"]);
    expect(result[0].churn).toBe(5);
    expect(result[1].churn).toBe(2);
  });
});
