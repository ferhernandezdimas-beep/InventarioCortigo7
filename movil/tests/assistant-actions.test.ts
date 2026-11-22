import test from "node:test";
import assert from "node:assert/strict";
import { planAction, toolFields } from "../src/assistant-actions";
import type { Snapshot } from "../src/types";
const snapshot = {
  categories: [{ id: 12, name: "Verduras" }],
  units: [{ id: 3, name: "Kilogramo", symbol: "kg" }],
  ingredients: [{ id: 8, name: "Jitomate" }],
  suppliers: [],
} as unknown as Snapshot;

test("Spanish ingredient instruction prepares exact decimal fields without executing", () => {
  const plan = planAction(
    'Crea ingrediente "Aguacate Hass" categoría Verduras unidad kg mínimo 2,5 máximo 15',
    snapshot,
  );
  assert.deepEqual(plan, {
    kind: "catalog.ingredient.create",
    data: {
      name: "Aguacate Hass",
      category_id: 12,
      unit_id: 3,
      minimum: "2.5",
      maximum: "15",
      supplier_id: 0,
      active: true,
    },
  });
});
test("questions and unsupported actions cannot become mutations", () => {
  for (const query of [
    "¿Cómo crear ingrediente?",
    "Cuántos ingredientes hay",
    "Elimina ingrediente Jitomate",
    "Crea venta de 2 tacos",
  ])
    assert.equal(planAction(query, snapshot), null);
});
test("four guided catalog tools and unknown names remain reviewable", () => {
  for (const [resource, kind] of [
    ["categoría", "category"],
    ["proveedor", "supplier"],
    ["presentación", "presentation"],
    ["ingrediente", "ingredient"],
  ]) {
    const plan = planAction(`Registra ${resource} "Nuevo registro"`, snapshot)!;
    assert.equal(plan.kind, `catalog.${kind}.create`);
    assert.equal(plan.data.name, "Nuevo registro");
    assert.ok(
      toolFields(plan.kind, snapshot).some(
        (f) => f.key === "name" && f.required,
      ),
    );
  }
  assert.equal(
    planAction("Crea ingrediente Menta", snapshot)?.data.category_id,
    undefined,
  );
});
test("ingredient review includes every optional web field and original IDs", () => {
  const fields = toolFields("catalog.ingredient.create", snapshot);
  assert.deepEqual(
    fields.map((f) => f.key),
    [
      "name",
      "code",
      "description",
      "category_id",
      "unit_id",
      "supplier_id",
      "minimum",
      "maximum",
      "reference_cost",
      "active",
    ],
  );
  assert.equal(fields.find((f) => f.key === "unit_id")!.options![0].id, 3);
});
