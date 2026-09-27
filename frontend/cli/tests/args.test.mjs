import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { parseArgv, parseTokenBudget, assertOptions, UsageError } from "../args.mjs";

describe("cli args: parsing", () => {
  it("separates positionals, flags and value options", () => {
    const parsed = parseArgv(["index", "/work/alpha", "--repo", "beta", "--json"]);
    assert.deepEqual(parsed.positionals, ["index", "/work/alpha"]);
    assert.equal(parsed.flags.json, true);
    assert.equal(parsed.options.repo, "beta");
    assert.deepEqual(parsed.used, ["--repo", "--json"]);
  });

  it("accepts --name=value and --name value equivalently", () => {
    assert.equal(parseArgv(["--repo=/work/alpha"]).options.repo, "/work/alpha");
    assert.equal(parseArgv(["--repo", "/work/alpha"]).options.repo, "/work/alpha");
    assert.equal(parseArgv(["--budget=8k"]).options.budget, "8k");
  });

  it("normalizes --graph / --no-graph to the last one given", () => {
    assert.equal(parseArgv(["--graph"]).flags.graph, true);
    assert.equal(parseArgv(["--no-graph"]).flags.graph, false);
    assert.equal(parseArgv(["--no-graph", "--graph"]).flags.graph, true);
  });

  it("treats everything after -- as positional", () => {
    const parsed = parseArgv(["construct", "--", "--not-an-option"]);
    assert.deepEqual(parsed.positionals, ["construct", "--not-an-option"]);
  });

  it("supports -h as the only short option", () => {
    assert.equal(parseArgv(["-h"]).flags.help, true);
    assert.throws(() => parseArgv(["-x"]), /unknown option|unexpected/);
  });

  it("rejects unknown options, missing values and values on booleans", () => {
    assert.throws(() => parseArgv(["--wat"]), (error) => error instanceof UsageError && /unknown option: --wat/.test(error.message));
    assert.throws(() => parseArgv(["--repo"]), (error) => error instanceof UsageError && /--repo requires a value/.test(error.message));
    assert.throws(() => parseArgv(["--json=yes"]), (error) => error instanceof UsageError && /--json does not take a value/.test(error.message));
  });
});

describe("cli args: token budgets", () => {
  it("normalizes k-suffixed budgets and plain token counts", () => {
    assert.equal(parseTokenBudget("4k"), 4096);
    assert.equal(parseTokenBudget("8K"), 8192);
    assert.equal(parseTokenBudget("16k"), 16384);
    assert.equal(parseTokenBudget("32k"), 32768);
    assert.equal(parseTokenBudget("512"), 512);
    assert.equal(parseTokenBudget("100"), 100);
  });

  it("rejects malformed budgets and anything below the backend minimum", () => {
    for (const value of ["0k", "99", "1.5k", "4kb", "k", "", "abc", "-4k"]) {
      assert.throws(
        () => parseTokenBudget(value),
        (error) => error instanceof UsageError,
        `expected "${value}" to be rejected`
      );
    }
    assert.throws(() => parseTokenBudget("99"), /at least 100 tokens/);
  });
});

describe("cli args: option validation", () => {
  it("accepts allowed options and rejects the rest", () => {
    assert.doesNotThrow(() => assertOptions(["--repo"], ["--repo"], "index"));
    assert.throws(
      () => assertOptions(["--repo"], [], "health"),
      (error) => error instanceof UsageError && /--repo is not valid for "health"/.test(error.message)
    );
  });
});
