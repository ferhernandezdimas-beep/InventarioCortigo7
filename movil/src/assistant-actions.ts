import { normalize } from "./domain";
import type { CatalogCommand, Snapshot } from "./types";
export type ToolKind = CatalogCommand["kind"];
export type FieldSpec = {
  key: string;
  label: string;
  type: "text" | "decimal" | "choice" | "boolean";
  required?: boolean;
  options?: { id: number; name: string }[];
};
export const toolLabels: Record<ToolKind, string> = {
  "catalog.ingredient.create": "Crear ingrediente",
  "catalog.category.create": "Crear categoría",
  "catalog.supplier.create": "Crear proveedor",
  "catalog.presentation.create": "Crear presentación",
};
export function toolFields(kind: ToolKind, snapshot: Snapshot): FieldSpec[] {
  const name: FieldSpec = {
    key: "name",
    label: "Nombre",
    type: "text",
    required: true,
  };
  if (kind === "catalog.category.create") return [name];
  if (kind === "catalog.supplier.create")
    return [
      name,
      ...[
        ["legal_name", "Razón social"],
        ["contact", "Contacto"],
        ["phone", "Teléfono"],
        ["email", "Correo electrónico"],
        ["address", "Dirección"],
        ["notes", "Notas"],
      ].map(([key, label]) => ({ key, label, type: "text" as const })),
      { key: "active", label: "Proveedor activo", type: "boolean" },
    ];
  if (kind === "catalog.presentation.create")
    return [
      name,
      {
        key: "ingredient_id",
        label: "Ingrediente",
        type: "choice",
        required: true,
        options: snapshot.ingredients.map((i) => ({ id: i.id, name: i.name })),
      },
      {
        key: "base_quantity",
        label: "Contenido en unidades base",
        type: "decimal",
        required: true,
      },
    ];
  return [
    name,
    { key: "code", label: "Código interno", type: "text" },
    { key: "description", label: "Descripción", type: "text" },
    {
      key: "category_id",
      label: "Categoría",
      type: "choice",
      required: true,
      options: snapshot.categories || [],
    },
    {
      key: "unit_id",
      label: "Unidad base",
      type: "choice",
      required: true,
      options: (snapshot.units || []).map((u) => ({
        id: u.id,
        name: `${u.name} (${u.symbol})`,
      })),
    },
    {
      key: "supplier_id",
      label: "Proveedor principal",
      type: "choice",
      options: [{ id: 0, name: "Sin proveedor" }, ...snapshot.suppliers],
    },
    {
      key: "minimum",
      label: "Existencia mínima",
      type: "decimal",
      required: true,
    },
    { key: "maximum", label: "Existencia máxima · opcional", type: "decimal" },
    {
      key: "reference_cost",
      label: "Costo de referencia · opcional",
      type: "decimal",
    },
    { key: "active", label: "Ingrediente activo", type: "boolean" },
  ];
}
export type Plan = { kind: ToolKind; data: CatalogCommand["data"] };
export function planAction(text: string, snapshot: Snapshot): Plan | null {
  const q = normalize(text);
  if (
    !/^(?:por favor\s+)?(?:crea(?:r)?|registra(?:r)?|agrega(?:r)?|anade|anadir|da de alta|dar de alta)\b/.test(
      q,
    )
  )
    return null;
  const resource = q.match(
    /\b(ingrediente|categoria|proveedor|presentacion)\b/,
  )?.[1];
  if (!resource) return null;
  const kinds: Record<string, ToolKind> = {
    ingrediente: "catalog.ingredient.create",
    categoria: "catalog.category.create",
    proveedor: "catalog.supplier.create",
    presentacion: "catalog.presentation.create",
  };
  const kind = kinds[resource];
  const quoted = text.match(/["“]([^"”]+)["”]/)?.[1];
  const start = q.indexOf(resource) + resource.length;
  const raw = text
    .slice(start)
    .trim()
    .replace(/^(?:llamad[oa]|de nombre)\s+/i, "");
  const name =
    quoted ||
    raw
      .split(
        /[,;]|\s+(?:categor[ií]a|unidad|m[ií]nimo|m[aá]ximo|proveedor|contenido|c[oó]digo)\b/i,
      )[0]
      .trim();
  const data: CatalogCommand["data"] = { name: name.replace(/[.?!]+$/, "") };
  if (kind === "catalog.ingredient.create") {
    data.minimum = "0";
    data.active = true;
    data.supplier_id = 0;
    const category = [...(snapshot.categories || [])]
      .sort((a, b) => b.name.length - a.name.length)
      .find((c) => q.includes(normalize(c.name)));
    const unit = [...(snapshot.units || [])]
      .sort((a, b) => b.symbol.length - a.symbol.length)
      .find((u) =>
        new RegExp(
          `(?:^|[^a-z])${normalize(u.symbol).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?:$|[^a-z])`,
        ).test(q),
      );
    if (category) data.category_id = category.id;
    if (unit) data.unit_id = unit.id;
    const min = q.match(/\bminimo\s*(?:de\s*|:|=)?\s*(\d+(?:[.,]\d+)?)/)?.[1];
    const max = q.match(/\bmaximo\s*(?:de\s*|:|=)?\s*(\d+(?:[.,]\d+)?)/)?.[1];
    if (min) data.minimum = min.replace(",", ".");
    if (max) data.maximum = max.replace(",", ".");
  } else if (kind === "catalog.supplier.create") data.active = true;
  return { kind, data };
}
