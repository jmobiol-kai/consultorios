import assert from "node:assert/strict";
import test from "node:test";

import { encounterFormMustBeReadonly } from "../src/encounter_readonly/readonly_logic.js";

test("a draft visit stays editable", () => {
    assert.equal(encounterFormMustBeReadonly("draft", false), false);
    assert.equal(encounterFormMustBeReadonly(false, false), false);
    assert.equal(encounterFormMustBeReadonly(undefined, false), false);
});

test("closed and signed visits are readonly", () => {
    assert.equal(encounterFormMustBeReadonly("closed", false), true);
    assert.equal(encounterFormMustBeReadonly("signed", false), true);
});

test("a history card is readonly even while the visit is still draft", () => {
    assert.equal(encounterFormMustBeReadonly("draft", true), true);
    assert.equal(encounterFormMustBeReadonly(false, true), true);
    assert.equal(encounterFormMustBeReadonly("closed", true), true);
});
