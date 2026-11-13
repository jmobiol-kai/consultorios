import assert from "node:assert/strict";
import test from "node:test";

import {
    FACE_SURFACES,
    STATE_BLUE,
    STATE_RED,
    STATUS_FOR_CONDITION,
    alignPrimarySlots,
    clearTargets,
    conditionIsWholeTooth,
    conditionSymbol,
    cssColor,
    chartEditsAllowed,
    faceClickAction,
    faceLayout,
    legendPaintPlan,
    legendShowsActive,
    nextMark,
    paintCondition,
    stateColor,
    stateKey,
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
    assert.deepEqual(nextMark(YELLOW, YELLOW, "pending"), {
        condition: YELLOW,
        status: "treated",
        same: false,
    });
    assert.deepEqual(nextMark("caries", "caries", "treated"), {
        condition: "caries",
        status: "pending",
        same: false,
    });
    assert.equal(nextMark("crown", "crown", "present").same, true);
    assert.equal(statusForCondition("endodontics"), "pending");
    assert.equal(statusForCondition("implant"), "pending");
    assert.equal(statusForCondition("extraction"), "pending");
    assert.equal(statusForCondition("prosthesis"), "pending");
    assert.equal(statusForCondition("sealant"), "treated");
    assert.equal(statusForCondition("no-such"), "pending");
});

test("legend statuses are stable codes, not the editable labels", () => {
    const codes = new Set(["present", "pending", "treated", "missing"]);
    for (const [condition, status] of Object.entries(STATUS_FOR_CONDITION)) {
        assert.equal(codes.has(status), true, condition);
        assert.equal(status.includes(" "), false, condition);
    }
    assert.equal(STATUS_FOR_CONDITION.caries, "pending");
    assert.equal(STATUS_FOR_CONDITION.restoration, "treated");
    assert.equal(STATUS_FOR_CONDITION.sound, "present");
    assert.equal(STATUS_FOR_CONDITION.missing, "missing");
});

test("the catalog flag decides whole-tooth, not the Spanish name", () => {
    assert.equal(conditionIsWholeTooth({ whole_tooth: true, name: "Caries" }, "caries"), true);
    assert.equal(
        conditionIsWholeTooth({ whole_tooth: false, name: "Implante" }, "implant"),
        false
    );
    assert.equal(conditionIsWholeTooth({ whole_tooth: 1 }, "caries"), true);
    assert.equal(conditionIsWholeTooth({ whole_tooth: 0 }, "crown"), false);
    // Sin fila no se lee el nombre: solo el código de fábrica.
    assert.equal(conditionIsWholeTooth({ name: "Prótesis" }, "protesis_fija"), false);
    assert.equal(conditionIsWholeTooth(null, "protesis_fija"), false);
});

test("factory codes cover the whole-tooth legend and not face conditions", () => {
    for (const code of ["sound", "crown", "implant", "extraction", "missing", "prosthesis"]) {
        assert.equal(conditionIsWholeTooth(null, code), true, code);
        assert.equal(conditionIsWholeTooth({}, code), true, code);
    }
    for (const code of ["caries", "restoration", "endodontics", "fracture", "sealant"]) {
        assert.equal(conditionIsWholeTooth(null, code), false, code);
    }
});

test("a whole-tooth legend click writes the pieza and clears every face", () => {
    for (const selected of ["occlusal", "mesial", "buccal", "lingual", "distal", "tooth"]) {
        const plan = legendPaintPlan(selected, true);
        assert.deepEqual(plan.write, ["tooth"], selected);
        assert.deepEqual(plan.clear, FACE_SURFACES, selected);
        assert.equal(plan.clear.includes("tooth"), false, selected);
    }
    const tooth = "implant";
    for (const surface of FACE_SURFACES) {
        assert.equal(paintCondition(surface, "", tooth), tooth, surface);
    }
    // Una cara con marca propia sigue tapando el color de la pieza:
    // por eso el plan la borra antes de pintar.
    assert.equal(paintCondition("mesial", "caries", tooth), "caries");
});

test("a face condition from the legend paints only the selected face", () => {
    assert.deepEqual(legendPaintPlan("occlusal", false), {
        write: ["occlusal"],
        clear: [],
    });
    assert.deepEqual(legendPaintPlan("mesial", false), {
        write: ["mesial"],
        clear: [],
    });
    assert.deepEqual(legendPaintPlan("tooth", false), {
        write: ["tooth"],
        clear: [],
    });
});

test("the legend button stays active on an inherited whole-tooth color", () => {
    assert.equal(legendShowsActive("", "implant", "implant", true), true);
    assert.equal(legendShowsActive("implant", "implant", "implant", true), true);
    assert.equal(legendShowsActive("caries", "implant", "implant", true), false);
    assert.equal(legendShowsActive("caries", "implant", "caries", false), true);
    assert.equal(legendShowsActive("", "caries", "caries", false), false);
    assert.equal(legendShowsActive("", "", "sound", true), false);
});

test("the second click blanks a whole-tooth color that lives on the pieza", () => {
    assert.deepEqual(clearTargets("occlusal", "", "implant", true), ["tooth"]);
    assert.deepEqual(clearTargets("mesial", "", "crown", true), ["tooth"]);
    assert.deepEqual(clearTargets("occlusal", "caries", "implant", true), ["occlusal"]);
    assert.deepEqual(clearTargets("tooth", "crown", "crown", true), ["tooth"]);
    assert.deepEqual(clearTargets("occlusal", "", "caries", false), []);
    assert.deepEqual(clearTargets("occlusal", "", "", false), []);
});

test("state paints red to treat and blue when done or already restored", () => {
    assert.equal(stateKey("crown", "pending"), "pending");
    assert.equal(stateKey("crown", "treated"), "treated");
    assert.equal(stateKey("crown", "present"), "treated");
    assert.equal(stateColor("crown", "pending"), STATE_RED);
    assert.equal(stateColor("crown", "treated"), STATE_BLUE);
    assert.equal(stateColor("crown", "present"), STATE_BLUE);
    assert.notEqual(stateColor("crown", "pending"), stateColor("crown", "treated"));
    assert.equal(stateColor("caries", "pending"), STATE_RED);
    assert.equal(stateColor("restoration", "treated"), STATE_BLUE);
    assert.equal(stateColor("restoration", "present"), STATE_BLUE);
    assert.equal(stateColor("implant", "present"), STATE_BLUE);
    assert.equal(stateColor("sound", "present"), "");
    assert.equal(stateKey("missing", "missing"), "missing");
    assert.equal(stateColor("missing", "missing"), "");
    assert.equal(stateKey("sound", "unerupted"), "unerupted");
    assert.equal(conditionSymbol("crown"), "CR");
    assert.equal(conditionSymbol("caries"), "C");
    assert.equal(conditionSymbol("sound"), "");
    assert.equal(conditionSymbol("sound", true), "○");
});

test("primary teeth sit inside the permanent arch, on the midline side", () => {
    const upperRight = alignPrimarySlots(["55", "54", "53", "52", "51"], true);
    assert.deepEqual(upperRight, [null, null, null, "55", "54", "53", "52", "51"]);
    const upperLeft = alignPrimarySlots(["61", "62", "63", "64", "65"], false);
    assert.deepEqual(upperLeft, ["61", "62", "63", "64", "65", null, null, null]);
    const lowerRight = alignPrimarySlots(["85", "84", "83", "82", "81"], true);
    assert.equal(lowerRight[3], "85");
    assert.equal(lowerRight[7], "81");
    assert.equal(lowerRight[0], null);
});

test("each tooth exposes five faces and keeps mesial toward the midline", () => {
    const upperRight = faceLayout("16", false).map((face) => face.surface);
    assert.deepEqual(upperRight.sort(), ["buccal", "distal", "lingual", "mesial"].sort());
    const right = faceLayout("16", false).find((face) => face.surface === "mesial");
    const left = faceLayout("21", false).find((face) => face.surface === "mesial");
    assert.ok(right.x > 50);
    assert.ok(left.x < 50);
    assert.ok(faceLayout("55", false).every((face) => face.d.includes("M ")));
    assert.equal(faceLayout("75", true).find((face) => face.y > 60).surface, "buccal");
});

test("a readonly chart does not take face or legend edits", () => {
    assert.equal(chartEditsAllowed(false), true);
    assert.equal(chartEditsAllowed(undefined), true);
    assert.equal(chartEditsAllowed(true), false);
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
