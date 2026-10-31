import assert from "node:assert/strict";
import test from "node:test";

import {
    cssColor,
    faceClickAction,
    nextMark,
    paintCondition,
    statusForCondition,
} from "../src/odontogram/odontogram_chart_logic.js";

const YELLOW = "crown";

test("configured colors are hex only", () => {
    assert.equal(cssColor("#FFF59D"), "#fff59d");
    assert.equal(cssColor("  #ef9a9a "), "#ef9a9a");
    assert.equal(cssColor("red"), "");
    assert.equal(cssColor("#fff59d;}</style>"), "");
    assert.equal(cssColor(""), "");
});

test("a face keeps its own condition", () => {
    assert.equal(paintCondition("occlusal", "caries", ""), "caries");
    assert.equal(paintCondition("occlusal", "caries", YELLOW), "caries");
    assert.equal(paintCondition("mesial", "restoration", "implant"), "restoration");
});

test("an unmarked face inherits the whole-tooth condition", () => {
    for (const tooth of [
        "crown",
        "endodontics",
        "implant",
        "extraction",
        "missing",
        "prosthesis",
        "fracture",
        "sealant",
        "sound",
        "caries",
    ]) {
        assert.equal(paintCondition("occlusal", "", tooth), tooth);
        assert.equal(paintCondition("buccal", "", tooth), tooth);
        assert.equal(paintCondition("lingual", "", tooth), tooth);
    }
});

test("the pieza ring uses its own condition and does not inherit a face", () => {
    assert.equal(paintCondition("tooth", YELLOW, YELLOW), YELLOW);
    assert.equal(paintCondition("tooth", "", "caries"), "empty");
    assert.equal(paintCondition("occlusal", "", ""), "empty");
});

test("legend choice sets the condition and never clears it", () => {
    assert.deepEqual(nextMark("", "caries"), {
        condition: "caries",
        status: "pending",
        same: false,
    });
    assert.deepEqual(nextMark("caries", "restoration"), {
        condition: "restoration",
        status: "treated",
        same: false,
    });
    assert.deepEqual(nextMark("restoration", "missing"), {
        condition: "missing",
        status: "missing",
        same: false,
    });
    assert.deepEqual(nextMark("missing", "sound"), {
        condition: "sound",
        status: "present",
        same: false,
    });
    assert.deepEqual(nextMark("sound", "sound"), {
        condition: "sound",
        status: "present",
        same: true,
    });
    assert.deepEqual(nextMark("caries", YELLOW), {
        condition: YELLOW,
        status: "pending",
        same: false,
    });
    assert.equal(nextMark(YELLOW, YELLOW).same, true);
    assert.equal(statusForCondition("endodontics"), "pending");
    assert.equal(statusForCondition("implant"), "pending");
    assert.equal(statusForCondition("extraction"), "pending");
    assert.equal(statusForCondition("prosthesis"), "pending");
    assert.equal(statusForCondition("sealant"), "treated");
    assert.equal(statusForCondition("no-such"), "pending");
});

test("a face click selects, and the next click on that same face clears", () => {
    assert.equal(faceClickAction(false), "select");
    assert.equal(faceClickAction(true), "clear");
    // Repeated clicks must not walk caries → obturación → ausente → sano.
    let selected = false;
    let condition = "caries";
    const seen = [];
    for (let i = 0; i < 4; i++) {
        if (faceClickAction(selected) === "select") {
            selected = true;
        } else {
            condition = "";
        }
        seen.push(condition || "blank");
    }
    assert.deepEqual(seen, ["caries", "blank", "blank", "blank"]);
});
